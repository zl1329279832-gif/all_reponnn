from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QMenuBar,
    QFileDialog, QMessageBox, QStatusBar,
)
from database import Database
from ui.customer_list import CustomerListPanel
from ui.customer_detail import CustomerDetailPanel
from ui.timeline import TimelinePanel
from ui.dialogs import TodayFollowUpDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("小工作室客户跟进管理")
        self.resize(1280, 780)
        self.setMinimumSize(960, 600)

        self.db = Database()
        self._build_ui()
        self._build_menu()
        self._connect_signals()

        self.statusBar().showMessage("就绪")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(2)
        self.splitter.setStyleSheet("QSplitter::handle { background: #e0e0e0; }")

        self.list_panel = CustomerListPanel(self.db)
        self.list_panel.setMinimumWidth(280)

        self.detail_panel = CustomerDetailPanel(self.db)

        self.timeline_panel = TimelinePanel(self.db)
        self.timeline_panel.setMinimumWidth(300)

        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setHandleWidth(2)
        self.right_splitter.addWidget(self.detail_panel)
        self.right_splitter.addWidget(self.timeline_panel)
        self.right_splitter.setStretchFactor(0, 3)
        self.right_splitter.setStretchFactor(1, 2)

        self.splitter.addWidget(self.list_panel)
        self.splitter.addWidget(self.right_splitter)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 5)

        layout.addWidget(self.splitter)

        self.setStatusBar(QStatusBar())

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")

        import_action = QAction("导入 CSV…", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._on_import_csv)
        file_menu.addAction(import_action)

        export_action = QAction("导出 CSV…", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export_csv)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        today_action = QAction("今日待跟进", self)
        today_action.setShortcut("Ctrl+T")
        today_action.triggered.connect(self._show_today_dialog)
        file_menu.addAction(today_action)

        file_menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = menubar.addMenu("帮助(&H)")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _connect_signals(self):
        self.list_panel.customer_selected.connect(self._on_customer_selected)
        self.list_panel.customer_add_requested.connect(self._on_add_customer)
        self.detail_panel.customer_updated.connect(self._on_customer_changed)
        self.detail_panel.customer_deleted.connect(self._on_customer_changed)
        self.detail_panel.follow_up_added.connect(self._on_followup_added)

    def _on_customer_selected(self, customer_id: int):
        self.detail_panel.load_customer(customer_id)
        self.timeline_panel.load_customer(customer_id)

    def _on_add_customer(self):
        self.detail_panel.load_new_customer()
        self.timeline_panel.load_customer(None)

    def _on_customer_changed(self):
        self.list_panel.refresh()
        if self.detail_panel.current_customer and self.detail_panel.current_customer.id:
            self.timeline_panel.load_customer(self.detail_panel.current_customer.id)
        else:
            self.timeline_panel.load_customer(None)

    def _on_followup_added(self):
        self.list_panel.refresh()
        if self.detail_panel.current_customer and self.detail_panel.current_customer.id:
            self.timeline_panel.load_customer(self.detail_panel.current_customer.id)
            self.list_panel.select_customer(self.detail_panel.current_customer.id)

    def _on_import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入客户 CSV", "", "CSV 文件 (*.csv)"
        )
        if not path:
            return
        try:
            added, updated = self.db.import_csv(path)
            self.list_panel.refresh()
            QMessageBox.information(
                self, "导入成功",
                f"导入完成！\n新增: {added} 家\n更新: {updated} 家"
            )
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入出错: {str(e)}")

    def _on_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出客户 CSV", "customers.csv", "CSV 文件 (*.csv)"
        )
        if not path:
            return
        try:
            self.db.export_csv(path)
            QMessageBox.information(self, "导出成功", f"客户数据已导出到:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出出错: {str(e)}")

    def _show_today_dialog(self):
        items = self.db.get_today_follow_ups()
        if not items:
            QMessageBox.information(self, "今日待跟进", "太棒了！今日没有需要跟进的客户 🎉")
            return
        dlg = TodayFollowUpDialog(items, self)
        if dlg.exec():
            if dlg.selected_id:
                self.list_panel.select_customer(dlg.selected_id)

    def _show_about(self):
        QMessageBox.about(
            self, "关于",
            "<h3>小工作室客户跟进管理</h3>"
            "<p>本地桌面版客户关系管理工具</p>"
            "<p>数据存储: SQLite (本地)</p>"
            "<p>技术栈: Python + PyQt6</p>"
        )

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_first_show_done", False):
            self._first_show_done = True
            items = self.db.get_today_follow_ups()
            if items:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(200, self._show_today_dialog)

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)
