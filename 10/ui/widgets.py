from datetime import date, datetime, timedelta
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor, QFont, QAction
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QFormLayout,
    QTextEdit,
    QPushButton,
    QDateEdit,
    QSizePolicy,
    QScrollArea,
    QMenu,
    QAbstractItemView,
)

from core.models import Customer, FollowUpRecord


# =====================================================================
# FilterBar: 搜索 / 标签 / 日期范围（最近联系时间）/ 排序
# =====================================================================
class FilterBar(QWidget):
    filters_changed = Signal()
    reset_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        self.setStyleSheet(
            "QWidget { background-color: #2a2a2a; }"
            " QLineEdit, QComboBox, QDateEdit {"
            "   background-color: #3a3a3a; color: #ffffff; padding: 5px 8px;"
            "   border: 1px solid #555; border-radius: 4px; }"
            " QLabel { color: #cccccc; }"
            " QPushButton { background-color: #3a3a3a; color: #ffffff; padding: 5px 14px;"
            "   border: 1px solid #555; border-radius: 4px; }"
            " QPushButton:hover { background-color: #4a4a4a; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索公司 / 联系人 / 电话")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(lambda *_: self.filters_changed.emit())
        self.search_edit.setFixedWidth(260)
        layout.addWidget(self.search_edit)

        self.tag_combo = QComboBox()
        self.tag_combo.setMinimumWidth(140)
        self.tag_combo.currentTextChanged.connect(lambda *_: self.filters_changed.emit())
        layout.addWidget(QLabel("标签:"))
        layout.addWidget(self.tag_combo)

        today = QDate.currentDate()

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(today.addDays(-30))
        self.date_from.setSpecialValueText("不限")
        self.date_from.setMinimumDate(QDate(2000, 1, 1))
        self.date_from.userDateChanged.connect(lambda *_: self.filters_changed.emit())
        layout.addWidget(QLabel("最近联系:"))
        layout.addWidget(self.date_from)

        til = QLabel("～")
        til.setStyleSheet("color: #888888;")
        layout.addWidget(til)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(today)
        self.date_to.userDateChanged.connect(lambda *_: self.filters_changed.emit())
        layout.addWidget(self.date_to)

        self.enable_date = QComboBox()
        self.enable_date.addItem("不过滤最近联系", "none")
        self.enable_date.addItem("启用日期范围筛选", "range")
        self.enable_date.setCurrentIndex(0)
        self.enable_date.currentIndexChanged.connect(self._on_enable_changed)
        self.enable_date.currentIndexChanged.connect(lambda *_: self.filters_changed.emit())
        layout.addWidget(self.enable_date)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("按下次跟进排序", "next_follow_up")
        self.sort_combo.addItem("按公司名排序", "company")
        self.sort_combo.addItem("按最近联系排序", "last_contact")
        self.sort_combo.addItem("按创建时间排序", "created_at")
        self.sort_combo.currentIndexChanged.connect(lambda *_: self.filters_changed.emit())
        layout.addSpacing(10)
        layout.addWidget(QLabel("排序:"))
        layout.addWidget(self.sort_combo)

        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset)
        layout.addWidget(reset_btn)

        layout.addStretch()
        self._on_enable_changed(0)

    def _on_enable_changed(self, idx: int) -> None:
        enabled = self.enable_date.currentData() == "range"
        self.date_from.setEnabled(enabled)
        self.date_to.setEnabled(enabled)

    def reset(self) -> None:
        self.search_edit.blockSignals(True)
        self.search_edit.clear()
        self.search_edit.blockSignals(False)
        if self.tag_combo.count() > 0:
            self.tag_combo.blockSignals(True)
            self.tag_combo.setCurrentIndex(0)
            self.tag_combo.blockSignals(False)
        self.enable_date.blockSignals(True)
        self.enable_date.setCurrentIndex(0)
        self.enable_date.blockSignals(False)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self._on_enable_changed(0)
        self.sort_combo.blockSignals(True)
        self.sort_combo.setCurrentIndex(0)
        self.sort_combo.blockSignals(False)
        self.reset_requested.emit()
        self.filters_changed.emit()

    def set_tags(self, tags: List[str]) -> None:
        current = self.tag_combo.currentText() if self.tag_combo.currentIndex() >= 0 else ""
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem("全部标签", "")
        for t in tags:
            self.tag_combo.addItem(t, t)
        idx = self.tag_combo.findText(current)
        if idx >= 0:
            self.tag_combo.setCurrentIndex(idx)
        self.tag_combo.blockSignals(False)

    def params(self) -> dict:
        date_from = None
        date_to = None
        if self.enable_date.currentData() == "range":
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
        return {
            "search": self.search_edit.text().strip(),
            "tag": self.tag_combo.currentData() if self.tag_combo.currentData() else "",
            "last_contact_from": date_from,
            "last_contact_to": date_to,
            "sort_by": self.sort_combo.currentData() or "next_follow_up",
        }


