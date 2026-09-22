import time
from typing import Any, Dict, Optional

from .models import AlertDecision, WeeklyQuotaView
from .storage import AlertStateStore


class AlertEngine:
    def __init__(self, store: AlertStateStore, threshold: float = 20.0, clear_at: float = 25.0):
        self.store = store
        self.threshold = threshold
        self.clear_at = clear_at

    def evaluate(self, view: WeeklyQuotaView, now: Optional[float] = None) -> AlertDecision:
        if not view.is_ready:
            return AlertDecision(False, False, "invalid-or-stale")
        current_time = now if now is not None else time.time()
        state = self.store.load()
        scopes = state.setdefault("scopes", {})
        record = scopes.setdefault(view.scope_key, {})

        previous_reset = record.get("expectedResetAt")
        cycle_id = record.get("cycleId")
        if cycle_id is None:
            cycle_id = "reset:%s" % (view.resets_at if view.resets_at is not None else "unknown")
        elif (
            isinstance(previous_reset, (int, float))
            and isinstance(view.resets_at, int)
            and current_time >= float(previous_reset) - 300
            and view.resets_at > float(previous_reset) + 86400
        ):
            cycle_id = "reset:%s" % view.resets_at
            record["notifiedCycleId"] = None
            record["aboveClearCount"] = 0

        record["cycleId"] = cycle_id
        if view.resets_at is not None:
            record["expectedResetAt"] = view.resets_at

        remaining = float(view.remaining_percent)
        badge = bool(record.get("badgeVisible", False))
        if remaining < self.threshold:
            badge = True
            record["aboveClearCount"] = 0
        elif remaining >= self.clear_at:
            count = int(record.get("aboveClearCount", 0)) + 1
            record["aboveClearCount"] = count
            if count >= 2:
                badge = False
        else:
            record["aboveClearCount"] = 0
        record["badgeVisible"] = badge

        should_notify = remaining < self.threshold and record.get("notifiedCycleId") != cycle_id
        if should_notify:
            record["notifiedCycleId"] = cycle_id
            record["notifiedAt"] = current_time
        record["lastRemainingPercent"] = remaining
        record["updatedAt"] = current_time
        self.store.save(state)
        return AlertDecision(should_notify, badge, "below-threshold" if should_notify else "no-new-alert")

