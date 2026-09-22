from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class WeeklyQuotaView:
    state: str
    scope_key: str
    source: str
    fetched_at: float
    remaining_percent: Optional[float] = None
    used_percent: Optional[float] = None
    resets_at: Optional[int] = None
    limit_id: str = "codex"
    message: str = ""

    @property
    def is_ready(self) -> bool:
        return self.state == "ready" and self.remaining_percent is not None


@dataclass(frozen=True)
class PetTarget:
    hwnd: int
    process_id: int
    rect: Tuple[int, int, int, int]
    score: int
    class_name: str
    confidence: str

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]


@dataclass(frozen=True)
class AlertDecision:
    should_notify: bool
    badge_visible: bool
    reason: str

