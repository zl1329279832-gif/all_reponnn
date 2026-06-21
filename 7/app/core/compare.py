"""
存档对比工具：数据模型 + 字段对比 + 文本行级 diff
"""

import os
import difflib
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

from .models import SaveSlot, Backup, ParsedSaveData
from ..parsers.registry import get_parser_registry


@dataclass
class CompareSource:
    """对比源：可以是当前存档槽位，也可以是某个备份"""
    label: str
    path: str
    source_type: str = "slot"  # "slot" | "backup"
    game_name: str = ""
    timestamp: str = ""
    note: str = ""

    @classmethod
    def from_slot(cls, slot: SaveSlot) -> "CompareSource":
        return cls(
            label=f"[当前] {slot.game_name}",
            path=slot.path,
            source_type="slot",
            game_name=slot.game_name,
            timestamp=slot.last_modified_str,
            note=slot.note,
        )

    @classmethod
    def from_backup(cls, backup: Backup, game_name: str = "") -> "CompareSource":
        return cls(
            label=f"[备份] {backup.timestamp_str}",
            path=cls._find_backup_file(backup),
            source_type="backup",
            game_name=game_name,
            timestamp=backup.timestamp_str,
            note=backup.note,
        )

    @staticmethod
    def _find_backup_file(backup: Backup) -> str:
        if not os.path.isdir(backup.path):
            return backup.path
        entries = os.listdir(backup.path)
        if not entries:
            return backup.path
        return os.path.join(backup.path, entries[0])


@dataclass
class FieldDiff:
    """单个字段的对比结果"""
    field_name: str
    label: str
    value_a: Optional[str]
    value_b: Optional[str]
    is_different: bool

    @property
    def display_a(self) -> str:
        return self.value_a if self.value_a is not None else "-"

    @property
    def display_b(self) -> str:
        return self.value_b if self.value_b is not None else "-"


@dataclass
class LineDiff:
    """文本 diff 的单行结果"""
    line_number_a: Optional[int]
    line_number_b: Optional[int]
    content: str
    change_type: str  # "equal" | "add" | "delete" | "replace"


@dataclass
class CompareResult:
    """完整的对比结果"""
    source_a: CompareSource
    source_b: CompareSource
    parsed_a: ParsedSaveData
    parsed_b: ParsedSaveData
    field_diffs: List[FieldDiff] = field(default_factory=list)
    line_diffs: List[LineDiff] = field(default_factory=list)

    @property
    def has_field_differences(self) -> bool:
        return any(f.is_different for f in self.field_diffs)

    @property
    def field_diff_count(self) -> int:
        return sum(1 for f in self.field_diffs if f.is_different)

    @property
    def line_diff_count(self) -> int:
        return sum(1 for l in self.line_diffs if l.change_type != "equal")


# ============================================================
# 核心对比函数
# ============================================================

FIELD_DEFS: List[Tuple[str, str]] = [
    ("character_name", "角色名"),
    ("level", "等级"),
    ("chapter", "章节/进度"),
    ("playtime", "游玩时长"),
]


def _parse_source(source: CompareSource) -> ParsedSaveData:
    registry = get_parser_registry()
    return registry.parse(source.path)


def _compare_fields(a: ParsedSaveData, b: ParsedSaveData) -> List[FieldDiff]:
    diffs: List[FieldDiff] = []
    for attr_name, label in FIELD_DEFS:
        va = getattr(a, attr_name)
        vb = getattr(b, attr_name)
        is_diff = va != vb
        diffs.append(FieldDiff(
            field_name=attr_name,
            label=label,
            value_a=va,
            value_b=vb,
            is_different=is_diff,
        ))
    extra_keys = set(a.fields.keys()) | set(b.fields.keys())
    for key in sorted(extra_keys):
        if key.lower() in {"player_name", "character_name", "level", "lv",
                           "chapter", "playtime", "name"}:
            continue
        va = a.fields.get(key)
        vb = b.fields.get(key)
        sa = str(va) if va is not None else None
        sb = str(vb) if vb is not None else None
        diffs.append(FieldDiff(
            field_name=key,
            label=key,
            value_a=sa,
            value_b=sb,
            is_different=sa != sb,
        ))
    return diffs


def _compare_lines(text_a: str, text_b: str, context: int = 3) -> List[LineDiff]:
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    if not lines_a and not lines_b:
        return []

    sm = difflib.SequenceMatcher(None, lines_a, lines_b)
    result: List[LineDiff] = []
    num_a, num_b = 0, 0

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                result.append(LineDiff(
                    line_number_a=num_a + 1,
                    line_number_b=num_b + 1,
                    content=lines_a[i1 + k],
                    change_type="equal",
                ))
                num_a += 1
                num_b += 1
        elif tag == "replace":
            a_len = i2 - i1
            b_len = j2 - j1
            min_len = min(a_len, b_len)
            for k in range(min_len):
                result.append(LineDiff(
                    line_number_a=num_a + 1,
                    line_number_b=num_b + 1,
                    content=f"- {lines_a[i1 + k]}",
                    change_type="delete",
                ))
                num_a += 1
                result.append(LineDiff(
                    line_number_a=None,
                    line_number_b=num_b + 1,
                    content=f"+ {lines_b[j1 + k]}",
                    change_type="add",
                ))
                num_b += 1
            for k in range(min_len, a_len):
                result.append(LineDiff(
                    line_number_a=num_a + 1,
                    line_number_b=None,
                    content=f"- {lines_a[i1 + k]}",
                    change_type="delete",
                ))
                num_a += 1
            for k in range(min_len, b_len):
                result.append(LineDiff(
                    line_number_a=None,
                    line_number_b=num_b + 1,
                    content=f"+ {lines_b[j1 + k]}",
                    change_type="add",
                ))
                num_b += 1
        elif tag == "delete":
            for k in range(i2 - i1):
                result.append(LineDiff(
                    line_number_a=num_a + 1,
                    line_number_b=None,
                    content=f"- {lines_a[i1 + k]}",
                    change_type="delete",
                ))
                num_a += 1
        elif tag == "insert":
            for k in range(j2 - j1):
                result.append(LineDiff(
                    line_number_a=None,
                    line_number_b=num_b + 1,
                    content=f"+ {lines_b[j1 + k]}",
                    change_type="add",
                ))
                num_b += 1

    return result


def compare_sources(source_a: CompareSource, source_b: CompareSource) -> CompareResult:
    parsed_a = _parse_source(source_a)
    parsed_b = _parse_source(source_b)
    field_diffs = _compare_fields(parsed_a, parsed_b)
    line_diffs = _compare_lines(parsed_a.raw_text, parsed_b.raw_text)
    return CompareResult(
        source_a=source_a,
        source_b=source_b,
        parsed_a=parsed_a,
        parsed_b=parsed_b,
        field_diffs=field_diffs,
        line_diffs=line_diffs,
    )
