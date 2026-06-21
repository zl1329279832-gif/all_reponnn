import json
import os
from typing import Dict, Any

from .base_parser import BaseParser
from ..core.models import ParsedSaveData


class JsonParser(BaseParser):
    name = "JsonParser"
    description = "通用 JSON 存档解析器"
    file_extensions = [".json", ".sav", ".save"]

    def can_parse(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in self.file_extensions:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(4096)
                    stripped = content.strip()
                    if stripped and (stripped.startswith("{") or stripped.startswith("[")):
                        return True
            except Exception:
                pass
        return False

    def parse(self, file_path: str) -> ParsedSaveData:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        except Exception as e:
            return ParsedSaveData(raw_text=f"[读取失败: {e}]")

        data: Dict[str, Any] = {}
        try:
            data = json.loads(raw_text)
        except Exception:
            return ParsedSaveData(raw_text=raw_text)

        common = self.extract_common_fields(data if isinstance(data, dict) else {"root": data})

        preview_data = data
        if isinstance(data, dict) and len(data) > 50:
            preview_data = dict(list(data.items())[:50])
        try:
            pretty_text = json.dumps(preview_data, ensure_ascii=False, indent=2)
        except Exception:
            pretty_text = raw_text

        result = ParsedSaveData(raw_text=pretty_text)
        result.character_name = common["character_name"]
        result.level = common["level"]
        result.chapter = common["chapter"]
        result.playtime = common["playtime"]
        if isinstance(data, dict):
            result.fields = {k: str(v) for k, v in data.items() if not isinstance(v, (dict, list))}
        return result
