from typing import List, Optional

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QComboBox, QListView, QLabel, QFileDialog, QMessageBox, QStyledItemDelegate,
    QStyleOptionViewItem, QStyle, QApplication,
)

from ..core import database as db
from ..core.models import SaveSlot


class SaveSlotModel(QAbstractListModel):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._slots: List[SaveSlot] = []

    def load(self, keyword: str = "", sort_by: str = "modified_desc") -> None:
        self.beginResetModel()
        self._slots = db.list_save_slots(keyword=keyword, sort_by=sort_by)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._slots)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or index.row() >= len(self._slots):
            return None
        slot = self._slots[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return slot
        if role == Qt.ItemDataRole.DisplayRole:
            return slot
        return None

    def get_slot(self, index: QModelIndex) -> Optional[SaveSlot]:
        if not index.isValid() or index.row() >= len(self._slots):
            return None
        return self._slots[index.row()]


class SaveSlotDelegate(QStyledItemDelegate):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(0, 68)

    def paint(self, painter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        slot: Optional[SaveSlot] = index.data(Qt.ItemDataRole.UserRole)
        if slot is None:
            painter.restore()
            return

        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        if selected:
            painter.fillRect(option.rect, option.palette.highlight())
            text_color = option.palette.highlightedText().color()
        elif hovered:
            base = option.palette.base().color()
            hover = base.lighter(108)
            painter.fillRect(option.rect, hover)
            text_color = option.palette.text().color()
        else:
            painter.fillRect(option.rect, option.palette.base())
            text_color = option.palette.text().color()

        rect = option.rect.adjusted(12, 8, -12, -8)

        title_font = QFont(option.font)
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 1)
        painter.setFont(title_font)
        painter.setPen(text_color)

        title = slot.game_name or "未知游戏"
        if slot.note:
            title = f"{title}  [{slot.note}]"
        painter.drawText(rect.left(), rect.top() + 18, title)

        small_font = QFont(option.font)
        small_font.setPointSize(small_font.pointSize() - 1)
        painter.setFont(small_font)
        info_color = QColor(text_color)
        info_color.setAlpha(180)
        painter.setPen(info_color)

        info_line = f"{slot.last_modified_str}    {slot.file_size_str}"
        painter.drawText(rect.left(), rect.top() + 40, info_line)

        path_font = QFont(option.font)
        path_font.setPointSize(path_font.pointSize() - 1)
        path_font.setItalic(True)
        painter.setFont(path_font)
        path_color = QColor(text_color)
        path_color.setAlpha(140)
        painter.setPen(path_color)
        fm = painter.fontMetrics()
        elided_path = fm.elidedText(slot.path, Qt.TextElideMode.ElideMiddle, rect.width())
        painter.drawText(rect.left(), rect.top() + 58, elided_path)

        painter.restore()


class SaveListPanel(QWidget):
    compare_requested = pyqtSignal(list)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索游戏名/路径/备注…")
        self.search_edit.setClearButtonEnabled(True)
        top_bar.addWidget(self.search_edit, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "最近修改", "最早修改", "名称升序", "名称降序", "大小降序"
        ])
        top_bar.addWidget(self.sort_combo)
        layout.addLayout(top_bar)

        self.list_view = QListView()
        self.list_view.setUniformItemSizes(True)
        self.list_view.setBatchSize(50)
        self.list_view.setLayoutMode(QListView.LayoutMode.Batched)
        self._model = SaveSlotModel(self)
        self._delegate = SaveSlotDelegate(self)
        self.list_view.setModel(self._model)
        self.list_view.setItemDelegate(self._delegate)
        self.list_view.setSelectionMode(QListView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.list_view, 1)

        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(6)
        self.btn_add_path = QPushButton("添加扫描路径")
        self.btn_rescan = QPushButton("重新扫描")
        self.btn_compare = QPushButton("对比选中 (2)")
        self.btn_compare.setToolTip("按住 Ctrl 选中两个存档后点击此按钮")
        self.btn_compare.clicked.connect(self._on_compare_clicked)
        btn_bar.addWidget(self.btn_add_path)
        btn_bar.addWidget(self.btn_rescan)
        btn_bar.addWidget(self.btn_compare)
        btn_bar.addStretch(1)
        self.status_label = QLabel("")
        btn_bar.addWidget(self.status_label)
        layout.addLayout(btn_bar)

        self.search_edit.textChanged.connect(self._on_filter_changed)
        self.sort_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.btn_add_path.clicked.connect(self._on_add_path)

        self.list_view.selectionModel().selectionChanged.connect(self._on_selection_changed_internally)
        self.reload()

    def _on_selection_changed_internally(self, *_args) -> None:
        count = len(self.selected_slots())
        self.btn_compare.setText(f"对比选中 ({count})")

    def _sort_key(self) -> str:
        keys = ["modified_desc", "modified_asc", "name_asc", "name_desc", "size_desc"]
        idx = self.sort_combo.currentIndex()
        return keys[idx] if 0 <= idx < len(keys) else "modified_desc"

    def _on_filter_changed(self, *_args) -> None:
        self.reload()

    def reload(self) -> None:
        keyword = self.search_edit.text().strip()
        self._model.load(keyword=keyword, sort_by=self._sort_key())
        count = self._model.rowCount()
        self.status_label.setText(f"共 {count} 条存档（Ctrl 多选两个可对比）")

    def current_slot(self) -> Optional[SaveSlot]:
        idx = self.list_view.currentIndex()
        return self._model.get_slot(idx)

    def selected_slots(self) -> List[SaveSlot]:
        result: List[SaveSlot] = []
        for idx in self.list_view.selectedIndexes():
            slot = self._model.get_slot(idx)
            if slot is not None:
                result.append(slot)
        return result

    def _on_add_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择要扫描的存档目录")
        if not path:
            return
        db.add_scan_path(path)
        QMessageBox.information(self, "提示", f"已添加扫描路径: {path}\n点击「重新扫描」开始扫描。")

    def _on_compare_clicked(self) -> None:
        slots = self.selected_slots()
        if len(slots) < 2:
            QMessageBox.information(
                self, "提示",
                "请选中两个存档进行对比：\n\n"
                "1. 先点击第一个存档\n"
                "2. 按住 Ctrl 键点击第二个存档\n"
                "3. 再点击「对比选中」按钮\n\n"
                "也可以在右侧备份列表点选一个备份，点击「与当前对比」。",
            )
            return
        if len(slots) > 2:
            QMessageBox.information(self, "提示", "一次最多对比两个存档。请只选中两个。")
            return
        self.compare_requested.emit(slots)

    def selection_model(self):
        return self.list_view.selectionModel()

    def clear_selection(self) -> None:
        self.list_view.clearSelection()
