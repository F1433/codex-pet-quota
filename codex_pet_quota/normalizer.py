import math
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import WeeklyQuotaView


WEEK_MINUTES = 7 * 24 * 60


def _windows(bucket: Dict[str, Any]) -> Iterable[Tuple[str, Dict[str, Any]]]:
    for role in ("primary", "secondary"):
        value = bucket.get(role)
        if isinstance(value, dict):
            yield role, value
    additional = bucket.get("additional")
    if isinstance(additional, list):
        for index, value in enumerate(additional):
            if isinstance(value, dict):
                yield "additional:%d" % index, value


def _core_buckets(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_id = result.get("rateLimitsByLimitId")
    if isinstance(by_id, dict):
        exact = by_id.get("codex")
        if isinstance(exact, dict):
            return [exact]
        return []
    legacy = result.get("rateLimits")
    if isinstance(legacy, dict) and legacy.get("limitId", "codex") == "codex":
        return [legacy]
    return []


def normalize_weekly(
    result: Dict[str, Any],
    scope_key: str,
    fetched_at: Optional[float] = None,
) -> WeeklyQuotaView:
    """Return only the verified seven-day Codex core window.

    Five-hour and model-specific buckets are intentionally ignored.
    """
    fetched = fetched_at if fetched_at is not None else time.time()
    if not isinstance(result, dict):
        return WeeklyQuotaView(
            state="error",
            scope_key=scope_key,
            source="cli-rpc",
            fetched_at=fetched,
            message="额度响应格式无效",
        )

    candidates = []
    for bucket in _core_buckets(result):
        for role, window in _windows(bucket):
            duration = window.get("windowDurationMins")
            try:
                duration_number = int(duration)
            except (TypeError, ValueError, OverflowError):
                continue
            if duration_number == WEEK_MINUTES:
                candidates.append((bucket, role, window))

    if not candidates:
        return WeeklyQuotaView(
            state="unavailable",
            scope_key=scope_key,
            source="cli-rpc",
            fetched_at=fetched,
            message="周额度暂不可用",
        )

    bucket, _role, window = candidates[0]
    used = window.get("usedPercent")
    if isinstance(used, bool):
        used = None
    try:
        used_number = float(used)
    except (TypeError, ValueError, OverflowError):
        used_number = math.nan
    if not math.isfinite(used_number) or used_number < 0 or used_number > 100:
        return WeeklyQuotaView(
            state="invalid",
            scope_key=scope_key,
            source="cli-rpc",
            fetched_at=fetched,
            limit_id=str(bucket.get("limitId") or "codex"),
            message="周额度数值无效",
        )

    reset = window.get("resetsAt")
    try:
        reset_number = int(reset) if reset is not None else None
    except (TypeError, ValueError, OverflowError):
        reset_number = None

    return WeeklyQuotaView(
        state="ready",
        scope_key=scope_key,
        source="cli-rpc",
        fetched_at=fetched,
        remaining_percent=max(0.0, min(100.0, 100.0 - used_number)),
        used_percent=used_number,
        resets_at=reset_number,
        limit_id=str(bucket.get("limitId") or "codex"),
    )

