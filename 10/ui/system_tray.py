from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon, QPainter, QColor, QBrush, QPen, QPixmap


def _create_tray_icon() -> QIcon:
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


class SystemTray(QSystemTrayIcon):
    show_main_requested = Signal()
    quit_requested = Signal()
    pause_resume_requested = Signal()
    abandon_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(_create_tray_icon())
        self.setToolTip("番茄钟")
        self._menu = QMenu()
        self._toggle_action = self._menu.addAction("显示/隐藏主窗口")
        self._toggle_action.triggered.connect(self.show_main_requested.emit)
        self._menu.addSeparator()
        self._pause_action = self._menu.addAction("暂停/继续")
        self._pause_action.triggered.connect(self.pause_resume_requested.emit)
        self._abandon_action = self._menu.addAction("放弃当前")
        self._abandon_action.triggered.connect(self.abandon_requested.emit)
        self._menu.addSeparator()
        self._quit_action = self._menu.addAction("退出")
        self._quit_action.triggered.connect(self.quit_requested.emit)
        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.show_main_requested.emit()

    def update_status(self, text: str) -> None:
        self.setToolTip(f"番茄钟 - {text}")
