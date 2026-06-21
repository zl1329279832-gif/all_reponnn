from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class SaveSlot:
    id: Optional[int] = None
    path: str = ""
    game_name: str = ""
    note: str = ""
    last_modified: float = 0.0
    file_size: int = 0
    scan_path_id: Optional[int] = None
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())

    @property
    def last_modified_str(self) -> str:
        if self.last_modified == 0:
            return "-"
        return datetime.fromtimestamp(self.last_modified).strftime("%Y-%m-%d %H:%M:%S")

    @property
    def file_size_str(self) -> str:
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


@dataclass
class ScanPath:
    id: Optional[int] = None
    path: str = ""
    label: str = ""
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Backup:
    id: Optional[int] = None
    save_slot_id: int = 0
    path: str = ""
    timestamp: float = 0.0
    note: str = ""

    @property
    def timestamp_str(self) -> str:
        if self.timestamp == 0:
            return "-"
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class ParsedSaveData:
    raw_text: str = ""
    fields: Dict[str, Any] = field(default_factory=dict)
    character_name: Optional[str] = None
    level: Optional[str] = None
    chapter: Optional[str] = None
    playtime: Optional[str] = None

    @property
    def preview_lines(self) -> List[str]:
        lines = self.raw_text.splitlines()
        return lines[:20]
