import os
import tempfile
from datetime import datetime

import pytest

from core.timer import PomodoroTimer
from core.models import TimerState, SessionStatus, PRESETS, DEFAULT_PRESET
from core.database import PomodoroDB


class TestPomodoroTimerStateTransitions:
    def test_initial_state(self):
        t = PomodoroTimer()
        assert t.state == TimerState.IDLE
        assert t.total_seconds == PRESETS[DEFAULT_PRESET]
        assert t.remaining_seconds == t.total_seconds
        assert t.elapsed_seconds == 0

    def test_cannot_start_from_running(self):
        t = PomodoroTimer()
        t.start()
        with pytest.raises(RuntimeError):
            t.start()

    def test_cannot_start_from_paused(self):
        t = PomodoroTimer()
        t.start()
        t.pause()
        with pytest.raises(RuntimeError):
            t.start()

    def test_cannot_pause_from_idle(self):
        t = PomodoroTimer()
        with pytest.raises(RuntimeError):
            t.pause()

    def test_cannot_pause_from_paused(self):
        t = PomodoroTimer()
        t.start()
        t.pause()
        with pytest.raises(RuntimeError):
            t.pause()

    def test_cannot_resume_from_idle(self):
        t = PomodoroTimer()
        with pytest.raises(RuntimeError):
            t.resume()

    def test_cannot_resume_from_running(self):
        t = PomodoroTimer()
        t.start()
        with pytest.raises(RuntimeError):
            t.resume()

    def test_cannot_abandon_from_idle(self):
        t = PomodoroTimer()
        with pytest.raises(RuntimeError):
            t.abandon()

    def test_cannot_complete_from_idle(self):
        t = PomodoroTimer()
        with pytest.raises(RuntimeError):
            t.complete()

    def test_cannot_complete_from_paused(self):
        t = PomodoroTimer()
        t.start()
        t.pause()
        with pytest.raises(RuntimeError):
            t.complete()


class TestPresetSelectionDrivesStartDuration:
    def test_default_preset_is_25min(self):
        t = PomodoroTimer()
        assert t.total_seconds == 25 * 60

    def test_set_preset_updates_total_before_start(self):
        t = PomodoroTimer()
        t.set_preset("深度专注 45min")
        assert t.total_seconds == 45 * 60
        assert t.remaining_seconds == 45 * 60
        assert t.current_preset == "深度专注 45min"

    def test_start_uses_preset_total_not_settings_default(self):
        t = PomodoroTimer()
        t.set_preset("深度专注 45min")
        t.start()
        assert t.total_seconds == 45 * 60
        assert t.remaining_seconds == 45 * 60

    def test_set_preset_15min_start_matches(self):
        t = PomodoroTimer()
        t.set_preset("短专注 15min")
        t.start()
        assert t.remaining_seconds == 15 * 60

    def test_set_preset_60min_start_matches(self):
        t = PomodoroTimer()
        t.set_preset("长专注 60min")
        t.start()
        assert t.remaining_seconds == 60 * 60

    def test_cannot_change_preset_while_running(self):
        t = PomodoroTimer()
        t.start()
        with pytest.raises(RuntimeError):
            t.set_preset("深度专注 45min")

    def test_cannot_change_preset_while_paused(self):
        t = PomodoroTimer()
        t.start()
        t.pause()
        with pytest.raises(RuntimeError):
            t.set_preset("深度专注 45min")

    def test_unknown_preset_raises(self):
        t = PomodoroTimer()
        with pytest.raises(ValueError):
            t.set_preset("不存在的预设")

    def test_set_duration_seconds_custom(self):
        t = PomodoroTimer()
        t.set_duration_seconds(1800)
        assert t.total_seconds == 1800
        t.start()
        assert t.remaining_seconds == 1800


class TestTickAndCountdown:
    def test_tick_decrements_remaining(self):
        t = PomodoroTimer()
        t.set_preset("短专注 15min")
        t.start()
        finished = t.tick()
        assert not finished
        assert t.remaining_seconds == 15 * 60 - 1
        assert t.elapsed_seconds == 1

    def test_tick_returns_true_when_finished(self):
        t = PomodoroTimer()
        t.set_duration_seconds(2)
        t.start()
        assert not t.tick()
        assert t.tick()

    def test_tick_does_nothing_when_paused(self):
        t = PomodoroTimer()
        t.set_duration_seconds(10)
        t.start()
        t.tick()
        t.pause()
        result = t.tick()
        assert result is False
        assert t.remaining_seconds == 9

    def test_tick_does_nothing_when_idle(self):
        t = PomodoroTimer()
        result = t.tick()
        assert result is False


class TestAbandonAndComplete:
    def test_abandon_while_running_returns_positive_elapsed(self):
        t = PomodoroTimer()
        t.set_duration_seconds(100)
        t.start()
        for _ in range(10):
            t.tick()
        elapsed = t.abandon()
        assert elapsed == 10
        assert t.state == TimerState.IDLE
        assert t.remaining_seconds == 100

    def test_abandon_while_paused_returns_negative_elapsed(self):
        t = PomodoroTimer()
        t.set_duration_seconds(100)
        t.start()
        for _ in range(10):
            t.tick()
        t.pause()
        elapsed = t.abandon()
        assert elapsed == -10
        assert t.state == TimerState.IDLE

    def test_complete_returns_elapsed(self):
        t = PomodoroTimer()
        t.set_duration_seconds(3)
        t.start()
        t.tick()
        t.tick()
        t.tick()
        elapsed = t.complete()
        assert elapsed == 3
        assert t.state == TimerState.IDLE

    def test_abandon_resets_to_total(self):
        t = PomodoroTimer()
        t.set_preset("深度专注 45min")
        t.start()
        for _ in range(30):
            t.tick()
        t.abandon()
        assert t.total_seconds == 45 * 60
        assert t.remaining_seconds == 45 * 60


