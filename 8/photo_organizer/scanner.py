import os
import threading
import shutil
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from . import config as config_mod

THUMB_DIR = os.path.join(config_mod.get_data_dir(), "thumbnails")

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png"}


def _ensure_thumb_dir():
    os.makedirs(THUMB_DIR, exist_ok=True)


def _get_exif_data(image: Image.Image):
    exif_data = {}
    raw = image.getexif()
    if not raw:
        return exif_data
    for tag_id, value in raw.items():
        tag = TAGS.get(tag_id, tag_id)
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8", errors="replace")
            except Exception:
                value = str(value)
        exif_data[tag] = value
    return exif_data


def _extract_capture_time(exif_data: dict, file_mtime: float):
    for key in ("DateTimeOriginal", "DateTime", "DateTimeDigitized"):
        if key in exif_data:
            raw = exif_data[key]
            try:
                return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S").isoformat()
            except (ValueError, TypeError):
                continue
    return datetime.fromtimestamp(file_mtime).isoformat()


def _extract_camera_model(exif_data: dict):
    for key in ("Model", "CameraModelName", "Make"):
        if key in exif_data:
            val = str(exif_data[key]).strip()
            if val:
                return val
    return ""


def _generate_thumbnail(filepath: str, thumb_size: int = 200):
    _ensure_thumb_dir()
    try:
        img = Image.open(filepath)
        img.thumbnail((thumb_size, thumb_size), Image.LANCZOS)
        ext = os.path.splitext(filepath)[1].lower()
        thumb_name = (
            filepath.replace(":", "_").replace("\\", "_").replace("/", "_")
        )
        thumb_name = thumb_name + f".thumb{ext}"
        thumb_path = os.path.join(THUMB_DIR, thumb_name)
        img.save(thumb_path, quality=85)
        return thumb_path, img.width, img.height
    except Exception:
        return None, None, None


def scan_file(filepath: str):
    stat = os.stat(filepath)
    filename = os.path.basename(filepath)
    photo = {
        "filepath": filepath,
        "filename": filename,
        "capture_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "camera_model": "",
        "title": "",
        "notes": "",
        "file_size": stat.st_size,
        "file_mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "width": None,
        "height": None,
        "thumbnail_path": "",
        "scanned_at": datetime.now().isoformat(),
    }
    error_msg = None
    try:
        img = Image.open(filepath)
        photo["width"] = img.width
        photo["height"] = img.height
        exif_data = _get_exif_data(img)
        if exif_data:
            photo["capture_time"] = _extract_capture_time(exif_data, stat.st_mtime)
            photo["camera_model"] = _extract_camera_model(exif_data)
        thumb_path, w, h = _generate_thumbnail(filepath)
        if thumb_path:
            photo["thumbnail_path"] = thumb_path
        img.close()
    except Exception as e:
        error_msg = f"解析失败: {e}"
    return photo, error_msg


def scan_directory(root_dirs: list, callback=None, cancel_event=None):
    file_list = []
    for root_dir in root_dirs:
        for dirpath, _, filenames in os.walk(root_dir):
            if cancel_event and cancel_event.is_set():
                return file_list
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in SUPPORTED_EXTS:
                    file_list.append(os.path.join(dirpath, fname))
    return file_list


class ScanWorker(threading.Thread):
    def __init__(self, root_dirs, db_module, on_progress=None, on_done=None, on_error=None):
        super().__init__(daemon=True)
        self.root_dirs = root_dirs
        self.db_module = db_module
        self.on_progress = on_progress
        self.on_done = on_done
        self.on_error = on_error
        self.cancel_event = threading.Event()
        self.total = 0
        self.processed = 0

    def run(self):
        try:
            file_list = scan_directory(self.root_dirs, cancel_event=self.cancel_event)
            self.total = len(file_list)
            if self.cancel_event.is_set():
                return
            conn = self.db_module.get_connection()
            for i, filepath in enumerate(file_list):
                if self.cancel_event.is_set():
                    conn.close()
                    return
                try:
                    photo, parse_err = scan_file(filepath)
                    self.db_module.upsert_photo(conn, photo)
                    if parse_err and self.on_error:
                        self.on_error(filepath, parse_err)
                except Exception as e:
                    if self.on_error:
                        self.on_error(filepath, str(e))
                self.processed = i + 1
                if self.on_progress:
                    self.on_progress(self.processed, self.total, filepath)
            conn.commit()
            conn.close()
            if self.on_done:
                self.on_done()
        except Exception as e:
            if self.on_error:
                self.on_error("", str(e))

    def cancel(self):
        self.cancel_event.set()


def batch_move_to_album(photo_paths: list, album_dir: str):
    results = {"success": [], "failed": []}
    os.makedirs(album_dir, exist_ok=True)
    for old_path in photo_paths:
        try:
            filename = os.path.basename(old_path)
            new_path = os.path.join(album_dir, filename)
            if os.path.exists(new_path) and old_path != new_path:
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(new_path):
                    new_path = os.path.join(album_dir, f"{base}_{counter}{ext}")
                    counter += 1
            shutil.move(old_path, new_path)
            results["success"].append((old_path, new_path))
        except Exception as e:
            results["failed"].append((old_path, str(e)))
    return results


def batch_rename_by_date(photo_paths: list, date_format: str = "%Y%m%d_%H%M%S"):
    results = {"success": [], "failed": []}
    for old_path in photo_paths:
        try:
            dirname = os.path.dirname(old_path)
            ext = os.path.splitext(old_path)[1]
            stat = os.stat(old_path)
            img = Image.open(old_path)
            exif_data = _get_exif_data(img)
            capture = _extract_capture_time(exif_data, stat.st_mtime)
            img.close()
            dt = datetime.fromisoformat(capture)
            new_name = dt.strftime(date_format) + ext
            new_path = os.path.join(dirname, new_name)
            if os.path.exists(new_path) and old_path != new_path:
                base_new = os.path.splitext(new_name)[0]
                counter = 1
                while os.path.exists(new_path):
                    new_path = os.path.join(dirname, f"{base_new}_{counter}{ext}")
                    counter += 1
            os.rename(old_path, new_path)
            results["success"].append((old_path, new_path))
        except Exception as e:
            results["failed"].append((old_path, str(e)))
    return results
