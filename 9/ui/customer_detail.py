from datetime import date, datetime
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QDateEdit, QPushButton, QLabel, QTextEdit, QMessageBox,
    QFrame,
)
from models import Customer, STAGE_CHOICES


class CustomerDetailPanel(QWidget):
    customer_updated = pyqtSignal()
    customer_deleted = pyqtSignal()
    follow_up_added = pyqtSignal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_customer: Customer | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.title_label = QLabel("请选择或新增客户")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header.addWidget(self.title_label, 1)

        self.save_btn = QPushButton("保存修改")
        self.save_btn.setStyleSheet("""
            QPushButton { background: #2d7ff9; color: white; padding: 6px 14px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #1e6ee0; }
        """)
        self.delete_btn = QPushButton("删除客户")
        self.delete_btn.setStyleSheet("""
            QPushButton { background: #d93025; color: white; padding: 6px 14px;
                          border: none; border-radius: 4px; }
            QPushButton:hover { background: #b8261c; }
        """)
        header.addWidget(self.save_btn)
        header.addWidget(self.delete_btn)
        layout.addLayout(header)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(sep1)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.company_edit = QLineEdit()
        self.contact_edit = QLineEdit()
        self.phone_edit = QLineEdit()

        self.stage_combo = QComboBox()
        self.stage_combo.addItems(STAGE_CHOICES)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("多个标签用英文逗号分隔，如: 制造业,大客户")

        self.next_followup_edit = QDateEdit()
        self.next_followup_edit.setCalendarPopup(True)
        self.next_followup_edit.setDisplayFormat("yyyy-MM-dd")
        self.next_followup_edit.setDate(QDate.currentDate())
        self.next_clear_btn = QPushButton("清空")
        self.next_clear_btn.setFixedWidth(60)
        next_row = QHBoxLayout()
        next_row.addWidget(self.next_followup_edit, 1)
        next_row.addWidget(self.next_clear_btn)
        next_wrap = QWidget()
        next_wrap.setLayout(next_row)

        self.last_contacted_label = QLabel("—")
        self.last_contacted_label.setStyleSheet("color: #666;")
        self.created_at_label = QLabel("—")
        self.created_at_label.setStyleSheet("color: #666;")

        form.addRow("公司名称 *", self.company_edit)
        form.addRow("联系人", self.contact_edit)
        form.addRow("电话", self.phone_edit)
        form.addRow("跟进阶段", self.stage_combo)
        form.addRow("标签", self.tags_edit)
        form.addRow("下次跟进日期", next_wrap)
        form.addRow("最后联系", self.last_contacted_label)
        form.addRow("创建时间", self.created_at_label)

        layout.addLayout(form)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(sep2)

        fu_header = QLabel("新增跟进记录")
        fu_header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(fu_header)

        self.fu_summary = QTextEdit()
        self.fu_summary.setPlaceholderText("记录本次沟通摘要…")
        self.fu_summary.setFixedHeight(80)
        layout.addWidget(self.fu_summary)

        fu_action = QHBoxLayout()
        fu_action.addStretch(1)
        self.add_followup_btn = QPushButton("提交跟进")
        self.add_followup_btn.setStyleSheet("""
            QPushButton { background: #2e7d32; color: white; padding: 6px 16px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #1f6128; }
        """)
        fu_action.addWidget(self.add_followup_btn)
        layout.addLayout(fu_action)

        layout.addStretch(1)

        self._connect_signals()
        self._set_enabled(False)

    def _connect_signals(self):
        self.save_btn.clicked.connect(self._on_save)
        self.delete_btn.clicked.connect(self._on_delete)
        self.add_followup_btn.clicked.connect(self._on_add_followup)
        self.next_clear_btn.clicked.connect(
            lambda: self.next_followup_edit.setDate(QDate.fromString("2000-01-01", "yyyy-MM-dd"))
        )

    def _set_enabled(self, enabled: bool):
        for w in [self.company_edit, self.contact_edit, self.phone_edit,
                  self.stage_combo, self.tags_edit, self.next_followup_edit,
                  self.next_clear_btn, self.save_btn, self.delete_btn,
                  self.fu_summary, self.add_followup_btn]:
            w.setEnabled(enabled)

    def load_customer(self, customer_id: int | None):
        if customer_id is None:
            self.current_customer = None
            self.title_label.setText("请选择或新增客户")
            self._clear_form()
            self._set_enabled(False)
            return
        c = self.db.get_customer(customer_id)
        if not c:
            self.current_customer = None
            self._clear_form()
            self._set_enabled(False)
            return
        self.current_customer = c
        self.title_label.setText(c.company or "(未命名客户)")
        self.company_edit.setText(c.company)
        self.contact_edit.setText(c.contact)
        self.phone_edit.setText(c.phone)
        idx = self.stage_combo.findText(c.stage)
        self.stage_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.tags_edit.setText(c.tags)
        if c.next_follow_up:
            d = QDate.fromString(c.next_follow_up, "yyyy-MM-dd")
            if d.isValid():
                self.next_followup_edit.setDate(d)
        self.last_contacted_label.setText(c.last_contacted or "—")
        self.created_at_label.setText(c.created_at or "—")
        self.fu_summary.clear()
        self._set_enabled(True)

    def load_new_customer(self):
        self.current_customer = None
        self.title_label.setText("新增客户")
        self._clear_form()
        self.company_edit.setFocus()
        self._set_enabled(True)
        self.delete_btn.setEnabled(False)
        self.add_followup_btn.setEnabled(False)

    def _clear_form(self):
        self.company_edit.clear()
        self.contact_edit.clear()
        self.phone_edit.clear()
        self.stage_combo.setCurrentIndex(0)
        self.tags_edit.clear()
        self.next_followup_edit.setDate(QDate.currentDate())
        self.last_contacted_label.setText("—")
        self.created_at_label.setText("—")
        self.fu_summary.clear()

    def _collect_form(self) -> Customer | None:
        company = self.company_edit.text().strip()
        if not company:
            QMessageBox.warning(self, "提示", "公司名称不能为空")
            return None
        c = self.current_customer or Customer()
        c.company = company
        c.contact = self.contact_edit.text().strip()
        c.phone = self.phone_edit.text().strip()
        c.stage = self.stage_combo.currentText()
        c.tags = self.tags_edit.text().strip()
        d = self.next_followup_edit.date()
        if d.isValid() and d.year() > 2000:
            c.next_follow_up = d.toString("yyyy-MM-dd")
        else:
            c.next_follow_up = None
        return c

    def _on_save(self):
        c = self._collect_form()
        if not c:
            return
        if c.id:
            self.db.update_customer(c)
            QMessageBox.information(self, "成功", "客户信息已更新")
        else:
            new_id = self.db.add_customer(c)
            c.id = new_id
            self.current_customer = c
            QMessageBox.information(self, "成功", "客户已创建")
        self.customer_updated.emit()
        self.load_customer(c.id)

    def _on_delete(self):
        if not self.current_customer or not self.current_customer.id:
            return
        ret = QMessageBox.question(
            self, "确认删除",
            f"确定要删除客户「{self.current_customer.company}」吗？\n相关跟进记录也会被删除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_customer(self.current_customer.id)
        self.current_customer = None
        self._clear_form()
        self._set_enabled(False)
        self.title_label.setText("请选择或新增客户")
        self.customer_deleted.emit()

    def _on_add_followup(self):
        if not self.current_customer or not self.current_customer.id:
            return
        summary = self.fu_summary.toPlainText().strip()
        if not summary:
            QMessageBox.warning(self, "提示", "跟进内容不能为空")
            return
        from models import FollowUp
        fu = FollowUp(
            customer_id=self.current_customer.id,
            summary=summary,
            contacted_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.db.add_follow_up(fu)
        self.fu_summary.clear()
        self.last_contacted_label.setText(fu.contacted_at)
        self.follow_up_added.emit()
        QMessageBox.information(self, "成功", "跟进记录已添加")
