from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QStatusBar,
    QMessageBox,
)

from .save_list import SaveListPanel
from .preview_panel import PreviewPanel
from .action_panel import ActionPanel
from ..core import database as db
from ..core import scanner
from ..core.models import SaveSlot


class ScanWorker(QThread):
    progress = pyqtSignal(str, int, int)
    finished_ok = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

    def run(self) -> None:
        try:
            count = 0
            def cb(path: str, current: int, total: int) -> None:
                nonlocal count
                count = max(count, current)
                self.progress.emit(path, current, total)
            slots = scanner.scan_all_paths(cb)
            self.finished_ok.emit(len(slots))
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("单机游戏存档管理器")
        self.resize(1200, 720)
        self._build_ui()
        self._scan_worker: Optional[ScanWorker] = None

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.save_list = SaveListPanel()
        self.preview_panel = PreviewPanel()
        self.action_panel = ActionPanel()

        splitter.addWidget(self.save_list)
        splitter.addWidget(self.preview_panel)
        splitter.addWidget(self.action_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 3)
        splitter.setSizes([360, 480, 360])

        root_layout.addWidget(splitter)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")

        self.save_list.selection_model().currentChanged.connect(self._on_selection_changed)
        self.save_list.btn_rescan.clicked.connect(self._on_rescan)

    def _on_selection_changed(self, current, _previous) -> None:
        slot: Optional[SaveSlot] = current.data(Qt.ItemDataRole.UserRole) if current.isValid() else None
        self.preview_panel.set_slot(slot)
        self.action_panel.set_slot(slot)

    def _on_rescan(self) -> None:
        paths = db.list_scan_paths()
        if not paths:
            QMessageBox.information(
                self, "提示",
                "尚未添加任何扫描路径。\n请先点击左下角「添加扫描路径」选择存档所在的文件夹。",
            )
            return
        if self._scan_worker is not None and self._scan_worker.isRunning():
            QMessageBox.information(self, "提示", "正在扫描中，请稍候…")
            return

        self._scan_worker = ScanWorker()
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished_ok.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self.save_list.btn_rescan.setEnabled(False)
        self.statusBar.showMessage("开始扫描…")
        self._scan_worker.start()

    def _on_scan_progress(self, path: str, current: int, total: int) -> None:
        if total > 0:
            self.statusBar.showMessage(f"扫描中: {path} ({current}/{total})")
        else:
            self.statusBar.showMessage(f"扫描中: {path}")

    def _on_scan_finished(self, count: int) -> None:
        self.save_list.btn_rescan.setEnabled(True)
        self.statusBar.showMessage(f"扫描完成，共发现 {count} 个存档")
        self.save_list.reload()

    def _on_scan_error(self, msg: str) -> None:
        self.save_list.btn_rescan.setEnabled(True)
        self.statusBar.showMessage("扫描出错")
        QMessageBox.critical(self, "扫描失败", f"扫描过程中发生错误:\n{msg}")

    def on_slot_updated(self) -> None:
        self.save_list.reload()
        slot = self.save_list.current_slot()
        self.preview_panel.set_slot(slot)
        self.action_panel.set_slot(slot)
