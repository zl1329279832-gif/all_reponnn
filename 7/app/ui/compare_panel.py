from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget,
    QMessageBox,
)

from ..core.compare import (
    CompareResult, CompareSource, compare_sources,
)
from .field_compare_panel import FieldComparePanel
from .text_diff_panel import TextDiffPanel


class ComparePanel(QWidget):
    back_to_preview_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._result: Optional[CompareResult] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_bar = QHBoxLayout()
        title_bar.setSpacing(10)
        title_label = QLabel("存档对比")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        title_label.setFont(title_font)
        title_bar.addWidget(title_label)
        title_bar.addStretch(1)
        self.btn_back = QPushButton("← 返回预览")
        self.btn_back.setMinimumHeight(32)
        self.btn_back.clicked.connect(self.back_to_preview_requested.emit)
        title_bar.addWidget(self.btn_back)
        layout.addLayout(title_bar)

        self.tabs = QTabWidget()
        self.field_panel = FieldComparePanel()
        self.text_panel = TextDiffPanel()
        self.tabs.addTab(self.field_panel, "字段对比")
        self.tabs.addTab(self.text_panel, "文本 Diff")
        layout.addWidget(self.tabs, 1)

        self.hint_label = QLabel("")
        hint_font = QFont()
        hint_font.setPointSize(hint_font.pointSize() - 1)
        hint_font.setItalic(True)
        self.hint_label.setFont(hint_font)
        layout.addWidget(self.hint_label)

        self._set_empty()

    def _set_empty(self) -> None:
        self.tabs.setEnabled(False)
        self.hint_label.setText("请在左侧列表选中两个存档（按住 Ctrl 多选），或在右侧备份列表选一个备份点击「与当前对比」")
        self.field_panel.set_result(None)
        self.text_panel.set_result(None)

    def compare(self, source_a: CompareSource, source_b: CompareSource) -> bool:
        if source_a.path == source_b.path:
            QMessageBox.warning(self, "提示", "不能对比同一个存档。请选择两个不同的存档或备份。")
            return False
        try:
            result = compare_sources(source_a, source_b)
        except Exception as e:
            QMessageBox.critical(self, "对比失败", f"解析或对比存档时出错:\n{e}")
            return False
        self._result = result
        self.tabs.setEnabled(True)
        self.field_panel.set_result(result)
        self.text_panel.set_result(result)

        field_diffs = result.field_diff_count
        line_diffs = result.line_diff_count
        if field_diffs == 0 and line_diffs == 0:
            self.hint_label.setText("两个存档完全一致。没有检测到任何差异。")
            self.hint_label.setStyleSheet("color: #2e7d32;")
        else:
            msg = f"字段差异: {field_diffs} 项 | 文本差异: {line_diffs} 行"
            if field_diffs > 0:
                msg += "（差异项在字段对比中高亮显示为红色）"
            self.hint_label.setText(msg)
            self.hint_label.setStyleSheet("color: #c62828;")
        return True

    def clear(self) -> None:
        self._result = None
        self._set_empty()

    @property
    def result(self) -> Optional[CompareResult]:
        return self._result
