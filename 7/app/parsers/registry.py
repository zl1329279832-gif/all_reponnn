import importlib.util
import os
import sys
from typing import List, Optional, Type

from .base_parser import BaseParser
from .json_parser import JsonParser
from .ini_parser import IniParser
from ..core.database import get_plugins_dir
from ..core.models import ParsedSaveData


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: List[BaseParser] = []
        self._register_builtin()
        self._register_plugins()

    def _register_builtin(self) -> None:
        self._parsers.append(JsonParser())
        self._parsers.append(IniParser())

    def _register_plugins(self) -> None:
        plugins_dir = get_plugins_dir()
        if not os.path.isdir(plugins_dir):
            return
        init_file = os.path.join(plugins_dir, "__init__.py")
        if not os.path.exists(init_file):
            try:
                with open(init_file, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception:
                pass
        if plugins_dir not in sys.path:
            sys.path.insert(0, os.path.dirname(plugins_dir))
        for filename in os.listdir(plugins_dir):
            if filename.startswith("_") or not filename.endswith(".py"):
                continue
            filepath = os.path.join(plugins_dir, filename)
            module_name = f"plugins.{filename[:-3]}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, filepath)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseParser)
                        and attr is not BaseParser
                    ):
                        try:
                            self._parsers.append(attr())
                        except Exception:
                            pass
            except Exception:
                continue

    def find_parser(self, file_path: str) -> Optional[BaseParser]:
        for parser in self._parsers:
            try:
                if parser.can_parse(file_path):
                    return parser
            except Exception:
                continue
        return None

    def parse(self, file_path: str) -> ParsedSaveData:
        parser = self.find_parser(file_path)
        if parser is not None:
            try:
                return parser.parse(file_path)
            except Exception as e:
                return ParsedSaveData(raw_text=f"[解析失败: {e}]")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        except Exception as e:
            return ParsedSaveData(raw_text=f"[读取失败: {e}]")
        return ParsedSaveData(raw_text=raw_text)

    @property
    def parsers(self) -> List[BaseParser]:
        return list(self._parsers)


_parser_registry: Optional[ParserRegistry] = None


def get_parser_registry() -> ParserRegistry:
    global _parser_registry
    if _parser_registry is None:
        _parser_registry = ParserRegistry()
    return _parser_registry
