from datetime import date
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QFrame,
)
from models import Customer, STAGE_CHOICES


class CustomerListPanel(QWidget):
    customer_selected = pyqtSignal(int)
    customer_add_requested = pyqtSignal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._build_ui()
        self._connect_signals()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("客户列表")
        title.setStyleSheet("font-size: 15px; font-weight: bold; padding: 4px 0;")
        layout.addWidget(title)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索公司/联系人/电话…")
        layout.addWidget(self.search_edit)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)
        self.tag_combo = QComboBox()
        self.tag_combo.setPlaceholderText("标签")
        self.stage_combo = QComboBox()
        self.stage_combo.setPlaceholderText("阶段")
        filter_row.addWidget(self.tag_combo, 1)
        filter_row.addWidget(self.stage_combo, 1)
        layout.addLayout(filter_row)

        sort_row = QHBoxLayout()
        sort_row.setSpacing(4)
        sort_row.addWidget(QLabel("排序:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["最近联系", "公司名称", "下次跟进", "创建时间"])
        self.sort_order_btn = QPushButton("降序")
        self.sort_order_btn.setCheckable(True)
        self.sort_order_btn.setChecked(True)
        sort_row.addWidget(self.sort_combo, 1)
        sort_row.addWidget(self.sort_order_btn)
        layout.addLayout(sort_row)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #d0d0d0; border-radius: 4px; }
            QListWidget::item { padding: 6px; border-bottom: 1px solid #f0f0f0; }
            QListWidget::item:selected { background: #e6f2ff; color: #000; }
        """)
        layout.addWidget(self.list_widget, 1)

        self.add_btn = QPushButton("+ 新增客户")
        self.add_btn.setStyleSheet("""
            QPushButton { background: #2d7ff9; color: white; padding: 6px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #1e6ee0; }
        """)
        layout.addWidget(self.add_btn)

        self._refresh_filters()

    def _connect_signals(self):
        self.search_edit.textChanged.connect(self.refresh)
        self.tag_combo.currentIndexChanged.connect(self.refresh)
        self.stage_combo.currentIndexChanged.connect(self.refresh)
        self.sort_combo.currentIndexChanged.connect(self.refresh)
        self.sort_order_btn.toggled.connect(self._on_sort_order_toggled)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.add_btn.clicked.connect(self.customer_add_requested.emit)

    def _on_sort_order_toggled(self, checked):
        self.sort_order_btn.setText("降序" if checked else "升序")
        self.refresh()

    def _refresh_filters(self):
        current_tag = self.tag_combo.currentText()
        current_stage = self.stage_combo.currentText()
        self.tag_combo.blockSignals(True)
        self.stage_combo.blockSignals(True)
        self.tag_combo.clear()
        self.stage_combo.clear()
        self.tag_combo.addItem("全部标签", "")
        for t in self.db.list_all_tags():
            self.tag_combo.addItem(t, t)
        self.stage_combo.addItem("全部阶段", "")
        for s in STAGE_CHOICES:
            self.stage_combo.addItem(s, s)
        if current_tag:
            idx = self.tag_combo.findText(current_tag)
            if idx >= 0:
                self.tag_combo.setCurrentIndex(idx)
        if current_stage:
            idx = self.stage_combo.findText(current_stage)
            if idx >= 0:
                self.stage_combo.setCurrentIndex(idx)
        self.tag_combo.blockSignals(False)
        self.stage_combo.blockSignals(False)

    def refresh(self):
        self._refresh_filters()
        keyword = self.search_edit.text().strip()
        tag = self.tag_combo.currentData() or ""
        stage = self.stage_combo.currentData() or ""
        sort_map = {
            "最近联系": "last_contacted",
            "公司名称": "company",
            "下次跟进": "next_follow_up",
            "创建时间": "created_at",
        }
        sort_by = sort_map.get(self.sort_combo.currentText(), "last_contacted")
        sort_desc = self.sort_order_btn.isChecked()
        customers = self.db.list_customers(keyword, tag, stage, sort_by, sort_desc)
        self.list_widget.clear()
        today = date.today().isoformat()
        for c in customers:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            widget = self._build_item_widget(c, today)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

    def _build_item_widget(self, c: Customer, today: str) -> QWidget:
        w = QFrame()
        w.setStyleSheet("QFrame { background: transparent; }")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(2)

        company_label = QLabel(c.company or "(未命名)")
        company_label.setStyleSheet("font-weight: bold; font-size: 13px;")

        info_parts = []
        if c.contact:
            info_parts.append(c.contact)
        if c.phone:
            info_parts.append(c.phone)
        info_label = QLabel(" · ".join(info_parts) if info_parts else "无联系人信息")
        info_label.setStyleSheet("color: #666; font-size: 11px;")

        stage_label = QLabel(c.stage)
        stage_label.setStyleSheet("""
            color: #2d7ff9; font-size: 11px;
            background: #eaf2ff; padding: 1px 6px; border-radius: 3px;
        """)

        last_label_text = f"最后联系: {c.last_contacted[:10] if c.last_contacted else '—'}"
        last_label = QLabel(last_label_text)
        last_label.setStyleSheet("color: #888; font-size: 11px;")

        next_text = ""
        is_overdue = False
        if c.next_follow_up:
            next_text = f"下次: {c.next_follow_up}"
            if c.next_follow_up < today:
                is_overdue = True
        next_label = QLabel(next_text if next_text else "")
        if is_overdue:
            next_label.setStyleSheet("color: #d93025; font-size: 11px; font-weight: bold;")
        else:
            next_label.setStyleSheet("color: #2e7d32; font-size: 11px;")

        row1 = QHBoxLayout()
        row1.addWidget(company_label, 1)
        row1.addWidget(stage_label)
        lay.addLayout(row1)

        lay.addWidget(info_label)

        row3 = QHBoxLayout()
        row3.addWidget(last_label, 1)
        row3.addWidget(next_label)
        lay.addLayout(row3)

        if c.tags:
            tags_row = QHBoxLayout()
            tags_row.setSpacing(3)
            for t in c.tag_list()[:4]:
                tl = QLabel(t)
                tl.setStyleSheet("""
                    background: #f0f0f0; color: #555; font-size: 10px;
                    padding: 1px 5px; border-radius: 2px;
                """)
                tags_row.addWidget(tl)
            tags_row.addStretch(1)
            lay.addLayout(tags_row)

        return w

    def _on_item_clicked(self, item: QListWidgetItem):
        cid = item.data(Qt.ItemDataRole.UserRole)
        if cid is not None:
            self.customer_selected.emit(int(cid))

    def select_customer(self, customer_id: int):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == customer_id:
                self.list_widget.setCurrentRow(i)
                self.customer_selected.emit(customer_id)
                break
