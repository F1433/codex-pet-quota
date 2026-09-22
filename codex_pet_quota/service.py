import time
from pathlib import Path
from typing import Optional, Tuple

from .alerts import AlertEngine
from .app_server import AppServerClient, identity_string
from .models import AlertDecision, WeeklyQuotaView
from .normalizer import normalize_weekly
from .storage import AlertStateStore, ScopeHasher, SnapshotCache, data_dir


class QuotaService:
    def __init__(self, root: Optional[Path] = None, timeout: float = 15.0):
        self.root = root or data_dir()
        self.hasher = ScopeHasher(self.root)
        self.cache = SnapshotCache(self.root)
        self.alerts = AlertEngine(AlertStateStore(self.root))
        self.client = AppServerClient(timeout=timeout)

    def refresh(self) -> Tuple[WeeklyQuotaView, AlertDecision]:
        try:
            account, raw_limits = self.client.fetch()
            scope = self.hasher.key(identity_string(account))
            view = normalize_weekly(raw_limits, scope, time.time())
            self.cache.save(view)
            decision = self.alerts.evaluate(view)
            return view, decision
        except Exception:
            # A failed protocol/auth process is rebuilt on the next backoff attempt.
            self.client.close()
            raise

    def close(self) -> None:
        self.client.close()
