from datetime import date
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame,
)
from models import Customer


class TodayFollowUpDialog(QDialog):
    def __init__(self, customers: list[Customer], parent=None):
        super().__init__(parent)
        self.setWindowTitle("今日待跟进提醒")
        self.setMinimumSize(480, 360)
        self.customers = customers
        self.selected_id: int | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        today = date.today().isoformat()
        overdue = [c for c in self.customers if c.next_follow_up and c.next_follow_up < today]
        due_today = [c for c in self.customers if c.next_follow_up and c.next_follow_up == today]

        title = QLabel("📋 今日待跟进提醒")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel(
            f"过期未跟进: <span style='color:#d93025;font-weight:bold;'>{len(overdue)}</span> 家，"
            f"今日到期: <span style='color:#f57c00;font-weight:bold;'>{len(due_today)}</span> 家，"
            f"共 <b>{len(self.customers)}</b> 家需要跟进"
        )
        subtitle.setTextFormat(Qt.TextFormat.RichText)
        subtitle.setStyleSheet("color: #555;")
        layout.addWidget(subtitle)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #d0d0d0; border-radius: 4px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #f0f0f0; }
            QListWidget::item:selected { background: #e6f2ff; color: #000; }
        """)
        layout.addWidget(self.list_widget, 1)

        for c in self.customers:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            w = self._build_item(c, today)
            item.setSizeHint(w.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, w)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton("知道了")
        close_btn.setStyleSheet("""
            QPushButton { padding: 6px 18px; border: 1px solid #ccc;
                          border-radius: 4px; background: white; }
            QPushButton:hover { background: #f5f5f5; }
        """)
        open_btn = QPushButton("打开选中客户")
        open_btn.setStyleSheet("""
            QPushButton { padding: 6px 18px; border: none; border-radius: 4px;
                          background: #2d7ff9; color: white; font-weight: bold; }
            QPushButton:hover { background: #1e6ee0; }
        """)
        btn_row.addWidget(close_btn)
        btn_row.addWidget(open_btn)
        layout.addLayout(btn_row)

        close_btn.clicked.connect(self.accept)
        open_btn.clicked.connect(self._on_open)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)

    def _build_item(self, c: Customer, today: str) -> QWidget:
        w = QFrame()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(2)

        is_overdue = c.next_follow_up and c.next_follow_up < today
        is_today = c.next_follow_up and c.next_follow_up == today

        row1 = QHBoxLayout()
        name = QLabel(c.company or "(未命名)")
        name.setStyleSheet("font-weight: bold; font-size: 13px;")

        badge_text = ""
        badge_style = ""
        if is_overdue:
            badge_text = "已过期"
            badge_style = "background:#d93025;color:white;"
        elif is_today:
            badge_text = "今日到期"
            badge_style = "background:#f57c00;color:white;"
        else:
            badge_text = "即将到期"
            badge_style = "background:#fbc02d;color:#333;"

        badge = QLabel(badge_text)
        badge.setStyleSheet(f"{badge_style} font-size:11px; padding:1px 8px; border-radius:3px;")

        row1.addWidget(name, 1)
        row1.addWidget(badge)
        lay.addLayout(row1)

        info = QLabel(f"联系人: {c.contact or '—'}  |  电话: {c.phone or '—'}  |  阶段: {c.stage}")
        info.setStyleSheet("color: #666; font-size: 11px;")
        lay.addWidget(info)

        if c.next_follow_up:
            next_l = QLabel(f"下次跟进日期: {c.next_follow_up}")
            if is_overdue:
                next_l.setStyleSheet("color: #d93025; font-size: 11px; font-weight: bold;")
            else:
                next_l.setStyleSheet("color: #555; font-size: 11px;")
            lay.addWidget(next_l)

        return w

    def _on_open(self):
        item = self.list_widget.currentItem()
        if item:
            self.selected_id = int(item.data(Qt.ItemDataRole.UserRole))
            self.accept()

    def _on_double_click(self, item: QListWidgetItem):
        self.selected_id = int(item.data(Qt.ItemDataRole.UserRole))
        self.accept()
