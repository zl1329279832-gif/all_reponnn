from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)

from ..core.compare import CompareResult, LineDiff


class TextDiffPanel(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._result: Optional[CompareResult] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(16)

        self.lbl_a = QLabel()
        self.lbl_a.setWordWrap(True)
        fa = QFont()
        fa.setBold(True)
        self.lbl_a.setFont(fa)

        arrow = QLabel("⇄")
        af = QFont()
        af.setPointSize(af.pointSize() + 4)
        arrow.setFont(af)
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setFixedWidth(30)

        self.lbl_b = QLabel()
        self.lbl_b.setWordWrap(True)
        fb = QFont()
        fb.setBold(True)
        self.lbl_b.setFont(fb)

        header.addWidget(self.lbl_a, 1)
        header.addWidget(arrow)
        header.addWidget(self.lbl_b, 1)
        layout.addLayout(header)

        self.summary_label = QLabel()
        sf = QFont()
        sf.setPointSize(sf.pointSize() - 1)
        self.summary_label.setFont(sf)
        layout.addWidget(self.summary_label)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["行号 A", "行号 B", "变更", "内容"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setAlternatingRowColors(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(24)
        mono_font = QFont("Consolas")
        mono_font.setStyleHint(QFont.StyleHint.TypeWriter)
        mono_font.setPointSize(mono_font.pointSize() - 1)
        self.table.setFont(mono_font)
        layout.addWidget(self.table, 1)

        self.set_result(None)

    def set_result(self, result: Optional[CompareResult]) -> None:
        self._result = result
        if result is None:
            self.lbl_a.setText("（未选择存档 A）")
            self.lbl_b.setText("（未选择存档 B）")
            self.summary_label.setText("")
            self.table.setRowCount(0)
            return

        src_a = result.source_a
        src_b = result.source_b
        self.lbl_a.setText(src_a.label)
        self.lbl_b.setText(src_b.label)

        diff_count = result.line_diff_count
        if diff_count == 0:
            self.summary_label.setText("✅ 文本内容完全一致")
            self.summary_label.setStyleSheet("color: #2e7d32;")
        else:
            self.summary_label.setText(f"⚠️  共 {diff_count} 行有差异")
            self.summary_label.setStyleSheet("color: #c62828;")

        self._fill_table(result.line_diffs)

    def _fill_table(self, diffs: list[LineDiff]) -> None:
        self.table.setRowCount(len(diffs))
        for row, diff in enumerate(diffs):
            ln_a = QTableWidgetItem(str(diff.line_number_a) if diff.line_number_a else "")
            ln_a.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, ln_a)

            ln_b = QTableWidgetItem(str(diff.line_number_b) if diff.line_number_b else "")
            ln_b.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, ln_b)

            change_map = {
                "equal": ("", None, None),
                "add": ("+", QColor("#e8f5e9"), QColor("#2e7d32")),
                "delete": ("-", QColor("#ffebee"), QColor("#c62828")),
                "replace": ("~", QColor("#fff8e1"), QColor("#ef6c00")),
            }
            tag, bg_color, fg_color = change_map.get(diff.change_type, ("", None, None))
            ch_item = QTableWidgetItem(tag)
            ch_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if bg_color:
                ch_item.setBackground(QBrush(bg_color))
            if fg_color:
                ch_item.setForeground(QBrush(fg_color))
                bold_font = QFont(self.table.font())
                bold_font.setBold(True)
                ch_item.setFont(bold_font)
            self.table.setItem(row, 2, ch_item)

            content_item = QTableWidgetItem(diff.content)
            if bg_color:
                content_item.setBackground(QBrush(bg_color))
            if fg_color:
                content_item.setForeground(QBrush(fg_color))
                bold_font = QFont(self.table.font())
                bold_font.setBold(True)
                content_item.setFont(bold_font)
            self.table.setItem(row, 3, content_item)

        self.table.scrollToTop()
