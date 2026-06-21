import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.timer import PomodoroTimer, TimerState, TimerEndReason, TimerSnapshot


class TestPomodoroTimerCore:
    def test_countdown_to_zero_triggers_completed_state(self):
        timer = PomodoroTimer(total_seconds=2)
        completed_called = []
        state_transitions = []

        def on_completed():
            completed_called.append(True)

        def on_state_changed(old, new):
            state_transitions.append((old, new))

        timer.on_completed(on_completed)
        timer.on_state_changed(on_state_changed)

        assert timer.state == TimerState.IDLE
        timer.start()
        assert timer.state == TimerState.RUNNING

        timer.tick()
        assert timer.state == TimerState.RUNNING

        time.sleep(2.2)

        snap = timer.tick()

        assert timer.state == TimerState.COMPLETED
        assert timer.end_reason == TimerEndReason.COMPLETED
        assert len(completed_called) >= 1
        assert snap.remaining_seconds == 0
        assert snap.progress >= 0.99
        assert (TimerState.RUNNING, TimerState.COMPLETED) in state_transitions

    def test_abandoned_not_counted_as_completed(self):
        timer = PomodoroTimer(total_seconds=600)
        completed_called = []
        timer.on_completed(lambda: completed_called.append(True))

        timer.start()
        time.sleep(1.5)
        snap_before = timer.tick()
        timer.abandon()

        assert timer.state == TimerState.IDLE
        assert timer.end_reason == TimerEndReason.ABANDONED
        assert len(completed_called) == 0
        assert snap_before.elapsed_seconds >= 1
        assert timer.get_elapsed_seconds() >= 1

    def test_completed_marked_as_completed(self):
        timer = PomodoroTimer(total_seconds=1)
        completed_called = []
        timer.on_completed(lambda: completed_called.append(True))

        timer.start()
        time.sleep(1.2)
        timer.tick()

        assert timer.state == TimerState.COMPLETED
        assert timer.end_reason == TimerEndReason.COMPLETED
        assert len(completed_called) == 1

    def test_pause_resume_does_not_drift(self):
        timer = PomodoroTimer(total_seconds=100)
        timer.start()
        time.sleep(0.5)
        snap1 = timer.tick()
        elapsed_after_run = snap1.elapsed_seconds
        assert elapsed_after_run >= 0

        timer.pause()
        paused_elapsed = timer.get_elapsed_seconds()
        time.sleep(0.3)
        assert timer.get_elapsed_seconds() == paused_elapsed

        timer.resume()
        time.sleep(0.3)
        snap2 = timer.tick()
        assert snap2.elapsed_seconds >= paused_elapsed
        assert timer.state == TimerState.RUNNING

    def test_reset_clears_progress(self):
        timer = PomodoroTimer(total_seconds=100)
        timer.start()
        time.sleep(0.2)
        timer.tick()
        timer.reset()

        assert timer.state == TimerState.IDLE
        snap = timer.snapshot()
        assert snap.elapsed_seconds == 0
        assert snap.remaining_seconds == 100
        assert snap.progress == 0.0
