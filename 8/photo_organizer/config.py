import json
import os
import sys
import sqlite3

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_APP_DIR, "data")


def _can_sqlite_write(directory):
    try:
        os.makedirs(directory, exist_ok=True)
        test_db = os.path.join(directory, "_test_write.db")
        conn = sqlite3.connect(test_db)
        conn.execute("CREATE TABLE IF NOT EXISTS _t(id INTEGER)")
        conn.commit()
        conn.close()
        os.remove(test_db)
        return True
    except Exception:
        return False


if sys.platform == "win32":
    _LOCAL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "PhotoOrganizer")
    if _LOCAL_DIR and _can_sqlite_write(_LOCAL_DIR):
        _DATA_DIR = _LOCAL_DIR

CONFIG_PATH = os.path.join(_DATA_DIR, "config.json")

DEFAULT_CONFIG = {
    "root_dirs": [],
    "window_width": 1280,
    "window_height": 800,
    "sidebar_width": 480,
    "thumbnail_size": 120,
}


def get_data_dir():
    return _DATA_DIR


def _ensure_dir():
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)


def load_config():
    _ensure_dir()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged.update(saved)
            return merged
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    _ensure_dir()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
