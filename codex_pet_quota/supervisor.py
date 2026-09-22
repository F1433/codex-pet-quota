import datetime as dt
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from .instance_lock import SingleInstance
from .pet_locator import enumerate_codex_windows
from .storage import data_dir


POLL_SECONDS = 1.0
RESTART_DELAY_SECONDS = 2.0
MAX_LOG_BYTES = 256 * 1024


def _log(message: str) -> None:
    path = data_dir() / "watchdog.log"
    try:
        mode = "w" if path.exists() and path.stat().st_size >= MAX_LOG_BYTES else "a"
        timestamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        with path.open(mode, encoding="utf-8") as stream:
            stream.write("%s %s\n" % (timestamp, message))
    except OSError:
        pass


def codex_desktop_present() -> bool:
    """Return whether the packaged Codex desktop app is running.

    The app executable is currently named ChatGPT.exe. Requiring the exact
    image name avoids mistaking Codex CLI and computer-use helper windows for
    the desktop app.
    """
    return any(
        item.image_name.lower() in ("chatgpt.exe", "codex.exe")
        for item in enumerate_codex_windows()
        if item.image_name
    )


def _background_running() -> bool:
    with SingleInstance() as probe:
        return not probe.acquired


def _spawn_background() -> subprocess.Popen:
    project_root = Path(__file__).resolve().parent.parent
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        [sys.executable, "-m", "codex_pet_quota", "--background"],
        cwd=str(project_root),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )


def _stop_child(child: subprocess.Popen) -> None:
    if child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=3)


def run_supervisor() -> None:
    """Bind the quota UI process to the Codex desktop lifecycle."""
    child = None  # type: Optional[subprocess.Popen]
    previous_present = None  # type: Optional[bool]
    next_start = 0.0
    _log("supervisor started")
    try:
        while True:
            now = time.monotonic()
            present = codex_desktop_present()
            if present != previous_present:
                _log("Codex desktop detected" if present else "Codex desktop stopped")
                previous_present = present

            if child is not None:
                exit_code = child.poll()
                if exit_code is not None:
                    _log("quota watcher exited with code %s" % exit_code)
                    child = None
                    next_start = now + RESTART_DELAY_SECONDS

            if present:
                if child is None and now >= next_start:
                    if _background_running():
                        next_start = now + RESTART_DELAY_SECONDS
                    else:
                        try:
                            child = _spawn_background()
                            _log("quota watcher started pid=%s" % child.pid)
                        except OSError as exc:
                            _log("quota watcher start failed: %s" % exc)
                            next_start = now + RESTART_DELAY_SECONDS
            elif child is not None:
                _stop_child(child)
                _log("quota watcher stopped with Codex")
                child = None
                next_start = 0.0

            time.sleep(POLL_SECONDS)
    finally:
        if child is not None:
            _stop_child(child)
        _log("supervisor stopped")
