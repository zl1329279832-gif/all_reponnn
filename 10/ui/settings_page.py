from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QFrame,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from config.settings import AppSettings


class SettingsPage(QWidget):
    settings_changed = Signal()

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self._settings_manager = settings_manager
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        title = QLabel("设置")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        outer.addWidget(title)

        container = QFrame()
        container.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border-radius: 10px; }"
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        self._work_spin = self._make_spinbox(1, 180)
        self._short_break_spin = self._make_spinbox(1, 60)
        self._long_break_spin = self._make_spinbox(1, 120)
        self._interval_spin = self._make_spinbox(1, 12)

        self._add_row(layout, "工作时长 (分钟)", self._work_spin)
        self._add_row(layout, "短休息时长 (分钟)", self._short_break_spin)
        self._add_row(layout, "长休息时长 (分钟)", self._long_break_spin)
        self._add_row(layout, "长休息间隔 (番茄数)", self._interval_spin)

        self._strict_check = QCheckBox("严格模式 (休息期间不可跳过)")
        self._strict_check.setStyleSheet("color: #dddddd;")
        layout.addWidget(self._strict_check)

        self._auto_start_check = QCheckBox("开机自动启动 (仅记录配置)")
        self._auto_start_check.setStyleSheet("color: #dddddd;")
        layout.addWidget(self._auto_start_check)

        self._sound_check = QCheckBox("到时播放提示音")
        self._sound_check.setStyleSheet("color: #dddddd;")
        layout.addWidget(self._sound_check)

        self._notif_check = QCheckBox("到时弹出桌面通知")
        self._notif_check.setStyleSheet("color: #dddddd;")
        layout.addWidget(self._notif_check)

        tag_label = QLabel("任务标签:")
        tag_label.setStyleSheet("color: #dddddd;")
        layout.addWidget(tag_label)

        tag_row = QHBoxLayout()
        self._tag_input = QLineEdit()
        self._tag_input.setPlaceholderText("输入新标签后点击添加")
        self._tag_input.setStyleSheet(
            "QLineEdit { background-color: #3a3a3a; color: #ffffff; padding: 6px; border: 1px solid #555; border-radius: 5px; }"
        )
        add_tag_btn = QPushButton("添加")
        add_tag_btn.setStyleSheet(self._button_style())
        add_tag_btn.clicked.connect(self._add_tag)
        remove_tag_btn = QPushButton("删除选中")
        remove_tag_btn.setStyleSheet(self._button_style())
        remove_tag_btn.clicked.connect(self._remove_selected_tag)
        tag_row.addWidget(self._tag_input, 1)
        tag_row.addWidget(add_tag_btn)
        tag_row.addWidget(remove_tag_btn)
        layout.addLayout(tag_row)

        self._tag_list = QListWidget()
        self._tag_list.setStyleSheet(
            "QListWidget { background-color: #3a3a3a; color: #ffffff; border: 1px solid #555; border-radius: 5px; padding: 4px; }"
            " QListWidget::item { padding: 6px; }"
        )
        self._tag_list.setFixedHeight(90)
        layout.addWidget(self._tag_list)

        outer.addWidget(container, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("保存设置")
        save_btn.setStyleSheet(self._primary_button_style())
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        outer.addLayout(btn_row)

    def _make_spinbox(self, min_v: int, max_v: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_v, max_v)
        spin.setStyleSheet(
            "QSpinBox { background-color: #3a3a3a; color: #ffffff; padding: 4px; border: 1px solid #555; border-radius: 5px; }"
        )
        return spin

    def _add_row(self, parent_layout: QVBoxLayout, label_text: str, widget) -> None:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setStyleSheet("color: #dddddd;")
        label.setFixedWidth(160)
        row.addWidget(label)
        row.addWidget(widget, 1)
        parent_layout.addLayout(row)

    def _button_style(self) -> str:
        return (
            "QPushButton { background-color: #3a3a3a; color: #ffffff; padding: 6px 16px;"
            " border: 1px solid #555; border-radius: 5px; }"
            " QPushButton:hover { background-color: #4a4a4a; }"
        )

    def _primary_button_style(self) -> str:
        return (
            "QPushButton { background-color: #e74c3c; color: #ffffff; padding: 8px 24px;"
            " border: none; border-radius: 5px; font-weight: bold; }"
            " QPushButton:hover { background-color: #c0392b; }"
        )

    def _load_values(self) -> None:
        s: AppSettings = self._settings_manager.get()
        self._work_spin.setValue(s.work_minutes)
        self._short_break_spin.setValue(s.short_break_minutes)
        self._long_break_spin.setValue(s.long_break_minutes)
        self._interval_spin.setValue(s.long_break_interval)
        self._strict_check.setChecked(s.strict_mode)
        self._auto_start_check.setChecked(s.auto_start)
        self._sound_check.setChecked(s.play_sound)
        self._notif_check.setChecked(s.show_notification)
        self._tag_list.clear()
        for tag in s.task_tags:
            item = QListWidgetItem(tag)
            self._tag_list.addItem(item)

    def _add_tag(self) -> None:
        tag = self._tag_input.text().strip()
        if not tag:
            return
        s = self._settings_manager.get()
        if tag in s.task_tags:
            return
        self._settings_manager.add_tag(tag)
        self._tag_input.clear()
        item = QListWidgetItem(tag)
        self._tag_list.addItem(item)
        self.settings_changed.emit()

    def _remove_selected_tag(self) -> None:
        current = self._tag_list.currentItem()
        if not current:
            return
        tag = current.text()
        self._settings_manager.remove_tag(tag)
        row = self._tag_list.row(current)
        self._tag_list.takeItem(row)
        self.settings_changed.emit()

    def _save(self) -> None:
        self._settings_manager.update(
            work_minutes=self._work_spin.value(),
            short_break_minutes=self._short_break_spin.value(),
            long_break_minutes=self._long_break_spin.value(),
            long_break_interval=self._interval_spin.value(),
            strict_mode=self._strict_check.isChecked(),
            auto_start=self._auto_start_check.isChecked(),
            play_sound=self._sound_check.isChecked(),
            show_notification=self._notif_check.isChecked(),
        )
        self.settings_changed.emit()
        QMessageBox.information(self, "已保存", "设置已保存。")
