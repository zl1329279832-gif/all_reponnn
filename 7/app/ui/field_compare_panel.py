from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout,
    QGroupBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView,
)

from ..core.compare import CompareResult, FieldDiff


class FieldComparePanel(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._result: Optional[CompareResult] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(16)

        self.lbl_a = QLabel()
        self.lbl_a.setWordWrap(True)
        font_a = QFont()
        font_a.setBold(True)
        self.lbl_a.setFont(font_a)

        arrow = QLabel("⇄")
        arrow_font = QFont()
        arrow_font.setPointSize(arrow_font.pointSize() + 4)
        arrow.setFont(arrow_font)
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setFixedWidth(30)

        self.lbl_b = QLabel()
        self.lbl_b.setWordWrap(True)
        font_b = QFont()
        font_b.setBold(True)
        self.lbl_b.setFont(font_b)

        header.addWidget(self.lbl_a, 1)
        header.addWidget(arrow)
        header.addWidget(self.lbl_b, 1)
        layout.addLayout(header)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        sum_font = QFont()
        sum_font.setPointSize(sum_font.pointSize() - 1)
        self.summary_label.setFont(sum_font)
        layout.addWidget(self.summary_label)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["字段", "存档 A", "存档 B"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setAlternatingRowColors(True)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(28)
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
        html_a = f"{src_a.label}<br><span style='font-size:10px;color:#888;'>{src_a.timestamp} {src_a.note}</span>"
        html_b = f"{src_b.label}<br><span style='font-size:10px;color:#888;'>{src_b.timestamp} {src_b.note}</span>"
        self.lbl_a.setText(html_a)
        self.lbl_b.setText(html_b)

        diff_count = result.field_diff_count
        total = len(result.field_diffs)
        if diff_count == 0:
            self.summary_label.setText(f"✅ 完全一致（共 {total} 个字段）")
            self.summary_label.setStyleSheet("color: #2e7d32;")
        else:
            self.summary_label.setText(f"⚠️  共 {diff_count} 个字段有差异（总 {total} 个字段）")
            self.summary_label.setStyleSheet("color: #c62828;")

        self._fill_table(result.field_diffs)

    def _fill_table(self, diffs: list[FieldDiff]) -> None:
        self.table.setRowCount(len(diffs))
        for row, diff in enumerate(diffs):
            label_item = QTableWidgetItem(diff.label)
            label_font = QFont()
            if diff.is_different:
                label_font.setBold(True)
            label_item.setFont(label_font)
            self.table.setItem(row, 0, label_item)

            a_item = QTableWidgetItem(diff.display_a)
            b_item = QTableWidgetItem(diff.display_b)

            if diff.is_different:
                diff_bg = QBrush(QColor("#ffebee"))
                diff_fg = QBrush(QColor("#c62828"))
                a_item.setBackground(diff_bg)
                a_item.setForeground(diff_fg)
                b_item.setBackground(diff_bg)
                b_item.setForeground(diff_fg)
                a_font = QFont()
                a_font.setBold(True)
                a_item.setFont(a_font)
                b_item.setFont(a_font)

            self.table.setItem(row, 1, a_item)
            self.table.setItem(row, 2, b_item)

        self.table.scrollToTop()
