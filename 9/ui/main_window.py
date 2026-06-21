import sys
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QStackedWidget, QSystemTrayIcon, QMenu,
    QMessageBox,
)
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl

from core.timer import PomodoroTimer
from core.models import TimerState, SessionStatus, PRESETS, DEFAULT_PRESET
from core.database import PomodoroDB
from ui.ring_widget import RingWidget
from ui.stats_page import BarChartWidget
from ui.settings_page import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🍅 番茄专注")
        self.resize(420, 600)
        self.setMinimumSize(380, 520)

        self.timer_core = PomodoroTimer()
        self.db = PomodoroDB()
        self.session_started_at: str = ""
        self.session_duration: int = 0

        self._build_ui()
        self._build_tray()
        self._connect_signals()
        self._sync_ring_from_core()
        self._update_button_states()

        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(1000)
        self.tick_timer.timeout.connect(self._on_tick)

        self._notif_timer = QTimer(self)
        self._notif_timer.setSingleShot(True)
        self._notif_timer.setInterval(100)
        self._notif_timer.timeout.connect(self._show_complete_notification)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        nav = QHBoxLayout()
        self.btn_timer_page = QPushButton("计时器")
        self.btn_timer_page.setCheckable(True)
        self.btn_timer_page.setChecked(True)
        self.btn_timer_page.setStyleSheet(self._nav_style(True))
        self.btn_stats_page = QPushButton("统计")
        self.btn_stats_page.setCheckable(True)
        self.btn_stats_page.setStyleSheet(self._nav_style(False))
        self.btn_settings_page = QPushButton("设置")
        self.btn_settings_page.setCheckable(True)
        self.btn_settings_page.setStyleSheet(self._nav_style(False))
        nav.addWidget(self.btn_timer_page)
        nav.addWidget(self.btn_stats_page)
        nav.addWidget(self.btn_settings_page)
        layout.addLayout(nav)

        self.stack = QStackedWidget()

        timer_page = QWidget()
        tp_layout = QVBoxLayout(timer_page)
        tp_layout.setContentsMargins(0, 0, 0, 0)
        tp_layout.setSpacing(12)

        preset_row = QHBoxLayout()
        preset_label = QLabel("预设:")
        self.preset_combo = QComboBox()
        for name in PRESETS:
            self.preset_combo.addItem(name)
        self.preset_combo.setCurrentText(DEFAULT_PRESET)
        preset_row.addWidget(preset_label)
        preset_row.addWidget(self.preset_combo, 1)
        tp_layout.addLayout(preset_row)

        self.ring = RingWidget()
        tp_layout.addWidget(self.ring, 1)

        self.status_label = QLabel("准备开始专注")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        tp_layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.start_btn = QPushButton("开始专注")
        self.start_btn.setStyleSheet(self._action_style("#2d7ff9", "#1e6ee0"))

        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setStyleSheet(self._action_style("#f57c00", "#e65100"))
        self.pause_btn.setVisible(False)

        self.resume_btn = QPushButton("继续")
        self.resume_btn.setStyleSheet(self._action_style("#2e7d32", "#1b5e20"))
        self.resume_btn.setVisible(False)

        self.abandon_btn = QPushButton("放弃")
        self.abandon_btn.setStyleSheet(self._action_style("#d93025", "#b71c1c"))
        self.abandon_btn.setVisible(False)

        btn_row.addStretch(1)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.pause_btn)
        btn_row.addWidget(self.resume_btn)
        btn_row.addWidget(self.abandon_btn)
        btn_row.addStretch(1)
        tp_layout.addLayout(btn_row)

        self.stack.addWidget(timer_page)

        stats_page = QWidget()
        sp_layout = QVBoxLayout(stats_page)
        sp_layout.setContentsMargins(0, 0, 0, 0)
        sp_layout.setSpacing(8)
        stats_title = QLabel("近 7 天专注统计")
        stats_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        sp_layout.addWidget(stats_title)
        self.chart = BarChartWidget()
        sp_layout.addWidget(self.chart, 1)
        self.today_label = QLabel("")
        self.today_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.today_label.setStyleSheet("color: #666; font-size: 12px;")
        sp_layout.addWidget(self.today_label)
        self.refresh_btn = QPushButton("刷新统计")
        self.refresh_btn.setStyleSheet(self._action_style("#2d7ff9", "#1e6ee0"))
        self.refresh_btn.clicked.connect(self._refresh_stats)
        sp_layout.addWidget(self.refresh_btn)
        self.stack.addWidget(stats_page)

        self.settings_page = SettingsPage()
        self.stack.addWidget(self.settings_page)

        layout.addWidget(self.stack, 1)

    def _build_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("番茄专注")
        self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))

        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示主窗口")
        show_action.triggered.connect(self._show_window)
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self._quit_app)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _connect_signals(self):
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        self.start_btn.clicked.connect(self._on_start)
        self.pause_btn.clicked.connect(self._on_pause)
        self.resume_btn.clicked.connect(self._on_resume)
        self.abandon_btn.clicked.connect(self._on_abandon)

        self.btn_timer_page.clicked.connect(lambda: self._switch_page(0))
        self.btn_stats_page.clicked.connect(lambda: self._switch_page(1))
        self.btn_settings_page.clicked.connect(lambda: self._switch_page(2))

        self.settings_page.settings_changed.connect(self._on_settings_changed)

    def _nav_style(self, active: bool) -> str:
        if active:
            return """
                QPushButton { background: #2d7ff9; color: white; border: none;
                              padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            """
        return """
            QPushButton { background: #f0f0f0; color: #333; border: none;
                          padding: 8px 16px; border-radius: 4px; }
            QPushButton:hover { background: #e0e0e0; }
        """

    def _action_style(self, bg: str, hover: str) -> str:
        return f"""
            QPushButton {{ background: {bg}; color: white; padding: 10px 20px;
                          border: none; border-radius: 6px; font-weight: bold; font-size: 14px; }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:disabled {{ background: #ccc; color: #999; }}
        """

    def _switch_page(self, idx: int):
        self.stack.setCurrentIndex(idx)
        self.btn_timer_page.setChecked(idx == 0)
        self.btn_timer_page.setStyleSheet(self._nav_style(idx == 0))
        self.btn_stats_page.setChecked(idx == 1)
        self.btn_stats_page.setStyleSheet(self._nav_style(idx == 1))
        self.btn_settings_page.setChecked(idx == 2)
        self.btn_settings_page.setStyleSheet(self._nav_style(idx == 2))
        if idx == 1:
            self._refresh_stats()

    def _on_preset_changed(self, preset_name: str):
        if self.timer_core.state != TimerState.IDLE:
            return
        if preset_name in PRESETS:
            self.timer_core.set_preset(preset_name)
            self._sync_ring_from_core()

    def _sync_ring_from_core(self):
        self.ring.set_remaining(self.timer_core.format_remaining())
        self.ring.set_progress(self.timer_core.progress())
        state = self.timer_core.state
        if state == TimerState.IDLE:
            self.ring.set_state_text("准备专注")
            self.ring.set_ring_color(QColor("#2d7ff9"))
        elif state == TimerState.RUNNING:
            self.ring.set_state_text("专注中…")
            self.ring.set_ring_color(QColor("#2d7ff9"))
        elif state == TimerState.PAUSED:
            self.ring.set_state_text("已暂停")
            self.ring.set_ring_color(QColor("#f57c00"))

    def _update_button_states(self):
        state = self.timer_core.state
        self.start_btn.setVisible(state == TimerState.IDLE)
        self.pause_btn.setVisible(state == TimerState.RUNNING)
        self.resume_btn.setVisible(state == TimerState.PAUSED)
        self.abandon_btn.setVisible(state in (TimerState.RUNNING, TimerState.PAUSED))
        self.preset_combo.setEnabled(state == TimerState.IDLE)

    def _on_start(self):
        if self.timer_core.state != TimerState.IDLE:
            return

        current_preset = self.preset_combo.currentText()
        if current_preset in PRESETS and self.timer_core.current_preset != current_preset:
            self.timer_core.set_preset(current_preset)

        self.session_started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.session_duration = self.timer_core.total_seconds
        self.timer_core.start()
        self.tick_timer.start()
        self._sync_ring_from_core()
        self._update_button_states()
        self.status_label.setText(f"专注中 — {self.timer_core.current_preset or '自定义'}")

    def _on_pause(self):
        try:
            self.timer_core.pause()
            self.tick_timer.stop()
            self._sync_ring_from_core()
            self._update_button_states()
            self.status_label.setText("已暂停")
        except RuntimeError:
            pass

    def _on_resume(self):
        try:
            self.timer_core.resume()
            self.tick_timer.start()
            self._sync_ring_from_core()
            self._update_button_states()
            self.status_label.setText(f"专注中 — {self.timer_core.current_preset or '自定义'}")
        except RuntimeError:
            pass

    def _on_abandon(self):
        was_paused = self.timer_core.state == TimerState.PAUSED
        try:
            elapsed = self.timer_core.abandon()
            self.tick_timer.stop()
            actual_elapsed = abs(elapsed)
            status = SessionStatus.PAUSED_ABANDONED.value if was_paused else SessionStatus.ABANDONED.value
            self.db.record_session(
                started_at=self.session_started_at,
                duration_seconds=self.session_duration,
                completed_seconds=actual_elapsed,
                status=status,
                preset_name=self.timer_core.current_preset,
            )
            self._sync_ring_from_core()
            self._update_button_states()
            self.status_label.setText("已放弃")
            self.ring.set_state_text("已放弃")
        except RuntimeError:
            pass

    def _on_tick(self):
        finished = self.timer_core.tick()
        self._sync_ring_from_core()

        if finished:
            self.tick_timer.stop()
            elapsed = self.timer_core.complete()
            self.db.record_session(
                started_at=self.session_started_at,
                duration_seconds=self.session_duration,
                completed_seconds=elapsed,
                status=SessionStatus.COMPLETED.value,
                preset_name=self.timer_core.current_preset,
            )
            self._sync_ring_from_core()
            self._update_button_states()
            self.status_label.setText("🎉 专注完成！")
            self.ring.set_state_text("专注完成")
            self._notif_timer.start()

    def _show_complete_notification(self):
        self.tray_icon.showMessage(
            "🍅 番茄专注完成",
            f"恭喜！你完成了 {self.session_duration // 60} 分钟的专注！",
            QSystemTrayIcon.MessageIcon.Information,
            5000,
        )
        try:
            self._sound = QSoundEffect()
            self._sound.setSource(QUrl.fromLocalFile(""))
            self._sound.setVolume(0.8)
            try:
                import os, sys
                base = os.path.dirname(os.path.abspath(sys.argv[0]))
                for candidate in [
                    os.path.join(base, "complete.wav"),
                    os.path.join(base, "assets", "complete.wav"),
                ]:
                    if os.path.exists(candidate):
                        self._sound.setSource(QUrl.fromLocalFile(candidate))
                        break
                else:
                    self._sound.setSource(QUrl("qrc:/qt/sounds/default.wav"))
            except Exception:
                pass
            self._sound.play()
        except Exception:
            pass

    def _refresh_stats(self):
        stats = self.db.get_daily_stats(7)
        self.chart.set_stats(stats)
        today = self.db.get_today_summary()
        comp_m = today.completed_seconds // 60
        ab_m = today.abandoned_seconds // 60
        pa_m = today.paused_abandoned_seconds // 60
        self.today_label.setText(
            f"今日: 完成 {today.completed_count} 次 ({comp_m}min)  |  "
            f"放弃 {today.abandoned_count} 次 ({ab_m}min)  |  "
            f"暂停弃 {today.paused_abandoned_count} 次 ({pa_m}min)"
        )

    def _on_settings_changed(self):
        pass

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.activateWindow()

    def _quit_app(self):
        self.tray_icon.hide()
        self.db.close()
        QApplication.instance().quit()

    def closeEvent(self, event):
        if self.timer_core.state in (TimerState.RUNNING, TimerState.PAUSED):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "🍅 番茄专注",
                "计时器仍在运行，最小化到系统托盘。双击图标恢复窗口。",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
        else:
            self.db.close()
            event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_first_show_done", False):
            self._first_show_done = True
            self._refresh_stats()
