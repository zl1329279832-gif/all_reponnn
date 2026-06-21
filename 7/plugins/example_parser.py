"""
示例：自定义游戏解析插件
将此文件放入项目根目录的 plugins/ 文件夹即可自动加载。

请根据实际游戏的存档格式修改 can_parse 和 parse 方法。
"""

import os
import json
from typing import Any, Dict

from app.parsers.base_parser import BaseParser
from app.core.models import ParsedSaveData


class MyGameParser(BaseParser):
    """示例：自定义游戏存档解析器"""

    name = "MyGameParser"
    description = "我的自定义游戏存档解析器"
    file_extensions = [".mysav", ".mygame"]
    game_identifiers = ["MyAwesomeGame"]

    def can_parse(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.file_extensions:
            return False
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(512)
                return "MyAwesomeGame" in head or "game_version" in head
        except Exception:
            return False

    def parse(self, file_path: str) -> ParsedSaveData:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        except Exception as e:
            return ParsedSaveData(raw_text=f"[读取失败: {e}]")

        try:
            data: Dict[str, Any] = json.loads(raw_text)
        except Exception:
            return ParsedSaveData(raw_text=raw_text)

        result = ParsedSaveData()
        result.raw_text = json.dumps(data, ensure_ascii=False, indent=2)
        result.character_name = data.get("player", {}).get("name")
        result.level = str(data.get("player", {}).get("level", ""))
        result.chapter = data.get("story", {}).get("current_chapter")
        result.playtime = data.get("stats", {}).get("playtime")
        result.fields = {
            k: str(v) for k, v in data.items()
            if not isinstance(v, (dict, list))
        }
        return result
