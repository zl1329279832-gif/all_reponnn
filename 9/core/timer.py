from core.models import TimerState, PRESETS, DEFAULT_PRESET


class PomodoroTimer:
    def __init__(self):
        self.state: TimerState = TimerState.IDLE
        self.total_seconds: int = PRESETS[DEFAULT_PRESET]
        self.remaining_seconds: int = self.total_seconds
        self.elapsed_seconds: int = 0
        self.current_preset: str = DEFAULT_PRESET

    def set_preset(self, preset_name: str) -> None:
        if preset_name not in PRESETS:
            raise ValueError(f"Unknown preset: {preset_name}")
        if self.state != TimerState.IDLE:
            raise RuntimeError("Cannot change preset while timer is active")
        self.current_preset = preset_name
        self.total_seconds = PRESETS[preset_name]
        self.remaining_seconds = self.total_seconds
        self.elapsed_seconds = 0

    def set_duration_seconds(self, seconds: int) -> None:
        if self.state != TimerState.IDLE:
            raise RuntimeError("Cannot change duration while timer is active")
        if seconds <= 0:
            raise ValueError("Duration must be positive")
        self.total_seconds = seconds
        self.remaining_seconds = seconds
        self.elapsed_seconds = 0
        self.current_preset = ""

    def start(self) -> None:
        if self.state != TimerState.IDLE:
            raise RuntimeError(f"Cannot start from state {self.state.value}")
        self.state = TimerState.RUNNING
        self.remaining_seconds = self.total_seconds
        self.elapsed_seconds = 0

    def pause(self) -> None:
        if self.state != TimerState.RUNNING:
            raise RuntimeError(f"Cannot pause from state {self.state.value}")
        self.state = TimerState.PAUSED

    def resume(self) -> None:
        if self.state != TimerState.PAUSED:
            raise RuntimeError(f"Cannot resume from state {self.state.value}")
        self.state = TimerState.RUNNING

    def tick(self) -> bool:
        if self.state != TimerState.RUNNING:
            return False
        if self.remaining_seconds <= 0:
            return True
        self.remaining_seconds -= 1
        self.elapsed_seconds += 1
        return self.remaining_seconds <= 0

    def abandon(self) -> int:
        if self.state not in (TimerState.RUNNING, TimerState.PAUSED):
            raise RuntimeError(f"Cannot abandon from state {self.state.value}")
        elapsed = self.elapsed_seconds
        was_paused = self.state == TimerState.PAUSED
        self._reset()
        return elapsed if not was_paused else -elapsed

    def complete(self) -> int:
        if self.state != TimerState.RUNNING:
            raise RuntimeError(f"Cannot complete from state {self.state.value}")
        elapsed = self.elapsed_seconds
        self._reset()
        return elapsed

    def _reset(self) -> None:
        self.state = TimerState.IDLE
        self.remaining_seconds = self.total_seconds
        self.elapsed_seconds = 0

    def progress(self) -> float:
        if self.total_seconds <= 0:
            return 0.0
        if self.state == TimerState.IDLE:
            return 0.0
        return self.elapsed_seconds / self.total_seconds

    def format_remaining(self) -> str:
        mins, secs = divmod(max(self.remaining_seconds, 0), 60)
        return f"{mins:02d}:{secs:02d}"
