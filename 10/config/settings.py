import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List


@dataclass
class AppSettings:
    work_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    long_break_interval: int = 4
    strict_mode: bool = False
    auto_start: bool = False
    play_sound: bool = True
    show_notification: bool = True
    task_tags: List[str] = field(default_factory=lambda: ["工作", "学习", "阅读", "写作", "其他"])
    duration_presets: List[int] = field(default_factory=lambda: [15, 25, 45, 60])

    def to_dict(self) -> dict:
        return asdict(self)


class SettingsManager:
    def __init__(self, config_dir: str | None = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".pomodoro_app"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.config_dir / "settings.json"
        self.settings = self._load()

    def _load(self) -> AppSettings:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return AppSettings(**data)
            except (json.JSONDecodeError, TypeError, ValueError):
                return AppSettings()
        return AppSettings()

    def save(self) -> None:
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.settings.to_dict(), f, ensure_ascii=False, indent=2)

    def get(self) -> AppSettings:
        return self.settings

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        self.save()

    def add_tag(self, tag: str) -> None:
        tag = tag.strip()
        if tag and tag not in self.settings.task_tags:
            self.settings.task_tags.append(tag)
            self.save()

    def remove_tag(self, tag: str) -> None:
        if tag in self.settings.task_tags:
            self.settings.task_tags.remove(tag)
            self.save()

    def get_db_path(self) -> Path:
        return self.config_dir / "pomodoro.db"
