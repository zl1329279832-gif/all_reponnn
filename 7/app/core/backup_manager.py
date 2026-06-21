import os
import shutil
import stat
from datetime import datetime
from typing import List

from . import database as db
from .database import get_backups_dir
from .models import SaveSlot, Backup


def _timestamp_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_name(name: str) -> str:
    keep = "-_.() "
    return "".join(c if c.isalnum() or c in keep else "_" for c in name).strip() or "save"


def _handle_readonly(func, path, exc_info) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def create_backup(slot: SaveSlot, note: str = "") -> Backup:
    if not os.path.exists(slot.path):
        raise FileNotFoundError(f"存档文件不存在: {slot.path}")

    safe_game = _safe_name(slot.game_name or "unknown")
    ts = _timestamp_str()
    backup_subdir = os.path.join(get_backups_dir(), f"{safe_game}_{ts}")
    os.makedirs(backup_subdir, exist_ok=True)

    src = slot.path
    if os.path.isfile(src):
        dest = os.path.join(backup_subdir, os.path.basename(src))
        shutil.copy2(src, dest)
    else:
        dest = os.path.join(backup_subdir, os.path.basename(os.path.normpath(src)) or "save_dir")
        shutil.copytree(src, dest, symlinks=False, ignore=None, dirs_exist_ok=True)

    return db.add_backup(slot.id, backup_subdir, note)


def restore_backup(slot: SaveSlot, backup: Backup) -> None:
    if not os.path.exists(backup.path):
        raise FileNotFoundError(f"备份目录不存在: {backup.path}")

    src_files = os.listdir(backup.path)
    if not src_files:
        raise ValueError("备份目录为空")

    src_entry = os.path.join(backup.path, src_files[0])
    dest_parent = os.path.dirname(os.path.abspath(slot.path))
    os.makedirs(dest_parent, exist_ok=True)

    if os.path.exists(slot.path):
        if os.path.isfile(slot.path):
            try:
                os.remove(slot.path)
            except PermissionError:
                os.chmod(slot.path, stat.S_IWRITE)
                os.remove(slot.path)
        else:
            shutil.rmtree(slot.path, onerror=_handle_readonly)

    if os.path.isfile(src_entry):
        shutil.copy2(src_entry, slot.path)
    else:
        shutil.copytree(src_entry, slot.path, symlinks=False, dirs_exist_ok=True)


def list_slot_backups(slot: SaveSlot) -> List[Backup]:
    if slot.id is None:
        return []
    return db.list_backups(slot.id)


def delete_backup_file(backup: Backup) -> None:
    if os.path.isdir(backup.path):
        shutil.rmtree(backup.path, onerror=_handle_readonly)
    elif os.path.isfile(backup.path):
        try:
            os.remove(backup.path)
        except PermissionError:
            os.chmod(backup.path, stat.S_IWRITE)
            os.remove(backup.path)
    if backup.id is not None:
        db.delete_backup(backup.id)
