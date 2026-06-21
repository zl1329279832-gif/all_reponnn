from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QFrame, QScrollArea,
)
from models import FollowUp


class TimelinePanel(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("沟通时间线")
        title.setStyleSheet("font-size: 15px; font-weight: bold; padding: 4px 0;")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #d0d0d0; border-radius: 4px; background: #fafafa; }
            QListWidget::item { padding: 0; border-bottom: 1px solid #e8e8e8; }
        """)
        layout.addWidget(self.list_widget, 1)

        self.count_label = QLabel("共 0 条记录")
        self.count_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.count_label)

    def load_customer(self, customer_id: int | None):
        self.list_widget.clear()
        if customer_id is None:
            self.count_label.setText("共 0 条记录")
            return
        items = self.db.list_follow_ups(customer_id)
        self.count_label.setText(f"共 {len(items)} 条记录")
        for fu in items:
            self._add_item(fu)

    def refresh(self, customer_id: int | None):
        self.load_customer(customer_id)

    def _add_item(self, fu: FollowUp):
        item = QListWidgetItem()
        w = self._build_followup_widget(fu)
        item.setSizeHint(w.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, w)

    def _build_followup_widget(self, fu: FollowUp) -> QWidget:
        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        outer = QHBoxLayout(wrap)
        outer.setContentsMargins(8, 10, 8, 10)
        outer.setSpacing(10)

        timeline_col = QVBoxLayout()
        timeline_col.setSpacing(0)
        timeline_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        dot = QLabel()
        dot.setFixedSize(12, 12)
        dot.setStyleSheet("""
            background: #2d7ff9; border-radius: 6px;
            border: 2px solid white;
        """)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #cfd8dc;")
        line.setFixedWidth(2)
        timeline_col.addWidget(dot, 0, Qt.AlignmentFlag.AlignHCenter)
        timeline_col.addWidget(line, 1)

        content_col = QVBoxLayout()
        content_col.setSpacing(4)

        time_label = QLabel(fu.contacted_at)
        time_label.setStyleSheet("color: #2d7ff9; font-weight: bold; font-size: 12px;")

        summary_label = QLabel(fu.summary)
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet("color: #333; font-size: 13px; line-height: 1.5;")

        content_col.addWidget(time_label)
        content_col.addWidget(summary_label)

        outer.addLayout(timeline_col)
        outer.addLayout(content_col, 1)

        return wrap
