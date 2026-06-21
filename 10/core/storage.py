import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from enum import Enum


class SessionStatus(str, Enum):
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class SessionType(str, Enum):
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


class Storage:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_tag TEXT NOT NULL DEFAULT '',
                    session_type TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    actual_duration_seconds INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)"
            )
            conn.commit()

    def create_session(
        self,
        task_tag: str,
        session_type: SessionType,
        duration_seconds: int,
        started_at: Optional[datetime] = None,
    ) -> int:
        if started_at is None:
            started_at = datetime.now()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (task_tag, session_type, duration_seconds, started_at, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (task_tag, session_type.value, duration_seconds, started_at.isoformat(), SessionStatus.PAUSED.value),
            )
            conn.commit()
            return cursor.lastrowid

    def update_session_status(
        self,
        session_id: int,
        status: SessionStatus,
        actual_duration_seconds: int,
        ended_at: Optional[datetime] = None,
    ) -> None:
        if ended_at is None:
            ended_at = datetime.now()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE sessions
                SET status = ?, actual_duration_seconds = ?, ended_at = ?
                WHERE id = ?
                """,
                (status.value, actual_duration_seconds, ended_at.isoformat(), session_id),
            )
            conn.commit()

    def get_today_completed_count(self) -> int:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) as cnt FROM sessions
                WHERE status = ? AND session_type = ? AND started_at >= ?
                """,
                (SessionStatus.COMPLETED.value, SessionType.WORK.value, today_start.isoformat()),
            )
            row = cursor.fetchone()
            return row["cnt"] if row else 0

    def get_last_7_days_stats(self) -> List[Dict]:
        stats = []
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(6, -1, -1):
            day_start = today - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) as cnt FROM sessions
                    WHERE status = ? AND session_type = ?
                    AND started_at >= ? AND started_at < ?
                    """,
                    (
                        SessionStatus.COMPLETED.value,
                        SessionType.WORK.value,
                        day_start.isoformat(),
                        day_end.isoformat(),
                    ),
                )
                row = cursor.fetchone()
                stats.append(
                    {
                        "date": day_start.strftime("%m-%d"),
                        "full_date": day_start.strftime("%Y-%m-%d"),
                        "count": row["cnt"] if row else 0,
                    }
                )
        return stats

    def get_all_sessions(self, limit: int = 100) -> List[Dict]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM sessions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_tag_stats(self, days: int = 7) -> List[Tuple[str, int]]:
        start_date = datetime.now() - timedelta(days=days)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT task_tag, COUNT(*) as cnt FROM sessions
                WHERE status = ? AND session_type = ? AND started_at >= ?
                GROUP BY task_tag
                ORDER BY cnt DESC
                """,
                (SessionStatus.COMPLETED.value, SessionType.WORK.value, start_date.isoformat()),
            )
            rows = cursor.fetchall()
            return [(row["task_tag"] or "未分类", row["cnt"]) for row in rows]
