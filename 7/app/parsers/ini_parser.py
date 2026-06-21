import configparser
import os
from typing import Dict, Any

from .base_parser import BaseParser
from ..core.models import ParsedSaveData


class IniParser(BaseParser):
    name = "IniParser"
    description = "通用 INI 配置存档解析器"
    file_extensions = [".ini", ".cfg", ".conf", ".sav", ".save"]

    def can_parse(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in self.file_extensions:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(4096)
                    if "[General]" in content or "[Save]" in content or "=" in content:
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

        config = configparser.ConfigParser(interpolation=None)
        try:
            config.read_string(raw_text)
        except Exception:
            try:
                config.read_string("[root]\n" + raw_text)
            except Exception:
                return ParsedSaveData(raw_text=raw_text)

        data: Dict[str, Any] = {}
        for section in config.sections():
            data[section] = dict(config.items(section))
        if not data and config.defaults():
            data["DEFAULT"] = dict(config.defaults())

        common = self.extract_common_fields(data)

        lines: list[str] = []
        for section, values in data.items():
            lines.append(f"[{section}]")
            for k, v in values.items():
                lines.append(f"{k} = {v}")
            lines.append("")
        pretty_text = "\n".join(lines)

        result = ParsedSaveData(raw_text=pretty_text)
        result.character_name = common["character_name"]
        result.level = common["level"]
        result.chapter = common["chapter"]
        result.playtime = common["playtime"]
        flat: Dict[str, str] = {}
        for section, values in data.items():
            if isinstance(values, dict):
                for k, v in values.items():
                    flat[f"{section}.{k}"] = str(v)
        result.fields = flat
        return result
