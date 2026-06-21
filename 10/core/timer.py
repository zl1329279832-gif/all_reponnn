import time
from enum import Enum
from typing import Callable, Optional
from dataclasses import dataclass
from datetime import datetime


class TimerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class TimerEndReason(str, Enum):
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


@dataclass
class TimerSnapshot:
    state: TimerState
    total_seconds: int
    remaining_seconds: int
    elapsed_seconds: int
    progress: float


class PomodoroTimer:
    def __init__(self, total_seconds: int = 25 * 60):
        self._total_seconds = total_seconds
        self._state = TimerState.IDLE
        self._start_timestamp: Optional[float] = None
        self._accumulated_elapsed: float = 0.0
        self._end_reason: Optional[TimerEndReason] = None
        self._on_tick: Optional[Callable[[TimerSnapshot], None]] = None
        self._on_completed: Optional[Callable[[], None]] = None
        self._on_state_changed: Optional[Callable[[TimerState, TimerState], None]] = None

    def set_total_seconds(self, total_seconds: int) -> None:
        if self._state == TimerState.RUNNING:
            raise RuntimeError("Cannot change duration while running")
        self._total_seconds = total_seconds
        self._accumulated_elapsed = 0.0

    @property
    def total_seconds(self) -> int:
        return self._total_seconds

    @property
    def state(self) -> TimerState:
        return self._state

    @property
    def end_reason(self) -> Optional[TimerEndReason]:
        return self._end_reason

    def on_tick(self, callback: Callable[[TimerSnapshot], None]) -> None:
        self._on_tick = callback

    def on_completed(self, callback: Callable[[], None]) -> None:
        self._on_completed = callback

    def on_state_changed(
        self, callback: Callable[[TimerState, TimerState], None]
    ) -> None:
        self._on_state_changed = callback

    def _set_state(self, new_state: TimerState) -> None:
        old_state = self._state
        self._state = new_state
        if self._on_state_changed:
            self._on_state_changed(old_state, new_state)

    def start(self) -> None:
        if self._state in (TimerState.RUNNING, TimerState.COMPLETED):
            return
        self._start_timestamp = time.monotonic()
        self._end_reason = None
        self._set_state(TimerState.RUNNING)

    def pause(self) -> None:
        if self._state != TimerState.RUNNING:
            return
        if self._start_timestamp is not None:
            self._accumulated_elapsed += time.monotonic() - self._start_timestamp
            self._start_timestamp = None
        self._end_reason = TimerEndReason.PAUSED
        self._set_state(TimerState.PAUSED)

    def resume(self) -> None:
        if self._state != TimerState.PAUSED:
            return
        self._start_timestamp = time.monotonic()
        self._end_reason = None
        self._set_state(TimerState.RUNNING)

    def abandon(self) -> None:
        if self._state in (TimerState.IDLE, TimerState.COMPLETED):
            return
        self._end_reason = TimerEndReason.ABANDONED
        if self._start_timestamp is not None:
            self._accumulated_elapsed += time.monotonic() - self._start_timestamp
            self._start_timestamp = None
        self._set_state(TimerState.IDLE)

    def reset(self) -> None:
        self._accumulated_elapsed = 0.0
        self._start_timestamp = None
        self._end_reason = None
        self._set_state(TimerState.IDLE)

    def tick(self) -> TimerSnapshot:
        snapshot = self.snapshot()
        if self._state == TimerState.RUNNING:
            if snapshot.remaining_seconds <= 0:
                self._accumulated_elapsed = float(self._total_seconds)
                self._start_timestamp = None
                self._end_reason = TimerEndReason.COMPLETED
                self._set_state(TimerState.COMPLETED)
                snapshot = self.snapshot()
                if self._on_completed:
                    self._on_completed()
        if self._on_tick:
            self._on_tick(snapshot)
        return snapshot

    def snapshot(self) -> TimerSnapshot:
        elapsed = self._accumulated_elapsed
        if self._state == TimerState.RUNNING and self._start_timestamp is not None:
            elapsed += time.monotonic() - self._start_timestamp
        elapsed_seconds = int(min(elapsed, self._total_seconds))
        remaining = max(0, self._total_seconds - elapsed_seconds)
        progress = 0.0
        if self._total_seconds > 0:
            progress = min(1.0, elapsed_seconds / self._total_seconds)
        return TimerSnapshot(
            state=self._state,
            total_seconds=self._total_seconds,
            remaining_seconds=remaining,
            elapsed_seconds=elapsed_seconds,
            progress=progress,
        )

    def get_elapsed_seconds(self) -> int:
        return self.snapshot().elapsed_seconds
