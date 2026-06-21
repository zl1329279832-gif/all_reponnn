import sqlite3
import os
from datetime import datetime
from . import config as config_mod

DB_PATH = os.path.join(config_mod.get_data_dir(), "photos.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    capture_time TEXT,
    camera_model TEXT,
    title TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    file_size INTEGER,
    file_mtime TEXT,
    width INTEGER,
    height INTEGER,
    thumbnail_path TEXT,
    scanned_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_photos_capture_time ON photos(capture_time);
CREATE INDEX IF NOT EXISTS idx_photos_filename ON photos(filename);
CREATE INDEX IF NOT EXISTS idx_photos_filepath ON photos(filepath);
"""


def _ensure_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_connection():
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.close()


def upsert_photo(conn, photo: dict):
    existing = conn.execute(
        "SELECT id FROM photos WHERE filepath = ?", (photo["filepath"],)
    ).fetchone()
    if existing:
        fields = {k: v for k, v in photo.items() if k != "filepath"}
        sets = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [photo["filepath"]]
        conn.execute(f"UPDATE photos SET {sets} WHERE filepath = ?", values)
    else:
        cols = ", ".join(photo.keys())
        placeholders = ", ".join("?" for _ in photo)
        conn.execute(
            f"INSERT INTO photos ({cols}) VALUES ({placeholders})",
            list(photo.values()),
        )


def update_title_notes(conn, photo_id: int, title: str, notes: str):
    conn.execute(
        "UPDATE photos SET title = ?, notes = ? WHERE id = ?",
        (title, notes, photo_id),
    )
    conn.commit()


def search_photos(conn, keyword: str = "", date_from: str = "", date_to: str = ""):
    query = "SELECT * FROM photos WHERE 1=1"
    params = []
    if keyword:
        query += " AND (filename LIKE ? OR title LIKE ? OR notes LIKE ?)"
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw])
    if date_from:
        query += " AND capture_time >= ?"
        params.append(date_from)
    if date_to:
        query += " AND capture_time <= ?"
        params.append(date_to + "T23:59:59")
    query += " ORDER BY capture_time DESC, filename"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_all_photos(conn):
    rows = conn.execute(
        "SELECT * FROM photos ORDER BY capture_time DESC, filename"
    ).fetchall()
    return [dict(r) for r in rows]


def get_photo_by_id(conn, photo_id: int):
    row = conn.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
    return dict(row) if row else None


def delete_by_filepath(conn, filepath: str):
    conn.execute("DELETE FROM photos WHERE filepath = ?", (filepath,))
    conn.commit()


def update_filepath(conn, old_path: str, new_path: str, new_filename: str):
    conn.execute(
        "UPDATE photos SET filepath = ?, filename = ? WHERE filepath = ?",
        (new_path, new_filename, old_path),
    )
    conn.commit()
