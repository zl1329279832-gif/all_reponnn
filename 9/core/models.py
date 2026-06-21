from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SessionStatus(str, Enum):
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    PAUSED_ABANDONED = "paused_abandoned"


class TimerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


PRESETS: dict[str, int] = {
    "番茄钟 25min": 25 * 60,
    "深度专注 45min": 45 * 60,
    "短专注 15min": 15 * 60,
    "长专注 60min": 60 * 60,
}

DEFAULT_PRESET = "番茄钟 25min"


@dataclass
class FocusSession:
    id: Optional[int] = None
    started_at: str = ""
    duration_seconds: int = 0
    completed_seconds: int = 0
    status: str = SessionStatus.COMPLETED.value
    preset_name: str = ""


@dataclass
class DailyStat:
    date: str = ""
    completed_seconds: int = 0
    abandoned_seconds: int = 0
    paused_abandoned_seconds: int = 0
    completed_count: int = 0
    abandoned_count: int = 0
    paused_abandoned_count: int = 0

    @property
    def total_seconds(self) -> int:
        return self.completed_seconds + self.abandoned_seconds + self.paused_abandoned_seconds

    @property
    def total_count(self) -> int:
        return self.completed_count + self.abandoned_count + self.paused_abandoned_count
