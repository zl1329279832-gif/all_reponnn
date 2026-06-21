from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout, QGroupBox,
    QPlainTextEdit, QFrame,
)

from ..core.models import SaveSlot, ParsedSaveData
from ..parsers.registry import get_parser_registry


class PreviewPanel(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_slot: Optional[SaveSlot] = None
        self._parsed: Optional[ParsedSaveData] = None
        self._build_ui()
        self.set_slot(None)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_label = QLabel("存档预览")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout(info_group)
        info_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        info_layout.setHorizontalSpacing(16)
        info_layout.setVerticalSpacing(6)

        self.lbl_game = QLabel("-")
        self.lbl_game.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_path = QLabel("-")
        self.lbl_path.setWordWrap(True)
        self.lbl_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_modified = QLabel("-")
        self.lbl_size = QLabel("-")
        self.lbl_note = QLabel("-")
        self.lbl_note.setWordWrap(True)
        self.lbl_note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        info_layout.addRow("游戏:", self.lbl_game)
        info_layout.addRow("路径:", self.lbl_path)
        info_layout.addRow("修改时间:", self.lbl_modified)
        info_layout.addRow("大小:", self.lbl_size)
        info_layout.addRow("备注:", self.lbl_note)
        layout.addWidget(info_group)

        parsed_group = QGroupBox("解析字段")
        parsed_layout = QFormLayout(parsed_group)
        parsed_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        parsed_layout.setHorizontalSpacing(16)
        parsed_layout.setVerticalSpacing(6)

        self.lbl_character = QLabel("-")
        self.lbl_character.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_level = QLabel("-")
        self.lbl_level.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_chapter = QLabel("-")
        self.lbl_chapter.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_playtime = QLabel("-")
        self.lbl_playtime.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        parsed_layout.addRow("角色名:", self.lbl_character)
        parsed_layout.addRow("等级:", self.lbl_level)
        parsed_layout.addRow("章节/进度:", self.lbl_chapter)
        parsed_layout.addRow("游玩时长:", self.lbl_playtime)
        layout.addWidget(parsed_group)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        raw_label = QLabel("原始内容预览:")
        raw_font = QFont()
        raw_font.setBold(True)
        raw_label.setFont(raw_font)
        layout.addWidget(raw_label)

        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        mono_font = QFont("Consolas")
        mono_font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.preview_text.setFont(mono_font)
        layout.addWidget(self.preview_text, 1)

    def set_slot(self, slot: Optional[SaveSlot]) -> None:
        self._current_slot = slot
        if slot is None:
            self.lbl_game.setText("-")
            self.lbl_path.setText("-")
            self.lbl_modified.setText("-")
            self.lbl_size.setText("-")
            self.lbl_note.setText("-")
            self.lbl_character.setText("-")
            self.lbl_level.setText("-")
            self.lbl_chapter.setText("-")
            self.lbl_playtime.setText("-")
            self.preview_text.setPlainText("请在左侧选择一个存档以查看详情。")
            return

        self.lbl_game.setText(slot.game_name or "未知游戏")
        self.lbl_path.setText(slot.path)
        self.lbl_modified.setText(slot.last_modified_str)
        self.lbl_size.setText(slot.file_size_str)
        self.lbl_note.setText(slot.note or "-")

        registry = get_parser_registry()
        self._parsed: ParsedSaveData = registry.parse(slot.path)

        self.lbl_character.setText(self._parsed.character_name or "-")
        self.lbl_level.setText(self._parsed.level or "-")
        self.lbl_chapter.setText(self._parsed.chapter or "-")
        self.lbl_playtime.setText(self._parsed.playtime or "-")

        preview = "\n".join(self._parsed.preview_lines)
        if not preview.strip():
            preview = "[此存档为二进制格式或无法以文本方式预览]"
        self.preview_text.setPlainText(preview)
