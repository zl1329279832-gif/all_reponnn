import os
import re
from typing import Callable, List, Optional

from . import database as db
from .models import SaveSlot, ScanPath


COMMON_SAVE_DIR_NAMES = [
    "save", "saves", "savegames", "save_data", "saved",
    "存档", "Save", "Saves", "SaveGames",
    "Documents", "My Games",
]

COMMON_SAVE_EXTS = [
    ".sav", ".save", ".json", ".ini", ".cfg", ".dat",
    ".bin", ".es3", ".sav.json", ".profile",
]

MAX_SAVE_DEPTH = 4


def _is_save_dir_name(dir_name: str) -> bool:
    lower = dir_name.lower()
    return lower in [d.lower() for d in COMMON_SAVE_DIR_NAMES]


def _guess_game_name(path: str) -> str:
    parts = os.path.normpath(path).split(os.sep)
    for part in reversed(parts):
        lower = part.lower()
        if lower in {"save", "saves", "savegames", "save_data", "saved", "存档", "data"}:
            continue
        if part:
            cleaned = re.sub(r"[_-]+", " ", part).strip()
            if cleaned:
                return cleaned
    return os.path.basename(path) or "未知游戏"


def _is_likely_save_file(filepath: str) -> bool:
    name = os.path.basename(filepath).lower()
    if name.startswith("."):
        return False
    ext = os.path.splitext(name)[1]
    if ext in COMMON_SAVE_EXTS:
        return True
    if "save" in name or "slot" in name or "存档" in name:
        return True
    return False


def _scan_save_dir(dirpath: str, max_depth: int, depth: int) -> List[str]:
    results: List[str] = []
    if depth > max_depth:
        return results
    try:
        entries = os.listdir(dirpath)
    except (PermissionError, OSError):
        return results
    for entry in entries:
        full = os.path.join(dirpath, entry)
        try:
            if os.path.isfile(full):
                if _is_likely_save_file(full):
                    results.append(os.path.abspath(full))
            elif os.path.isdir(full):
                lower = entry.lower()
                if lower in {"cache", "logs", "temp", "tmp", "__pycache__", "node_modules", "www", "web"}:
                    continue
                results.extend(_scan_save_dir(full, max_depth, depth + 1))
        except (PermissionError, OSError):
            continue
    return results


def _find_save_dirs(root_path: str, max_depth: int = 3, depth: int = 0) -> List[str]:
    save_dirs: List[str] = []
    if depth > max_depth:
        return save_dirs
    try:
        entries = os.listdir(root_path)
    except (PermissionError, OSError):
        return save_dirs
    for entry in entries:
        full = os.path.join(root_path, entry)
        try:
            if os.path.isdir(full):
                lower = entry.lower()
                if lower in {"cache", "logs", "temp", "tmp", "__pycache__", "node_modules", "www", "web", "binaries", "content", "movies", "audio"}:
                    continue
                if _is_save_dir_name(entry):
                    save_dirs.append(full)
                else:
                    save_dirs.extend(_find_save_dirs(full, max_depth, depth + 1))
        except (PermissionError, OSError):
            continue
    return save_dirs


def scan_path_for_saves(
    scan_path: ScanPath,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[SaveSlot]:
    root = os.path.abspath(scan_path.path)
    all_files: List[str] = []

    if _is_save_dir_name(os.path.basename(root)):
        all_files.extend(_scan_save_dir(root, MAX_SAVE_DEPTH, 0))
    else:
        save_dirs = _find_save_dirs(root)
        if not save_dirs:
            return []
        for sd in save_dirs:
            all_files.extend(_scan_save_dir(sd, MAX_SAVE_DEPTH, 0))

    total = len(all_files)
    slots: List[SaveSlot] = []
    for idx, fpath in enumerate(all_files):
        try:
            stat = os.stat(fpath)
        except (OSError, FileNotFoundError):
            continue
        slot = SaveSlot(
            path=fpath,
            game_name=_guess_game_name(fpath),
            last_modified=stat.st_mtime,
            file_size=stat.st_size,
            scan_path_id=scan_path.id,
        )
        saved = db.upsert_save_slot(slot)
        slots.append(saved)
        if progress_callback is not None:
            progress_callback(idx + 1, total)
    return slots


def scan_all_paths(
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> List[SaveSlot]:
    paths = db.list_scan_paths()
    all_slots: List[SaveSlot] = []
    for sp in paths:
        def _cb(current: int, total: int, _sp: ScanPath = sp) -> None:
            if progress_callback is not None:
                progress_callback(_sp.path, current, total)
        slots = scan_path_for_saves(sp, _cb)
        all_slots.extend(slots)
    return all_slots
