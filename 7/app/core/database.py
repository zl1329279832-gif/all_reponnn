import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional, Generator

from .models import SaveSlot, ScanPath, Backup


def _get_app_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_db_path() -> str:
    return os.path.join(_get_app_dir(), "save_manager.db")


def get_backups_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    backups = os.path.join(base, "backups")
    os.makedirs(backups, exist_ok=True)
    return backups


def get_plugins_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    plugins = os.path.join(base, "plugins")
    os.makedirs(plugins, exist_ok=True)
    return plugins


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                label TEXT DEFAULT '',
                created_at REAL NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS save_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                game_name TEXT DEFAULT '',
                note TEXT DEFAULT '',
                last_modified REAL DEFAULT 0,
                file_size INTEGER DEFAULT 0,
                scan_path_id INTEGER,
                created_at REAL NOT NULL,
                FOREIGN KEY (scan_path_id) REFERENCES scan_paths(id) ON DELETE SET NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                save_slot_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                timestamp REAL NOT NULL,
                note TEXT DEFAULT '',
                FOREIGN KEY (save_slot_id) REFERENCES save_slots(id) ON DELETE CASCADE
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_slots_modified ON save_slots(last_modified)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_slots_game ON save_slots(game_name)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_backups_slot ON backups(save_slot_id)")


def add_scan_path(path: str, label: str = "") -> ScanPath:
    path = os.path.abspath(path)
    now = datetime.now().timestamp()
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO scan_paths (path, label, created_at) VALUES (?, ?, ?)",
            (path, label, now),
        )
        c.execute("SELECT * FROM scan_paths WHERE path = ?", (path,))
        row = c.fetchone()
        return ScanPath(id=row["id"], path=row["path"], label=row["label"], created_at=row["created_at"])


def remove_scan_path(scan_path_id: int) -> None:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM scan_paths WHERE id = ?", (scan_path_id,))


def list_scan_paths() -> List[ScanPath]:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM scan_paths ORDER BY created_at DESC")
        return [
            ScanPath(id=r["id"], path=r["path"], label=r["label"], created_at=r["created_at"])
            for r in c.fetchall()
        ]


def upsert_save_slot(slot: SaveSlot) -> SaveSlot:
    now = datetime.now().timestamp()
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO save_slots (path, game_name, note, last_modified, file_size, scan_path_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                game_name=excluded.game_name,
                last_modified=excluded.last_modified,
                file_size=excluded.file_size,
                scan_path_id=excluded.scan_path_id
            """,
            (slot.path, slot.game_name, slot.note, slot.last_modified, slot.file_size, slot.scan_path_id, now),
        )
        c.execute("SELECT * FROM save_slots WHERE path = ?", (slot.path,))
        row = c.fetchone()
        return SaveSlot(
            id=row["id"],
            path=row["path"],
            game_name=row["game_name"],
            note=row["note"],
            last_modified=row["last_modified"],
            file_size=row["file_size"],
            scan_path_id=row["scan_path_id"],
            created_at=row["created_at"],
        )


def update_save_slot_note(slot_id: int, note: str) -> None:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE save_slots SET note = ? WHERE id = ?", (note, slot_id))


def delete_save_slot(slot_id: int) -> None:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM save_slots WHERE id = ?", (slot_id,))


def list_save_slots(keyword: str = "", sort_by: str = "modified_desc") -> List[SaveSlot]:
    order_map = {
        "modified_desc": "last_modified DESC",
        "modified_asc": "last_modified ASC",
        "name_asc": "game_name ASC",
        "name_desc": "game_name DESC",
        "size_desc": "file_size DESC",
    }
    order = order_map.get(sort_by, "last_modified DESC")
    with get_conn() as conn:
        c = conn.cursor()
        if keyword:
            like = f"%{keyword}%"
            c.execute(
                f"SELECT * FROM save_slots WHERE game_name LIKE ? OR path LIKE ? OR note LIKE ? ORDER BY {order}",
                (like, like, like),
            )
        else:
            c.execute(f"SELECT * FROM save_slots ORDER BY {order}")
        return [
            SaveSlot(
                id=r["id"],
                path=r["path"],
                game_name=r["game_name"],
                note=r["note"],
                last_modified=r["last_modified"],
                file_size=r["file_size"],
                scan_path_id=r["scan_path_id"],
                created_at=r["created_at"],
            )
            for r in c.fetchall()
        ]


def add_backup(save_slot_id: int, path: str, note: str = "") -> Backup:
    now = datetime.now().timestamp()
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO backups (save_slot_id, path, timestamp, note) VALUES (?, ?, ?, ?)",
            (save_slot_id, path, now, note),
        )
        backup_id = c.lastrowid
        return Backup(id=backup_id, save_slot_id=save_slot_id, path=path, timestamp=now, note=note)


def list_backups(save_slot_id: int) -> List[Backup]:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM backups WHERE save_slot_id = ? ORDER BY timestamp DESC", (save_slot_id,))
        return [
            Backup(id=r["id"], save_slot_id=r["save_slot_id"], path=r["path"], timestamp=r["timestamp"], note=r["note"])
            for r in c.fetchall()
        ]


def delete_backup(backup_id: int) -> None:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
