from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QSpinBox, QPushButton,
    QLabel, QFrame, QMessageBox,
)

from core.models import PRESETS, DEFAULT_PRESET
from core.timer import PomodoroTimer


class SettingsPage(QWidget):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("设置")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(12)

        self.work_spin = QSpinBox()
        self.work_spin.setRange(1, 120)
        self.work_spin.setValue(25)
        self.work_spin.setSuffix(" 分钟")
        form.addRow("默认工作时长", self.work_spin)

        self.break_spin = QSpinBox()
        self.break_spin.setRange(1, 30)
        self.break_spin.setValue(5)
        self.break_spin.setSuffix(" 分钟")
        form.addRow("默认休息时长", self.break_spin)

        self.long_break_spin = QSpinBox()
        self.long_break_spin.setRange(1, 60)
        self.long_break_spin.setValue(15)
        self.long_break_spin.setSuffix(" 分钟")
        form.addRow("长休息时长", self.long_break_spin)

        layout.addLayout(form)

        note = QLabel(
            "注意：修改默认工作时长只影响新建计时器的默认值，\n"
            "主界面的预设下拉框选择会覆盖此默认值。"
        )
        note.setStyleSheet("color: #888; font-size: 11px; padding: 8px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch(1)

        save_btn = QPushButton("保存设置")
        save_btn.setStyleSheet("""
            QPushButton { background: #2d7ff9; color: white; padding: 8px 20px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #1e6ee0; }
        """)
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

    def _on_save(self):
        self.settings_changed.emit()
        QMessageBox.information(self, "设置已保存", "设置已保存，下次启动默认工作时长生效。")

    def get_default_work_minutes(self) -> int:
        return self.work_spin.value()

    def get_break_minutes(self) -> int:
        return self.break_spin.value()

    def get_long_break_minutes(self) -> int:
        return self.long_break_spin.value()
