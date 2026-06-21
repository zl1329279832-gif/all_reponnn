from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QComboBox,
    QLabel,
    QTabWidget,
    QFrame,
    QMessageBox,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QIcon, QPainter, QColor, QBrush, QPen, QPixmap, QCloseEvent
from PySide6.QtWidgets import QSystemTrayIcon

from core.timer import PomodoroTimer, TimerState, TimerEndReason, TimerSnapshot
from core.storage import Storage, SessionStatus, SessionType
from config.settings import SettingsManager, AppSettings
from ui.circle_timer import CircleTimer
from ui.system_tray import SystemTray
from ui.history_page import HistoryPage
from ui.settings_page import SettingsPage


def _window_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setBrush(QBrush(QColor("#e74c3c")))
    painter.setPen(QPen(QColor("#ffffff"), 3))
    painter.drawEllipse(6, 6, 52, 52)
    painter.setPen(QPen(QColor("#ffffff"), 4))
    painter.drawLine(32, 16, 32, 34)
    painter.drawLine(32, 34, 44, 34)
    painter.end()
    return QIcon(pixmap)


def format_seconds(seconds: int) -> str:
    m, s = divmod(max(0, seconds), 60)
    return f"{m:02d}:{s:02d}"


class FocusPage(QWidget):
    def __init__(self, settings_manager: SettingsManager, storage: Storage, parent=None):
        super().__init__(parent)
        self._settings_manager = settings_manager
        self._storage = storage
        self._session_id: int | None = None
        self._session_type: SessionType = SessionType.WORK
        self._completed_work_count: int = 0

        self._timer = PomodoroTimer(
            self._settings_manager.get().work_minutes * 60
        )
        self._timer.on_tick(self._on_tick)
        self._timer.on_completed(self._on_timer_completed)
        self._timer.on_state_changed(self._on_state_changed)

        self._qt_timer = QTimer(self)
        self._qt_timer.setInterval(200)
        self._qt_timer.timeout.connect(self._timer.tick)

        self._build_ui()
        self._sync_labels()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        self._circle = CircleTimer()
        self._circle.clicked.connect(self._on_circle_clicked)
        layout.addWidget(self._circle, 1, Qt.AlignCenter)

        selector_frame = QFrame()
        selector_frame.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border-radius: 10px; }"
        )
        sel_layout = QVBoxLayout(selector_frame)
        sel_layout.setContentsMargins(18, 16, 18, 16)
        sel_layout.setSpacing(12)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("任务标签:").__class__())
        tag_label = QLabel("任务标签:")
        tag_label.setStyleSheet("color: #dddddd;")
        tag_label.setFixedWidth(70)
        row1.addWidget(tag_label)
        self._tag_combo = QComboBox()
        self._tag_combo.setEditable(True)
        self._tag_combo.setStyleSheet(
            "QComboBox { background-color: #3a3a3a; color: #ffffff; padding: 6px; border: 1px solid #555; border-radius: 5px; }"
            " QComboBox QAbstractItemView { background-color: #3a3a3a; color: #ffffff; selection-background-color: #555; }"
        )
        self._refresh_tag_combo()
        row1.addWidget(self._tag_combo, 1)
        sel_layout.addLayout(row1)

        row2 = QHBoxLayout()
        preset_label = QLabel("时长预设:")
        preset_label.setStyleSheet("color: #dddddd;")
        preset_label.setFixedWidth(70)
        row2.addWidget(preset_label)
        self._preset_combo = QComboBox()
        self._preset_combo.setStyleSheet(
            "QComboBox { background-color: #3a3a3a; color: #ffffff; padding: 6px; border: 1px solid #555; border-radius: 5px; }"
            " QComboBox QAbstractItemView { background-color: #3a3a3a; color: #ffffff; selection-background-color: #555; }"
        )
        self._refresh_preset_combo()
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        row2.addWidget(self._preset_combo, 1)
        sel_layout.addLayout(row2)

        layout.addWidget(selector_frame)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._start_btn = QPushButton("开始专注")
        self._start_btn.setStyleSheet(self._primary_btn_style())
        self._start_btn.clicked.connect(self._on_start_clicked)
        btn_row.addWidget(self._start_btn)

        self._pause_btn = QPushButton("暂停")
        self._pause_btn.setStyleSheet(self._secondary_btn_style())
        self._pause_btn.clicked.connect(self._on_pause_clicked)
        self._pause_btn.setVisible(False)
        btn_row.addWidget(self._pause_btn)

        self._resume_btn = QPushButton("继续")
        self._resume_btn.setStyleSheet(self._primary_btn_style())
        self._resume_btn.clicked.connect(self._on_resume_clicked)
        self._resume_btn.setVisible(False)
        btn_row.addWidget(self._resume_btn)

        self._abandon_btn = QPushButton("放弃")
        self._abandon_btn.setStyleSheet(self._danger_btn_style())
        self._abandon_btn.clicked.connect(self._on_abandon_clicked)
        self._abandon_btn.setVisible(False)
        btn_row.addWidget(self._abandon_btn)

        self._skip_btn = QPushButton("跳过休息")
        self._skip_btn.setStyleSheet(self._secondary_btn_style())
        self._skip_btn.clicked.connect(self._on_skip_break_clicked)
        self._skip_btn.setVisible(False)
        btn_row.addWidget(self._skip_btn)

        layout.addLayout(btn_row)

        self._today_label = QLabel()
        self._today_label.setAlignment(Qt.AlignCenter)
        self._today_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        layout.addWidget(self._today_label)
        self._update_today_label()

    def _primary_btn_style(self) -> str:
        return (
            "QPushButton { background-color: #e74c3c; color: #ffffff; padding: 10px 22px;"
            " border: none; border-radius: 6px; font-weight: bold; font-size: 14px; }"
            " QPushButton:hover { background-color: #c0392b; }"
            " QPushButton:disabled { background-color: #666; }"
        )

    def _secondary_btn_style(self) -> str:
        return (
            "QPushButton { background-color: #3a3a3a; color: #ffffff; padding: 10px 22px;"
            " border: 1px solid #555; border-radius: 6px; font-size: 14px; }"
            " QPushButton:hover { background-color: #4a4a4a; }"
            " QPushButton:disabled { color: #888; }"
        )

    def _danger_btn_style(self) -> str:
        return (
            "QPushButton { background-color: transparent; color: #e74c3c; padding: 10px 22px;"
            " border: 1px solid #e74c3c; border-radius: 6px; font-size: 14px; }"
            " QPushButton:hover { background-color: rgba(231, 76, 60, 0.1); }"
        )

    def _refresh_tag_combo(self) -> None:
        current = self._tag_combo.currentText()
        self._tag_combo.blockSignals(True)
        self._tag_combo.clear()
        for t in self._settings_manager.get().task_tags:
            self._tag_combo.addItem(t)
        if current:
            idx = self._tag_combo.findText(current)
            if idx >= 0:
                self._tag_combo.setCurrentIndex(idx)
            else:
                self._tag_combo.setEditText(current)
        self._tag_combo.blockSignals(False)

    def _refresh_preset_combo(self) -> None:
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        for minutes in self._settings_manager.get().duration_presets:
            self._preset_combo.addItem(f"{minutes} 分钟", minutes * 60)
        s = self._settings_manager.get()
        default_idx = self._preset_combo.findData(s.work_minutes * 60)
        if default_idx >= 0:
            self._preset_combo.setCurrentIndex(default_idx)
        self._preset_combo.blockSignals(False)

    def _on_preset_changed(self, index: int) -> None:
        if self._timer.state == TimerState.RUNNING:
            return
        data = self._preset_combo.itemData(index)
        if data is not None:
            self._timer.set_total_seconds(int(data))
            self._sync_labels()

    def _on_circle_clicked(self) -> None:
        state = self._timer.state
        if state == TimerState.IDLE:
            self._on_start_clicked()
        elif state == TimerState.RUNNING:
            self._on_pause_clicked()
        elif state == TimerState.PAUSED:
            self._on_resume_clicked()

    def _current_task_tag(self) -> str:
        text = self._tag_combo.currentText().strip()
        if text and text not in self._settings_manager.get().task_tags:
            self._settings_manager.add_tag(text)
            self._refresh_tag_combo()
        return text or "未分类"

    def _on_start_clicked(self) -> None:
        s: AppSettings = self._settings_manager.get()
        if self._timer.state == TimerState.IDLE:
            self._session_type = SessionType.WORK
            self._timer.set_total_seconds(s.work_minutes * 60)
        self._session_id = self._storage.create_session(
            task_tag=self._current_task_tag(),
            session_type=self._session_type,
            duration_seconds=self._timer.total_seconds,
            started_at=datetime.now(),
        )
        self._timer.start()
        self._qt_timer.start()

    def _on_pause_clicked(self) -> None:
        if self._timer.state != TimerState.RUNNING:
            return
        self._timer.pause()
        self._qt_timer.stop()
        self._persist_current_status(SessionStatus.PAUSED)

    def _on_resume_clicked(self) -> None:
        if self._timer.state != TimerState.PAUSED:
            return
        self._timer.resume()
        self._qt_timer.start()

    def _on_abandon_clicked(self) -> None:
        if self._timer.state in (TimerState.IDLE, TimerState.COMPLETED):
            return
        reply = QMessageBox.question(
            self,
            "确认放弃",
            "确定要放弃本次计时吗？放弃将不计入完成数。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._timer.abandon()
        self._qt_timer.stop()
        self._persist_current_status(SessionStatus.ABANDONED)
        self._reset_to_idle()

    def _on_skip_break_clicked(self) -> None:
        s = self._settings_manager.get()
        if s.strict_mode and self._session_type in (SessionType.SHORT_BREAK, SessionType.LONG_BREAK):
            QMessageBox.information(self, "严格模式", "严格模式下无法跳过休息。")
            return
        self._persist_current_status(SessionStatus.ABANDONED)
        self._timer.reset()
        self._qt_timer.stop()
        self._start_work_session()

    def _persist_current_status(self, status: SessionStatus) -> None:
        if self._session_id is None:
            return
        self._storage.update_session_status(
            session_id=self._session_id,
            status=status,
            actual_duration_seconds=self._timer.get_elapsed_seconds(),
            ended_at=datetime.now(),
        )
        self._update_today_label()

    def _on_tick(self, snapshot: TimerSnapshot) -> None:
        self._circle.set_progress(snapshot.progress)
        self._circle.set_time_text(format_seconds(snapshot.remaining_seconds))

    def _on_state_changed(self, old: TimerState, new: TimerState) -> None:
        self._update_button_visibility()
        self._sync_labels()

    def _sync_labels(self) -> None:
        snap = self._timer.snapshot()
        self._circle.set_progress(snap.progress)
        self._circle.set_time_text(format_seconds(snap.remaining_seconds))
        if self._session_type == SessionType.WORK:
            if snap.state == TimerState.RUNNING:
                label = "专注中"
                color = QColor("#e74c3c")
            elif snap.state == TimerState.PAUSED:
                label = "已暂停"
                color = QColor("#f39c12")
            elif snap.state == TimerState.COMPLETED:
                label = "专注完成"
                color = QColor("#27ae60")
            else:
                label = "准备开始"
                color = QColor("#e74c3c")
        else:
            if snap.state == TimerState.RUNNING:
                label = "休息中"
                color = QColor("#3498db")
            elif snap.state == TimerState.PAUSED:
                label = "休息已暂停"
                color = QColor("#f39c12")
            elif snap.state == TimerState.COMPLETED:
                label = "休息结束"
                color = QColor("#27ae60")
            else:
                label = "准备休息"
                color = QColor("#3498db")
        self._circle.set_label_text(label)
        self._circle.set_progress_color(color)
        self._update_today_label()

    def _update_button_visibility(self) -> None:
        state = self._timer.state
        is_break = self._session_type in (SessionType.SHORT_BREAK, SessionType.LONG_BREAK)
        self._start_btn.setVisible(state in (TimerState.IDLE, TimerState.COMPLETED) and not is_break)
        self._pause_btn.setVisible(state == TimerState.RUNNING)
        self._resume_btn.setVisible(state == TimerState.PAUSED)
        self._abandon_btn.setVisible(state in (TimerState.RUNNING, TimerState.PAUSED))
        s = self._settings_manager.get()
        skip_visible = (state in (TimerState.RUNNING, TimerState.PAUSED)) and is_break
        self._skip_btn.setVisible(skip_visible)
        if skip_visible:
            self._skip_btn.setEnabled(not s.strict_mode)

    def _update_today_label(self) -> None:
        n = self._storage.get_today_completed_count()
        self._today_label.setText(f"今日已完成 {n} 个番茄")

    def _on_timer_completed(self) -> None:
        self._qt_timer.stop()
        if self._timer.end_reason == TimerEndReason.COMPLETED:
            status = SessionStatus.COMPLETED
        else:
            status = SessionStatus.PAUSED
        self._persist_current_status(status)

        self._sync_labels()
        self._update_button_visibility()

        if self._session_type == SessionType.WORK:
            self._completed_work_count += 1
            self._notify("专注完成", "好样的！休息一下吧。")
            self._schedule_break()
        else:
            self._notify("休息结束", "继续加油，开始下一个番茄！")
            self._start_work_session()

    def _schedule_break(self) -> None:
        s: AppSettings = self._settings_manager.get()
        if self._completed_work_count % s.long_break_interval == 0:
            self._session_type = SessionType.LONG_BREAK
            duration = s.long_break_minutes * 60
        else:
            self._session_type = SessionType.SHORT_BREAK
            duration = s.short_break_minutes * 60
        self._timer.set_total_seconds(duration)
        self._session_id = self._storage.create_session(
            task_tag="休息",
            session_type=self._session_type,
            duration_seconds=duration,
            started_at=datetime.now(),
        )
        self._timer.start()
        self._qt_timer.start()
        self._update_button_visibility()
        self._sync_labels()

    def _start_work_session(self) -> None:
        s: AppSettings = self._settings_manager.get()
        self._session_type = SessionType.WORK
        self._timer.set_total_seconds(s.work_minutes * 60)
        self._timer.reset()
        self._update_button_visibility()
        self._sync_labels()
        self._start_btn.setVisible(True)

    def _reset_to_idle(self) -> None:
        self._session_type = SessionType.WORK
        self._timer.reset()
        self._update_button_visibility()
        self._sync_labels()

    def _notify(self, title: str, body: str) -> None:
        s = self._settings_manager.get()
        parent = self.window()
        if s.show_notification and isinstance(parent, MainWindow):
            parent.show_tray_message(title, body)
        if s.play_sound and isinstance(parent, MainWindow):
            parent.play_notification_sound()

    def tray_toggle_pause_resume(self) -> None:
        state = self._timer.state
        if state == TimerState.RUNNING:
            self._on_pause_clicked()
        elif state == TimerState.PAUSED:
            self._on_resume_clicked()

    def tray_abandon(self) -> None:
        self._on_abandon_clicked()

    def refresh_from_settings(self) -> None:
        self._refresh_tag_combo()
        self._refresh_preset_combo()
        self._update_button_visibility()

    def get_status_text(self) -> str:
        snap = self._timer.snapshot()
        time_str = format_seconds(snap.remaining_seconds)
        if self._session_type == SessionType.WORK:
            prefix = "专注"
        else:
            prefix = "休息"
        if snap.state == TimerState.RUNNING:
            return f"{prefix}中 {time_str}"
        if snap.state == TimerState.PAUSED:
            return f"已暂停 {time_str}"
        if snap.state == TimerState.COMPLETED:
            return f"{prefix}已完成"
        return "准备开始"


class MainWindow(QMainWindow):
    def __init__(self, settings_manager: SettingsManager, storage: Storage):
        super().__init__()
        self._settings_manager = settings_manager
        self._storage = storage
        self._close_to_tray = True

        self.setWindowTitle("番茄钟")
        self.setWindowIcon(_window_icon())
        self.setMinimumSize(520, 720)
        self.resize(520, 780)
        self.setStyleSheet(
            "QMainWindow, QWidget { background-color: #1e1e1e; color: #ffffff; }"
            " QTabWidget::pane { border: none; background: #1e1e1e; }"
            " QTabBar::tab { background-color: #2a2a2a; color: #cccccc; padding: 10px 22px;"
            " margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; }"
            " QTabBar::tab:selected { background-color: #1e1e1e; color: #ffffff; font-weight: bold; }"
            " QLabel { color: #dddddd; }"
        )

        self._build_ui()
        self._tray = SystemTray(self)
        self._tray.show_main_requested.connect(self._toggle_window)
        self._tray.quit_requested.connect(self._quit_app)
        self._tray.pause_resume_requested.connect(self._focus_page.tray_toggle_pause_resume)
        self._tray.abandon_requested.connect(self._focus_page.tray_abandon)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray.show()

        self._tray_status_timer = QTimer(self)
        self._tray_status_timer.setInterval(1000)
        self._tray_status_timer.timeout.connect(self._update_tray_status)
        self._tray_status_timer.start()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._focus_page = FocusPage(self._settings_manager, self._storage)
        self._history_page = HistoryPage(self._storage)
        self._settings_page = SettingsPage(self._settings_manager)
        self._settings_page.settings_changed.connect(self._on_settings_changed)

        self._tabs.addTab(self._focus_page, "专注")
        self._tabs.addTab(self._history_page, "统计")
        self._tabs.addTab(self._settings_page, "设置")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self._tabs)

    def _on_tab_changed(self, index: int) -> None:
        if index == 1:
            self._history_page.refresh()

    def _on_settings_changed(self) -> None:
        self._focus_page.refresh_from_settings()

    def _toggle_window(self) -> None:
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()
            self.raise_()

    def _quit_app(self) -> None:
        self._close_to_tray = False
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._close_to_tray and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            if self._settings_manager.get().show_notification:
                self._tray.showMessage(
                    "番茄钟",
                    "已最小化到系统托盘，计时继续进行。",
                    QSystemTrayIcon.Information,
                    2000,
                )
        else:
            event.accept()
            QApplication.instance().quit()

    def show_tray_message(self, title: str, body: str) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray.showMessage(title, body, QSystemTrayIcon.Information, 4000)

    def play_notification_sound(self) -> None:
        try:
            from PySide6.QtMultimedia import QSoundEffect
            from PySide6.QtCore import QUrl
            if not hasattr(self, "_sound"):
                self._sound = QSoundEffect(self)
                self._sound.setVolume(0.8)
                beep = QUrl.fromLocalFile("")
                self._sound.setSource(beep)
            QApplication.beep()
        except Exception:
            try:
                QApplication.beep()
            except Exception:
                pass

    def _update_tray_status(self) -> None:
        text = self._focus_page.get_status_text()
        self._tray.update_status(text)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            if QSystemTrayIcon.isSystemTrayAvailable():
                pass
        super().changeEvent(event)
