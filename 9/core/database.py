import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import Optional

from core.models import FocusSession, SessionStatus, DailyStat


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pomodoro.db")


class PomodoroDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_schema()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                completed_seconds INTEGER NOT NULL,
                status TEXT NOT NULL,
                preset_name TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_started
            ON focus_sessions(started_at)
        """)
        self.conn.commit()

    def record_session(
        self,
        started_at: str,
        duration_seconds: int,
        completed_seconds: int,
        status: str,
        preset_name: str = "",
    ) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO focus_sessions (started_at, duration_seconds, completed_seconds, status, preset_name)
            VALUES (?, ?, ?, ?, ?)
        """, (started_at, duration_seconds, completed_seconds, status, preset_name))
        self.conn.commit()
        return cur.lastrowid

    def get_daily_stats(self, days: int = 7) -> list[DailyStat]:
        today = date.today()
        stats: list[DailyStat] = []
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            d_str = d.isoformat()
            start = f"{d_str} 00:00:00"
            end = f"{d_str} 23:59:59"
            cur = self.conn.cursor()
            cur.execute("""
                SELECT status, SUM(completed_seconds) as secs, COUNT(*) as cnt
                FROM focus_sessions
                WHERE started_at >= ? AND started_at <= ?
                GROUP BY status
            """, (start, end))
            rows = cur.fetchall()
            ds = DailyStat(date=d_str)
            for r in rows:
                s = r["status"]
                secs = r["secs"] or 0
                cnt = r["cnt"] or 0
                if s == SessionStatus.COMPLETED.value:
                    ds.completed_seconds = secs
                    ds.completed_count = cnt
                elif s == SessionStatus.ABANDONED.value:
                    ds.abandoned_seconds = secs
                    ds.abandoned_count = cnt
                elif s == SessionStatus.PAUSED_ABANDONED.value:
                    ds.paused_abandoned_seconds = secs
                    ds.paused_abandoned_count = cnt
            stats.append(ds)
        return stats

    def get_today_summary(self) -> DailyStat:
        stats = self.get_daily_stats(1)
        return stats[0] if stats else DailyStat(date=date.today().isoformat())
