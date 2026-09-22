import hashlib
import json
import os
import secrets
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from .models import WeeklyQuotaView


def data_dir() -> Path:
    override = os.environ.get("CODEX_PET_QUOTA_DATA_DIR")
    if override:
        root = Path(override)
    else:
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CodexPetQuota"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _atomic_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


class ScopeHasher:
    def __init__(self, root: Path):
        self.path = root / "scope-salt.bin"
        try:
            salt = self.path.read_bytes()
        except OSError:
            salt = secrets.token_bytes(32)
            self.path.write_bytes(salt)
        self.salt = salt

    def key(self, identity: str) -> str:
        digest = hashlib.sha256(self.salt + identity.encode("utf-8", "replace")).hexdigest()
        return "cli-" + digest[:20]


class SnapshotCache:
    def __init__(self, root: Path):
        self.path = root / "quota-cache.json"

    def save(self, view: WeeklyQuotaView) -> None:
        payload = asdict(view)
        _atomic_json(self.path, {"schemaVersion": 1, "snapshot": payload})

    def load(self) -> Dict[str, Any]:
        return load_json(self.path).get("snapshot", {})


class AlertStateStore:
    def __init__(self, root: Path):
        self.path = root / "alert-state.json"

    def load(self) -> Dict[str, Any]:
        value = load_json(self.path)
        return value if value.get("schemaVersion") == 1 else {"schemaVersion": 1, "scopes": {}}

    def save(self, value: Dict[str, Any]) -> None:
        _atomic_json(self.path, value)

