import glob
import json
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ALLOWED_METHODS = {"initialize", "account/read", "account/rateLimits/read"}


class AppServerError(RuntimeError):
    pass


def find_codex() -> str:
    found = shutil.which("codex") or shutil.which("codex.exe")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    if local:
        pattern = str(Path(local) / "OpenAI" / "Codex" / "bin" / "*" / "codex.exe")
        candidates = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        if candidates:
            return candidates[0]
    raise AppServerError("未找到 codex CLI")


class AppServerClient:
    def __init__(self, executable: Optional[str] = None, timeout: float = 15.0):
        self.executable = executable or find_codex()
        self.timeout = timeout
        self.process = None  # type: Optional[subprocess.Popen]
        self.responses = queue.Queue()  # type: queue.Queue
        self.stderr_tail = []  # type: List[str]
        self._next_id = 1
        self._lock = threading.Lock()

    def start(self) -> None:
        if self.process and self.process.poll() is None:
            return
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.process = subprocess.Popen(
            [self.executable, "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=flags,
        )
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        try:
            self._request(
                "initialize",
                {"clientInfo": {"name": "codex-pet-quota", "version": "0.1.0"}, "capabilities": {}},
            )
            self._send({"method": "initialized", "params": {}})
        except Exception:
            self.close()
            raise

    def _read_stdout(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        for line in self.process.stdout:
            try:
                value = json.loads(line)
            except ValueError:
                continue
            self.responses.put(value)

    def _read_stderr(self) -> None:
        assert self.process is not None and self.process.stderr is not None
        for line in self.process.stderr:
            clean = line.strip()
            if clean:
                self.stderr_tail = (self.stderr_tail + [clean])[-20:]

    def _send(self, payload: Dict[str, Any]) -> None:
        if not self.process or self.process.poll() is not None or not self.process.stdin:
            raise AppServerError("App Server 未运行")
        self.process.stdin.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def _request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if method not in ALLOWED_METHODS:
            raise AppServerError("拒绝非只读 RPC 方法：%s" % method)
        with self._lock:
            request_id = self._next_id
            self._next_id += 1
            payload = {"method": method, "id": request_id}
            if params is not None:
                payload["params"] = params
            self._send(payload)
            deadline = time.monotonic() + self.timeout
            deferred = []
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AppServerError("RPC 超时：%s" % method)
                try:
                    message = self.responses.get(timeout=remaining)
                except queue.Empty:
                    raise AppServerError("RPC 超时：%s" % method)
                if message.get("id") != request_id:
                    deferred.append(message)
                    continue
                for item in deferred:
                    self.responses.put(item)
                if message.get("error"):
                    error = message["error"]
                    detail = error.get("message", str(error)) if isinstance(error, dict) else str(error)
                    raise AppServerError("%s：%s" % (method, detail))
                result = message.get("result")
                return result if isinstance(result, dict) else {}

    def fetch(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        self.start()
        account = self._request("account/read", {"refreshToken": False})
        limits = self._request("account/rateLimits/read")
        return account, limits

    def close(self) -> None:
        process = self.process
        self.process = None
        if not process:
            return
        try:
            if process.stdin:
                process.stdin.close()
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, _type, _value, _traceback):
        self.close()


def identity_string(account_result: Dict[str, Any]) -> str:
    account = account_result.get("account")
    if not isinstance(account, dict):
        return "cli:unknown"
    fields = [
        str(account.get("type") or "unknown"),
        str(account.get("email") or ""),
        str(account.get("accountId") or account.get("id") or ""),
        str(account.get("planType") or ""),
    ]
    return "cli:" + "|".join(fields)