# =====================================================================
# CustomerListWidget: 左栏客户列表
# =====================================================================
class CustomerListWidget(QWidget):
    customer_selected = Signal(int)
    customer_context_menu = Signal(int, QAction)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet(
            "QFrame { background-color: #232323; border-bottom: 1px solid #333; }"
            " QLabel { color: #cccccc; padding: 10px 14px; font-weight: bold; }"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(4, 4, 4, 4)
        title = QLabel("📋 客户列表")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title.setFont(title_font)
        hl.addWidget(title)
        self.count_label = QLabel("共 0 位")
        self.count_label.setStyleSheet("color: #888888; font-weight: normal;")
        hl.addStretch()
        hl.addWidget(self.count_label)
        layout.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #1e1e1e; border: none; outline: none; }"
            " QListWidget::item { padding: 0; border-bottom: 1px solid #2a2a2a; }"
            " QListWidget::item:selected { background-color: #3b3b5e; }"
        )
        self.list_widget.currentItemChanged.connect(self._on_item_changed)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context)
        layout.addWidget(self.list_widget, 1)

        self._items_data = {}

    def _on_item_changed(self, curr: QListWidgetItem, _prev) -> None:
        if curr:
            cid = self.list_widget.itemWidget(curr).property("customer_id")
            if cid is not None:
                self.customer_selected.emit(int(cid))

    def _on_context(self, pos) -> None:
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        cid = self.list_widget.itemWidget(item).property("customer_id")
        if cid is None:
            return
        menu = QMenu(self)
        act_open = menu.addAction("查看详情")
        act_del = menu.addAction("删除客户")
        chosen = menu.exec(self.list_widget.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == act_open:
            self.customer_selected.emit(int(cid))
        elif chosen == act_del:
            self.customer_context_menu.emit(int(cid), act_del)

    def populate(self, customers: List[Customer]) -> None:
        self.list_widget.clear()
        self._items_data.clear()
        today = date.today()
        for c in customers:
            item = QListWidgetItem(self.list_widget)
            widget = self._build_item(c, today)
            widget.setProperty("customer_id", c.id)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            self._items_data[c.id] = item
        self.count_label.setText(f"共 {len(customers)} 位")

    def _build_item(self, customer: Customer, today: date) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(8)
        name = QLabel(customer.company)
        name_font = QFont()
        name_font.setPointSize(10)
        name_font.setBold(True)
        name.setFont(name_font)
        name.setStyleSheet("color: #ffffff;")
        name.setWordWrap(True)
        top.addWidget(name, 1)

        overdue = customer.is_overdue(today)
        is_today = customer.is_today(today)
        if overdue:
            badge = QLabel("过期")
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(42, 20)
            badge.setStyleSheet(
                "QLabel { background-color: #c0392b; color: #ffffff;"
                " border-radius: 4px; font-weight: bold; font-size: 11px; }"
            )
            top.addWidget(badge)
        elif is_today:
            badge = QLabel("今日")
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(42, 20)
            badge.setStyleSheet(
                "QLabel { background-color: #e67e22; color: #ffffff;"
                " border-radius: 4px; font-weight: bold; font-size: 11px; }"
            )
            top.addWidget(badge)

        outer.addLayout(top)

        info = QHBoxLayout()
        info.setSpacing(12)
        sub = QLabel(customer.contact_name or "—")
        sub.setStyleSheet("color: #bbbbbb; font-size: 12px;")
        info.addWidget(sub)
        if customer.phone:
            p = QLabel(customer.phone)
            p.setStyleSheet("color: #9ecfe7; font-size: 12px;")
            info.addWidget(p)
        info.addStretch()

        last_text = _format_last_contact(customer.last_contact)
        last = QLabel(last_text)
        last.setStyleSheet("color: #888888; font-size: 12px;")
        info.addWidget(last)
        outer.addLayout(info)

        if customer.tags:
            tag_row = QHBoxLayout()
            tag_row.setSpacing(4)
            for t in customer.tag_list[:4]:
                tag = QLabel(t)
                tag.setStyleSheet(
                    "QLabel { background-color: #34495e; color: #ecf0f1;"
                    " padding: 2px 6px; border-radius: 3px; font-size: 11px; }"
                )
                tag_row.addWidget(tag)
            if len(customer.tag_list) > 4:
                more = QLabel(f"+{len(customer.tag_list) - 4}")
                more.setStyleSheet("color: #888; font-size: 11px;")
                tag_row.addWidget(more)
            tag_row.addStretch()
            outer.addLayout(tag_row)

        if customer.next_follow_up:
            try:
                d_str = customer.next_follow_up[:10]
            except Exception:
                d_str = customer.next_follow_up
            color = "#e74c3c" if overdue else ("#f39c12" if is_today else "#7f8c8d")
            nxt = QLabel(f"下次跟进: {d_str}")
            nxt.setStyleSheet(f"color: {color}; font-size: 12px;")
            outer.addWidget(nxt)
        w.adjustSize()
        return w

    def select_customer(self, customer_id: int) -> None:
        if customer_id in self._items_data:
            self.list_widget.setCurrentItem(self._items_data[customer_id])

    def current_customer_id(self) -> Optional[int]:
        item = self.list_widget.currentItem()
        if not item:
            return None
        w = self.list_widget.itemWidget(item)
        cid = w.property("customer_id") if w else None
        return int(cid) if cid is not None else None


def _format_last_contact(value: Optional[str]) -> str:
    if not value:
        return "未联系"
    try:
        dt = datetime.fromisoformat(value[:19])
    except Exception:
        return value[:10] if len(value) >= 10 else value
    delta = datetime.now() - dt
    days = delta.days
    if days == 0:
        return "今天"
    if days == 1:
        return "昨天"
    if days < 7:
        return f"{days} 天前"
    if days < 30:
        weeks = days // 7
        return f"{weeks} 周前"
    return dt.strftime("%Y-%m-%d")


# =====================================================================
# CustomerDetailWidget: 中栏客户详情
# =====================================================================
class CustomerDetailWidget(QWidget):
    edit_requested = Signal()
    add_followup_requested = Signal()
    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._customer: Optional[Customer] = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet(
            "QFrame { background-color: #232323; border-bottom: 1px solid #333; }"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 10, 14, 10)
        self.title = QLabel("客户详情")
        tf = QFont()
        tf.setPointSize(11)
        tf.setBold(True)
        self.title.setFont(tf)
        self.title.setStyleSheet("color: #cccccc;")
        hl.addWidget(self.title)
        hl.addStretch()

        self.add_fu_btn = QPushButton("➕ 新增跟进")
        self.add_fu_btn.setStyleSheet(self._primary_btn())
        self.add_fu_btn.clicked.connect(self.add_followup_requested.emit)
        hl.addWidget(self.add_fu_btn)

        self.edit_btn = QPushButton("✏️ 编辑")
        self.edit_btn.setStyleSheet(self._secondary_btn())
        self.edit_btn.clicked.connect(self.edit_requested.emit)
        hl.addWidget(self.edit_btn)

        self.del_btn = QPushButton("🗑️ 删除")
        self.del_btn.setStyleSheet(self._danger_btn())
        self.del_btn.clicked.connect(self.delete_requested.emit)
        hl.addWidget(self.del_btn)

        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            "QScrollArea { background: #1e1e1e; border: none; }"
        )
        self.scroll_content = QWidget()
        self.body = QVBoxLayout(self.scroll_content)
        self.body.setContentsMargins(18, 18, 18, 18)
        self.body.setSpacing(12)

        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border-radius: 8px; }"
        )
        sf = QVBoxLayout(self.summary_frame)
        sf.setContentsMargins(16, 14, 16, 14)
        self.company_label = QLabel()
        self.company_label.setStyleSheet(
            "color: #ffffff; font-size: 18px; font-weight: bold; padding-bottom: 4px;"
        )
        sf.addWidget(self.company_label)
        self.tag_labels = QHBoxLayout()
        self.tag_labels.setSpacing(6)
        self.tag_container = QWidget()
        self.tag_container.setLayout(self.tag_labels)
        sf.addWidget(self.tag_container)
        self.body.addWidget(self.summary_frame)

        self.info_frame = QFrame()
        self.info_frame.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border-radius: 8px; }"
        )
        self.info_layout = QFormLayout(self.info_frame)
        self.info_layout.setContentsMargins(16, 14, 16, 14)
        self.info_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.info_layout.setSpacing(8)
        self.info_layout.setHorizontalSpacing(16)
        self._contact_name_val = self._info_row("联系人:", "—")
        self._phone_val = self._info_row("电话:", "—")
        self._email_val = self._info_row("邮箱:", "—")
        self._address_val = self._info_row("地址:", "—")
        self._next_val = self._info_row("下次跟进:", "—")
        self._last_val = self._info_row("最后联系:", "—")
        self._created_val = self._info_row("创建时间:", "—")
        self.body.addWidget(self.info_frame)

        self.notes_label = QLabel("备注")
        self.notes_label.setStyleSheet("color: #cccccc; font-weight: bold;")
        self.body.addWidget(self.notes_label)

        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setStyleSheet(
            "QTextEdit { background-color: #2a2a2a; color: #dddddd; padding: 10px;"
            " border: 1px solid #333; border-radius: 6px; }"
        )
        self.notes_text.setMaximumHeight(140)
        self.body.addWidget(self.notes_text)

        self.body.addStretch()
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll, 1)

        self.set_customer(None)

    def _info_row(self, label: str, default: str) -> QLabel:
        val = QLabel(default)
        val.setStyleSheet("color: #e8e8e8;")
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        val.setWordWrap(True)
        ql = QLabel(label)
        ql.setStyleSheet("color: #888888;")
        self.info_layout.addRow(ql, val)
        return val

    def _primary_btn(self) -> str:
        return (
            "QPushButton { background-color: #3498db; color: white; padding: 5px 12px;"
            " border-radius: 4px; border: none; font-weight: bold; }"
            " QPushButton:hover { background-color: #2980b9; }"
            " QPushButton:disabled { background-color: #555; color: #aaa; }"
        )

    def _secondary_btn(self) -> str:
        return (
            "QPushButton { background-color: #3a3a3a; color: #ddd; padding: 5px 12px;"
            " border-radius: 4px; border: 1px solid #555; }"
            " QPushButton:hover { background-color: #4a4a4a; }"
            " QPushButton:disabled { color: #666; }"
        )

    def _danger_btn(self) -> str:
        return (
            "QPushButton { background-color: transparent; color: #e74c3c; padding: 5px 12px;"
            " border-radius: 4px; border: 1px solid #e74c3c; }"
            " QPushButton:hover { background-color: rgba(231,76,60,0.15); }"
            " QPushButton:disabled { color: #666; border-color: #666; }"
        )

    def set_customer(self, customer: Optional[Customer]) -> None:
        self._customer = customer
        has = customer is not None
        self.add_fu_btn.setEnabled(has)
        self.edit_btn.setEnabled(has)
        self.del_btn.setEnabled(has)
        if not has:
            self.title.setText("客户详情（请选择左侧客户）")
            self.company_label.setText("")
            self._clear_tag_labels()
            self._contact_name_val.setText("—")
            self._phone_val.setText("—")
            self._email_val.setText("—")
            self._address_val.setText("—")
            self._next_val.setText("—")
            self._next_val.setStyleSheet("color: #e8e8e8;")
            self._last_val.setText("—")
            self._created_val.setText("—")
            self.notes_text.setPlainText("")
            return

        self.title.setText(f"客户详情 · {customer.company}")
        self.company_label.setText(customer.company)

        self._clear_tag_labels()
        for t in customer.tag_list:
            tag = QLabel(t)
            tag.setStyleSheet(
                "QLabel { background-color: #16a085; color: white;"
                " padding: 3px 8px; border-radius: 3px; font-size: 12px; }"
            )
            self.tag_labels.addWidget(tag)
        self.tag_labels.addStretch()

        self._contact_name_val.setText(customer.contact_name or "—")
        self._phone_val.setText(customer.phone or "—")
        self._email_val.setText(customer.email or "—")
        self._address_val.setText(customer.address or "—")

        if customer.next_follow_up:
            try:
                d = date.fromisoformat(customer.next_follow_up[:10])
                text = customer.next_follow_up[:16].replace("T", " ")
                today = date.today()
                if d < today:
                    color = "#e74c3c"
                    text += " · 已过期"
                elif d == today:
                    color = "#f39c12"
                    text += " · 今日"
                else:
                    color = "#27ae60"
            except Exception:
                text = customer.next_follow_up
                color = "#e8e8e8"
            self._next_val.setText(text)
            self._next_val.setStyleSheet(f"color: {color}; font-weight: bold;")
        else:
            self._next_val.setText("未安排")
            self._next_val.setStyleSheet("color: #888888;")

        if customer.last_contact:
            try:
                text = customer.last_contact[:16].replace("T", " ")
            except Exception:
                text = customer.last_contact
            self._last_val.setText(text)
        else:
            self._last_val.setText("尚未联系")

        try:
            dt = datetime.fromisoformat(customer.created_at[:19])
            self._created_val.setText(dt.strftime("%Y-%m-%d %H:%M"))
        except Exception:
            self._created_val.setText(customer.created_at or "—")

        self.notes_text.setPlainText(customer.notes or "")

    def _clear_tag_labels(self) -> None:
        while self.tag_labels.count():
            it = self.tag_labels.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()


