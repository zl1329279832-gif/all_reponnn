from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from ..core.models import ParsedSaveData


class BaseParser(ABC):
    """
    自定义游戏解析插件基类。

    要添加新游戏的解析支持，继承此类并实现所有抽象方法，
    然后将 .py 文件放入项目根目录的 plugins/ 文件夹即可自动加载。
    """

    name: str = "BaseParser"
    description: str = "Base parser class"
    file_extensions: List[str] = []
    game_identifiers: List[str] = []

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """
        判断该解析器是否能处理指定文件。

        Args:
            file_path: 存档文件的绝对路径

        Returns:
            如果能解析返回 True，否则 False
        """
        raise NotImplementedError

    @abstractmethod
    def parse(self, file_path: str) -> ParsedSaveData:
        """
        解析存档文件并返回结构化数据。

        Args:
            file_path: 存档文件的绝对路径

        Returns:
            ParsedSaveData 对象，包含解析出的字段和原始文本预览
        """
        raise NotImplementedError

    def extract_common_fields(self, data: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        从字典中尝试提取角色名、等级、章节、游玩时长等通用字段。
        子类可以覆盖此方法以适配特定游戏的字段命名。
        """
        result: Dict[str, Optional[str]] = {
            "character_name": None,
            "level": None,
            "chapter": None,
            "playtime": None,
        }

        name_keys = ["name", "player_name", "character_name", "角色名", "姓名", "char_name", "hero_name"]
        level_keys = ["level", "lv", "等级", "角色等级", "char_level"]
        chapter_keys = ["chapter", "stage", "章节", "进度", "quest", "scenario"]
        playtime_keys = ["playtime", "play_time", "time_played", "游玩时长", "游戏时间", "total_time", "hours"]

        def _find(data_dict: Dict[str, Any], keys: List[str]) -> Optional[str]:
            stack = [data_dict]
            while stack:
                current = stack.pop()
                if not isinstance(current, dict):
                    continue
                for k, v in current.items():
                    if isinstance(k, str) and k.lower() in [key.lower() for key in keys]:
                        if v is not None:
                            return str(v)
                    if isinstance(v, dict):
                        stack.append(v)
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                stack.append(item)
            return None

        result["character_name"] = _find(data, name_keys)
        result["level"] = _find(data, level_keys)
        result["chapter"] = _find(data, chapter_keys)
        result["playtime"] = _find(data, playtime_keys)
        return result
