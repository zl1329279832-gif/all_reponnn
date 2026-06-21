from typing import Optional, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QInputDialog, QGroupBox, QFrame,
)

from ..core import database as db
from ..core import backup_manager as bm
from ..core.models import SaveSlot, Backup


class ActionPanel(QWidget):
    backup_compare_requested = pyqtSignal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_slot: Optional[SaveSlot] = None
        self._build_ui()
        self.set_slot(None)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_label = QLabel("操作")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        action_group = QGroupBox("快捷操作")
        action_layout = QVBoxLayout(action_group)
        action_layout.setSpacing(8)

        self.btn_backup = QPushButton("📦  创建备份")
        self.btn_backup.setMinimumHeight(38)
        self.btn_restore = QPushButton("↩️  还原选中备份")
        self.btn_restore.setMinimumHeight(38)
        self.btn_rename = QPushButton("✏️  修改备注")
        self.btn_rename.setMinimumHeight(38)

        action_layout.addWidget(self.btn_backup)
        action_layout.addWidget(self.btn_restore)
        action_layout.addWidget(self.btn_rename)
        layout.addWidget(action_group)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        history_title = QLabel("备份历史")
        history_font = QFont()
        history_font.setBold(True)
        history_title.setFont(history_font)
        layout.addWidget(history_title)

        self.backup_list = QListWidget()
        self.backup_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.backup_list, 1)

        compare_bar = QHBoxLayout()
        compare_bar.setSpacing(6)
        self.btn_compare_backup = QPushButton("🔍  与当前对比")
        self.btn_compare_backup.setToolTip("将选中的备份与左侧选中的当前存档对比")
        self.btn_compare_backup.clicked.connect(self._on_compare_backup)
        compare_bar.addWidget(self.btn_compare_backup, 1)
        layout.addLayout(compare_bar)

        del_bar = QHBoxLayout()
        del_bar.setSpacing(6)
        self.btn_delete_backup = QPushButton("删除备份")
        self.btn_open_folder = QPushButton("打开备份目录")
        del_bar.addWidget(self.btn_delete_backup)
        del_bar.addWidget(self.btn_open_folder)
        layout.addLayout(del_bar)

        self.btn_backup.clicked.connect(self._on_backup)
        self.btn_restore.clicked.connect(self._on_restore)
        self.btn_rename.clicked.connect(self._on_rename)
        self.btn_delete_backup.clicked.connect(self._on_delete_backup)
        self.btn_open_folder.clicked.connect(self._on_open_folder)

    def set_slot(self, slot: Optional[SaveSlot]) -> None:
        self._current_slot = slot
        enabled = slot is not None
        self.btn_backup.setEnabled(enabled)
        self.btn_restore.setEnabled(False)
        self.btn_rename.setEnabled(enabled)
        self.btn_delete_backup.setEnabled(False)
        self.btn_compare_backup.setEnabled(False)
        self.backup_list.clear()
        if slot is not None:
            self._reload_backups()

    def _reload_backups(self) -> None:
        self.backup_list.clear()
        if self._current_slot is None:
            return
        backups: List[Backup] = bm.list_slot_backups(self._current_slot)
        for b in backups:
            label = f"{b.timestamp_str}"
            if b.note:
                label = f"{label}  -  {b.note}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, b)
            self.backup_list.addItem(item)
        if self.backup_list.count() == 0:
            placeholder = QListWidgetItem("（暂无备份）")
            placeholder.setFlags(placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.backup_list.addItem(placeholder)

        self.backup_list.itemSelectionChanged.connect(self._on_backup_selected)
        self._on_backup_selected()

    def _on_backup_selected(self) -> None:
        has = self.backup_list.currentItem() is not None and self.backup_list.currentItem().data(Qt.ItemDataRole.UserRole) is not None
        has_slot = self._current_slot is not None
        self.btn_restore.setEnabled(has and has_slot)
        self.btn_delete_backup.setEnabled(has)
        self.btn_compare_backup.setEnabled(has and has_slot)

    def _on_backup(self) -> None:
        if self._current_slot is None:
            return
        note, ok = QInputDialog.getText(self, "创建备份", "备份备注（可选）:")
        if not ok:
            return
        try:
            backup = bm.create_backup(self._current_slot, note.strip())
            self._reload_backups()
            QMessageBox.information(self, "备份完成", f"已创建备份:\n{backup.timestamp_str}\n\n备份路径:\n{backup.path}")
        except Exception as e:
            QMessageBox.critical(self, "备份失败", f"创建备份时出错:\n{e}")

    def _selected_backup(self) -> Optional[Backup]:
        item = self.backup_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_restore(self) -> None:
        backup = self._selected_backup()
        if backup is None or self._current_slot is None:
            return
        reply = QMessageBox.question(
            self, "确认还原",
            f"确定要将存档恢复到备份状态吗？\n\n"
            f"存档路径: {self._current_slot.path}\n"
            f"备份时间: {backup.timestamp_str}\n\n"
            "⚠️  当前存档将被覆盖，此操作无法撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            bm.restore_backup(self._current_slot, backup)
            db.upsert_save_slot(self._current_slot)
            QMessageBox.information(self, "还原完成", "存档已成功还原。")
            self.parent_widget_slot_reloaded()
        except Exception as e:
            QMessageBox.critical(self, "还原失败", f"还原存档时出错:\n{e}")

    def _on_compare_backup(self) -> None:
        backup = self._selected_backup()
        if backup is None or self._current_slot is None:
            return
        self.backup_compare_requested.emit((self._current_slot, backup))

    def _on_rename(self) -> None:
        if self._current_slot is None:
            return
        current = self._current_slot.note or ""
        note, ok = QInputDialog.getText(self, "修改备注", "备注:", text=current)
        if not ok:
            return
        note = note.strip()
        if self._current_slot.id is not None:
            db.update_save_slot_note(self._current_slot.id, note)
            self._current_slot.note = note
            self.parent_widget_slot_reloaded()

    def _on_delete_backup(self) -> None:
        backup = self._selected_backup()
        if backup is None:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除此备份吗？\n\n备份时间: {backup.timestamp_str}\n此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            bm.delete_backup_file(backup)
            self._reload_backups()
        except Exception as e:
            QMessageBox.critical(self, "删除失败", f"删除备份时出错:\n{e}")

    def _on_open_folder(self) -> None:
        import os
        import subprocess
        from ..core.database import get_backups_dir
        backups_dir = get_backups_dir()
        try:
            if os.name == "nt":
                os.startfile(backups_dir)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", backups_dir])
        except Exception as e:
            QMessageBox.critical(self, "打开失败", f"打开备份目录时出错:\n{e}")

    def parent_widget_slot_reloaded(self) -> None:
        mw = self.window()
        if hasattr(mw, "on_slot_updated"):
            mw.on_slot_updated()  # type: ignore[attr-defined]