# =====================================================================
# TimelineWidget: 右栏跟进时间线
# =====================================================================
class TimelineWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet(
            "QFrame { background-color: #232323; border-bottom: 1px solid #333; }"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 10, 14, 10)
        t = QLabel("📝 跟进时间线")
        tf = QFont()
        tf.setPointSize(11)
        tf.setBold(True)
        t.setFont(tf)
        t.setStyleSheet("color: #cccccc;")
        hl.addWidget(t)
        self.count = QLabel("共 0 条")
        self.count.setStyleSheet("color: #888888;")
        hl.addStretch()
        hl.addWidget(self.count)
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { background: #1e1e1e; border: none; }")
        self._container = QWidget()
        self._vb = QVBoxLayout(self._container)
        self._vb.setContentsMargins(16, 16, 16, 16)
        self._vb.setSpacing(12)
        self._vb.addStretch()
        self.scroll.setWidget(self._container)
        layout.addWidget(self.scroll, 1)

        self.set_records(None, [])

    def set_records(self, customer: Optional[Customer], records: List[FollowUpRecord]) -> None:
        while self._vb.count() > 1:
            it = self._vb.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

        self.count.setText(f"共 {len(records)} 条")
        if customer is None:
            empty = self._empty_card("请先选择一位客户")
            self._vb.insertWidget(0, empty)
            return
        if not records:
            empty = self._empty_card(f"「{customer.company}」暂无跟进记录，点击「➕ 新增跟进」开始吧")
            self._vb.insertWidget(0, empty)
            return

        for i, fu in enumerate(records):
            card = self._make_record_card(fu, is_last=(i == len(records) - 1))
            self._vb.insertWidget(i, card)

    def _empty_card(self, text: str) -> QWidget:
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(20, 30, 20, 30)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 13px;")
        l.addWidget(label)
        return w

    def _make_record_card(self, fu: FollowUpRecord, is_last: bool) -> QWidget:
        w = QWidget()
        main = QHBoxLayout(w)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        dot_col = QVBoxLayout()
        dot_col.setContentsMargins(4, 6, 12, 6)
        dot_col.setSpacing(0)
        dot = QWidget()
        dot.setFixedSize(14, 14)
        dot.setStyleSheet(
            "QWidget { background-color: #3498db; border: 3px solid #1e1e1e;"
            " border-radius: 7px; }"
        )
        dot_col.addWidget(dot)
        if not is_last:
            line = QWidget()
            line.setStyleSheet("background-color: #3a3a3a;")
            line.setFixedWidth(2)
            dot_col.addWidget(line, 1)
        else:
            dot_col.addStretch()
        main.addLayout(dot_col)

        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border-radius: 6px; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 12)
        card_layout.setSpacing(6)

        head = QHBoxLayout()
        try:
            dt = datetime.fromisoformat(fu.contact_time[:19])
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            time_str = fu.contact_time
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet("color: #9ecfe7; font-weight: bold; font-size: 12px;")
        head.addWidget(time_lbl)
        head.addStretch()
        channel_lbl = QLabel(f"【{fu.channel or '其他'}】")
        channel_lbl.setStyleSheet(
            "QLabel { background-color: #34495e; color: #ecf0f1;"
            " padding: 2px 8px; border-radius: 3px; font-size: 11px; }"
        )
        head.addWidget(channel_lbl)
        card_layout.addLayout(head)

        if fu.content:
            content_lbl = QLabel(fu.content)
            content_lbl.setWordWrap(True)
            content_lbl.setStyleSheet("color: #e8e8e8; font-size: 13px;")
            card_layout.addWidget(content_lbl)

        if fu.result:
            res = QLabel(f"结果：{fu.result}")
            res.setWordWrap(True)
            res.setStyleSheet("color: #27ae60; font-size: 12px;")
            card_layout.addWidget(res)

        if fu.next_step:
            ns = QLabel(f"下一步：{fu.next_step}")
            ns.setWordWrap(True)
            ns.setStyleSheet("color: #f39c12; font-size: 12px;")
            card_layout.addWidget(ns)

        main.addWidget(card, 1)
        return w