class TestProgress:
    def test_progress_zero_at_idle(self):
        t = PomodoroTimer()
        assert t.progress() == 0.0

    def test_progress_increases_with_ticks(self):
        t = PomodoroTimer()
        t.set_duration_seconds(10)
        t.start()
        t.tick()
        assert abs(t.progress() - 0.1) < 0.01

    def test_format_remaining(self):
        t = PomodoroTimer()
        t.set_duration_seconds(1500)
        t.start()
        assert t.format_remaining() == "25:00"
        t.tick()
        assert t.format_remaining() == "24:59"


class TestThreeWaySessionStatus:
    def test_completed_status(self):
        assert SessionStatus.COMPLETED.value == "completed"

    def test_abandoned_status(self):
        assert SessionStatus.ABANDONED.value == "abandoned"

    def test_paused_abandoned_status(self):
        assert SessionStatus.PAUSED_ABANDONED.value == "paused_abandoned"

    def test_three_statuses_are_distinct(self):
        values = {s.value for s in SessionStatus}
        assert len(values) == 3


class TestDatabaseRecording:
    def _make_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = PomodoroDB(path)
        return db, path

    def test_record_completed_session(self):
        db, path = self._make_db()
        try:
            sid = db.record_session(
                started_at="2026-06-21 10:00:00",
                duration_seconds=1500,
                completed_seconds=1500,
                status=SessionStatus.COMPLETED.value,
                preset_name="番茄钟 25min",
            )
            assert sid > 0
            stats = db.get_daily_stats(1)
            assert len(stats) == 1
            assert stats[0].completed_seconds == 1500
            assert stats[0].completed_count == 1
            assert stats[0].abandoned_seconds == 0
        finally:
            db.close()
            os.unlink(path)

    def test_record_abandoned_session(self):
        db, path = self._make_db()
        try:
            db.record_session(
                started_at="2026-06-21 10:00:00",
                duration_seconds=1500,
                completed_seconds=300,
                status=SessionStatus.ABANDONED.value,
                preset_name="番茄钟 25min",
            )
            stats = db.get_daily_stats(1)
            assert stats[0].abandoned_seconds == 300
            assert stats[0].abandoned_count == 1
            assert stats[0].completed_seconds == 0
        finally:
            db.close()
            os.unlink(path)

    def test_record_paused_abandoned_session(self):
        db, path = self._make_db()
        try:
            db.record_session(
                started_at="2026-06-21 10:00:00",
                duration_seconds=1500,
                completed_seconds=180,
                status=SessionStatus.PAUSED_ABANDONED.value,
                preset_name="番茄钟 25min",
            )
            stats = db.get_daily_stats(1)
            assert stats[0].paused_abandoned_seconds == 180
            assert stats[0].paused_abandoned_count == 1
            assert stats[0].completed_seconds == 0
            assert stats[0].abandoned_seconds == 0
        finally:
            db.close()
            os.unlink(path)

    def test_mixed_sessions_in_one_day(self):
        db, path = self._make_db()
        try:
            db.record_session("2026-06-21 09:00:00", 1500, 1500, SessionStatus.COMPLETED.value, "番茄钟 25min")
            db.record_session("2026-06-21 10:00:00", 1500, 300, SessionStatus.ABANDONED.value, "番茄钟 25min")
            db.record_session("2026-06-21 11:00:00", 1500, 120, SessionStatus.PAUSED_ABANDONED.value, "番茄钟 25min")
            db.record_session("2026-06-21 12:00:00", 1500, 1500, SessionStatus.COMPLETED.value, "番茄钟 25min")
            stats = db.get_daily_stats(1)
            assert stats[0].completed_count == 2
            assert stats[0].completed_seconds == 3000
            assert stats[0].abandoned_count == 1
            assert stats[0].abandoned_seconds == 300
            assert stats[0].paused_abandoned_count == 1
            assert stats[0].paused_abandoned_seconds == 120
        finally:
            db.close()
            os.unlink(path)

    def test_seven_day_stats(self):
        db, path = self._make_db()
        try:
            db.record_session("2026-06-15 10:00:00", 1500, 1500, SessionStatus.COMPLETED.value, "番茄钟 25min")
            db.record_session("2026-06-21 10:00:00", 1500, 1500, SessionStatus.COMPLETED.value, "番茄钟 25min")
            stats = db.get_daily_stats(7)
            assert len(stats) == 7
        finally:
            db.close()
            os.unlink(path)

    def test_today_summary(self):
        db, path = self._make_db()
        try:
            db.record_session("2026-06-21 09:00:00", 1500, 1500, SessionStatus.COMPLETED.value, "番茄钟 25min")
            summary = db.get_today_summary()
            assert summary.completed_count == 1
            assert summary.completed_seconds == 1500
        finally:
            db.close()
            os.unlink(path)
