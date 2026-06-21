from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, QDate, QDateTime, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QBrush, QPen
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFormLayout,
    QTextEdit,
    QComboBox,
    QDateTimeEdit,
    QDateEdit,
    QScrollArea,
    QFileDialog,
    QFrame,
    QMessageBox,
    QCheckBox,
    QSizePolicy,
    QPlainTextEdit,
    QDialogButtonBox,
)

from core.models import Customer, FollowUpRecord
from core.storage import CustomerStorage


# =====================================================================
# Icons helper
# =====================================================================
def _make_icon(color_hex: str, letter: str = "C") -> QIcon:
    pm = QPixmap(32, 32)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QBrush(QColor(color_hex)))
    p.setPen(QPen(QColor("#ffffff"), 2))
    p.drawEllipse(2, 2, 28, 28)
    p.setPen(QPen(QColor("#ffffff")))
    f = QFont()
    f.setBold(True)
    f.setPointSize(14)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, letter)
    p.end()
    return QIcon(pm)


# =====================================================================
# CustomerEditDialog: 新增/编辑客户
# =====================================================================
class CustomerEditDialog(QDialog):
    def __init__(self, storage: CustomerStorage, customer: Optional[Customer] = None, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._customer = customer
        self.setWindowTitle("编辑客户" if customer else "新增客户")
        self.setModal(True)
        self.resize(480, 560)
        self._build()

    def _build(self) -> None:
        self.setStyleSheet(
            "QDialog { background-color: #1e1e1e; color: #ffffff; }"
            " QLabel { color: #dddddd; }"
            " QLineEdit, QComboBox, QDateEdit, QTextEdit, QDateTimeEdit {"
            "   background-color: #2a2a2a; color: #ffffff; padding: 6px 8px;"
            "   border: 1px solid #444; border-radius: 4px; }"
            " QPushButton { padding: 6px 18px; border-radius: 4px; }"
            " QPushButton#primary { background-color: #3498db; color: #fff; border: none; font-weight: bold; }"
            " QPushButton#primary:hover { background-color: #2980b9; }"
            " QPushButton#secondary { background-color: #3a3a3a; color: #ddd; border: 1px solid #555; }"
            " QPushButton#secondary:hover { background-color: #4a4a4a; }"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setSpacing(10)

        self.company_edit = QLineEdit()
        self.company_edit.setPlaceholderText("例：XX科技有限公司")
        form.addRow("公司名称 *:", self.company_edit)

        self.contact_name_edit = QLineEdit()
        form.addRow("联系人:", self.contact_name_edit)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("手机或座机")
        form.addRow("电话:", self.phone_edit)

        self.email_edit = QLineEdit()
        form.addRow("邮箱:", self.email_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("多个用英文或中文逗号分隔，如：重点,老客户")
        form.addRow("标签:", self.tags_edit)

        self.address_edit = QLineEdit()
        form.addRow("地址:", self.address_edit)

        self.next_follow_up = QDateTimeEdit()
        self.next_follow_up.setCalendarPopup(True)
        self.next_follow_up.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.next_follow_up.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.next_follow_up.setMinimumDateTime(QDateTime.fromString("2000-01-01 00:00", "yyyy-MM-dd HH:mm"))
        form.addRow("下次跟进:", self.next_follow_up)

        self.no_next_check = QCheckBox("暂不安排下次跟进")
        form.addRow("", self.no_next_check)
        self.no_next_check.stateChanged.connect(
            lambda s: self.next_follow_up.setEnabled(not bool(s))
        )

        outer.addLayout(form)

        notes_lbl = QLabel("备注:")
        outer.addWidget(notes_lbl)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("关于该客户的其他信息，如背景、需求、意向度等")
        self.notes_edit.setMaximumHeight(120)
        outer.addWidget(self.notes_edit, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("secondary")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("保存")
        ok.setObjectName("primary")
        ok.clicked.connect(self._on_save)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        outer.addLayout(buttons)

        if self._customer:
            self._populate()

    def _populate(self) -> None:
        c = self._customer
        self.company_edit.setText(c.company)
        self.contact_name_edit.setText(c.contact_name)
        self.phone_edit.setText(c.phone)
        self.email_edit.setText(c.email)
        self.tags_edit.setText(c.tags)
        self.address_edit.setText(c.address)
        self.notes_edit.setPlainText(c.notes)
        if c.next_follow_up:
            try:
                dt = QDateTime.fromString(c.next_follow_up[:16].replace("T", " "), "yyyy-MM-dd HH:mm")
                if dt.isValid():
                    self.next_follow_up.setDateTime(dt)
                else:
                    self.no_next_check.setChecked(True)
            except Exception:
                self.no_next_check.setChecked(True)
        else:
            self.no_next_check.setChecked(True)

    def _on_save(self) -> None:
        company = self.company_edit.text().strip()
        if not company:
            QMessageBox.warning(self, "提示", "公司名称不能为空")
            return
        existing = self._storage.find_by_company(company)
        if existing and (self._customer is None or existing.id != self._customer.id):
            r = QMessageBox.question(
                self,
                "公司已存在",
                f"公司「{company}」已存在，是否合并到该客户（不新增）？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if r == QMessageBox.Cancel:
                return
            if r == QMessageBox.Yes:
                merged = self._storage.merge_customer(existing, self._to_customer())
                self._customer = merged
                self.accept()
                return

        if self._customer:
            self._update_customer()
        else:
            self._customer = self._to_customer()
            self._customer.id = self._storage.add_customer(self._customer)
        self.accept()

    def _to_customer(self) -> Customer:
        next_fu = None
        if not self.no_next_check.isChecked():
            next_fu = self.next_follow_up.dateTime().toString("yyyy-MM-dd HH:mm:00")
        c = self._customer or Customer()
        return Customer(
            id=c.id,
            company=self.company_edit.text().strip(),
            contact_name=self.contact_name_edit.text().strip(),
            phone=self.phone_edit.text().strip(),
            email=self.email_edit.text().strip(),
            tags=self.tags_edit.text().strip(),
            address=self.address_edit.text().strip(),
            notes=self.notes_edit.toPlainText().strip(),
            next_follow_up=next_fu,
            created_at=c.created_at,
            last_contact=c.last_contact,
        )

    def _update_customer(self) -> None:
        merged = self._to_customer()
        self._storage.update_customer(merged)
        self._customer = merged

    def result_customer(self) -> Optional[Customer]:
        return self._customer


# =====================================================================
# FollowUpDialog: 新增跟进记录
# =====================================================================
class FollowUpDialog(QDialog):
    CHANNELS = ["电话", "微信", "邮件", "面谈", "QQ", "其他"]

    def __init__(self, customer: Customer, parent=None):
        super().__init__(parent)
        self._customer = customer
        self._record: Optional[FollowUpRecord] = None
        self.setWindowTitle(f"新增跟进 - {customer.company}")
        self.setModal(True)
        self.resize(500, 520)
        self._build()

    def _build(self) -> None:
        self.setStyleSheet(
            "QDialog { background-color: #1e1e1e; color: #ffffff; }"
            " QLabel { color: #dddddd; }"
            " QLineEdit, QComboBox, QDateTimeEdit, QTextEdit {"
            "   background-color: #2a2a2a; color: #ffffff; padding: 6px 8px;"
            "   border: 1px solid #444; border-radius: 4px; }"
            " QPushButton { padding: 6px 18px; border-radius: 4px; }"
            " QPushButton#primary { background-color: #27ae60; color: #fff; border: none; font-weight: bold; }"
            " QPushButton#primary:hover { background-color: #219150; }"
            " QPushButton#secondary { background-color: #3a3a3a; color: #ddd; border: 1px solid #555; }"
            " QPushButton#secondary:hover { background-color: #4a4a4a; }"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(12)

        head = QLabel(f"📝 为 <b>{self._customer.company}</b> 添加跟进记录")
        head.setTextFormat(Qt.RichText)
        head.setStyleSheet("color: #fff; font-size: 14px; padding-bottom: 6px;")
        outer.addWidget(head)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setSpacing(10)

        self.time_edit = QDateTimeEdit()
        self.time_edit.setCalendarPopup(True)
        self.time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.time_edit.setDateTime(QDateTime.currentDateTime())
        self.time_edit.setMaximumDateTime(QDateTime.currentDateTime())
        form.addRow("联系时间 *:", self.time_edit)

        self.channel_combo = QComboBox()
        self.channel_combo.addItems(self.CHANNELS)
        form.addRow("沟通方式:", self.channel_combo)

        outer.addLayout(form)

        l1 = QLabel("沟通内容 *:")
        outer.addWidget(l1)
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("描述本次沟通的主要内容，越详细越好")
        self.content_edit.setMaximumHeight(120)
        outer.addWidget(self.content_edit)

        l2 = QLabel("沟通结果:")
        outer.addWidget(l2)
        self.result_edit = QLineEdit()
        self.result_edit.setPlaceholderText("如：已发送报价单 / 客户表示下周回复 等")
        outer.addWidget(self.result_edit)

        l3 = QLabel("下一步计划:")
        outer.addWidget(l3)
        self.next_edit = QLineEdit()
        self.next_edit.setPlaceholderText("如：下周三前发送样品 / 周五再打电话确认 等")
        outer.addWidget(self.next_edit)

        self.update_next_check = QCheckBox(
            "自动更新客户「下次跟进」时间为当前时间后 7 天"
        )
        self.update_next_check.setChecked(True)
        self.update_next_check.setStyleSheet("color: #cccccc; padding: 4px 0;")
        outer.addWidget(self.update_next_check)

        outer.addStretch()
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("secondary")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("保存跟进")
        ok.setObjectName("primary")
        ok.clicked.connect(self._on_save)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        outer.addLayout(buttons)

    def _on_save(self) -> None:
        content = self.content_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "提示", "请填写沟通内容")
            return
        time_str = self.time_edit.dateTime().toString("yyyy-MM-dd HH:mm:00")
        self._record = FollowUpRecord(
            customer_id=self._customer.id or 0,
            contact_time=time_str,
            channel=self.channel_combo.currentText(),
            content=content,
            result=self.result_edit.text().strip(),
            next_step=self.next_edit.text().strip(),
        )
        self.accept()

    def result_record(self) -> Optional[FollowUpRecord]:
        return self._record

    def should_update_next_follow_up(self) -> bool:
        return self.update_next_check.isChecked()


# =====================================================================
# TodayFollowUpDialog: 今日待跟进弹窗
# =====================================================================
class TodayFollowUpDialog(QDialog):
    open_customer = Signal(int)

    def __init__(self, customers: List[Customer], parent=None):
        super().__init__(parent)
        self._customers = customers
        self.setWindowTitle("今日待跟进")
        self.setModal(False)
        self.resize(640, 500)
        self._build()

    def _build(self) -> None:
        self.setStyleSheet(
            "QDialog { background-color: #1e1e1e; color: #ffffff; }"
            " QLabel#title { color: #fff; font-size: 16px; font-weight: bold; padding: 0; }"
            " QLabel#subtitle { color: #aaa; }"
            " QPushButton { padding: 6px 18px; border-radius: 4px; }"
            " QPushButton#primary { background-color: #3498db; color: #fff; border: none; font-weight: bold; }"
            " QPushButton#primary:hover { background-color: #2980b9; }"
            " QPushButton#secondary { background-color: #3a3a3a; color: #ddd; border: 1px solid #555; }"
            " QPushButton#secondary:hover { background-color: #4a4a4a; }"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(14)

        head = QHBoxLayout()
        t_lay = QVBoxLayout()
        title = QLabel("📌 今日待跟进客户")
        title.setObjectName("title")
        t_lay.addWidget(title)
        subtitle = QLabel(f"共 {len(self._customers)} 位客户需要跟进")
        subtitle.setObjectName("subtitle")
        t_lay.addWidget(subtitle)
        head.addLayout(t_lay)
        head.addStretch()
        outer.addLayout(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            "QScrollArea { background: #1e1e1e; border: 1px solid #333; border-radius: 6px; }"
        )
        container = QWidget()
        self._vb = QVBoxLayout(container)
        self._vb.setContentsMargins(8, 8, 8, 8)
        self._vb.setSpacing(6)

        today = date.today()
        overdue = [c for c in self._customers if c.is_overdue(today)]
        today_only = [c for c in self._customers if c.is_today(today)]

        if overdue:
            head_lbl = QLabel(f"⚠️ 已过期 ({len(overdue)})")
            head_lbl.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 6px 4px;")
            self._vb.addWidget(head_lbl)
            for c in overdue:
                self._vb.addWidget(self._build_item(c, is_overdue=True))

        if today_only:
            head_lbl = QLabel(f"📅 今日到期 ({len(today_only)})")
            head_lbl.setStyleSheet("color: #f39c12; font-weight: bold; padding: 6px 4px;")
            self._vb.addWidget(head_lbl)
            for c in today_only:
                self._vb.addWidget(self._build_item(c, is_overdue=False))

        if not self._customers:
            empty = QLabel("🎉 今天没有待跟进的客户，享受一下空闲时间吧！")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #888; padding: 30px; font-size: 14px;")
            self._vb.addWidget(empty)

        self._vb.addStretch()
        self.scroll.setWidget(container)
        outer.addWidget(self.scroll, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondary")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        outer.addLayout(buttons)

    def _build_item(self, customer: Customer, is_overdue: bool) -> QWidget:
        w = QWidget()
        w.setCursor(Qt.PointingHandCursor)
        w.setStyleSheet(
            "QWidget { background-color: #2a2a2a; border-radius: 6px;"
            " border-left: 4px solid " + ("#e74c3c" if is_overdue else "#f39c12") + "; }"
            " QWidget:hover { background-color: #343434; }"
        )
        row = QHBoxLayout(w)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(f"<b>{customer.company}</b> · {customer.contact_name or '未命名联系人'}")
        name.setTextFormat(Qt.RichText)
        name.setStyleSheet("color: #ffffff;")
        info.addWidget(name)

        try:
            d_str = customer.next_follow_up[:16].replace("T", " ")
        except Exception:
            d_str = customer.next_follow_up or ""
        if is_overdue:
            hint = f"<span style='color:#e74c3c;'>过期 · {d_str}</span>"
        else:
            hint = f"<span style='color:#f39c12;'>今日 · {d_str}</span>"
        sub = QLabel(f"{hint}" + (f" · 📞 {customer.phone}" if customer.phone else ""))
        sub.setTextFormat(Qt.RichText)
        sub.setStyleSheet("color: #bbbbbb;")
        info.addWidget(sub)
        row.addLayout(info, 1)

        btn = QPushButton("打开")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; padding: 4px 14px;"
            " border: none; border-radius: 4px; font-weight: bold; }"
            " QPushButton:hover { background-color: #2980b9; }"
        )
        cid = customer.id

        def _emit():
            self.open_customer.emit(cid)
            self.accept()

        btn.clicked.connect(_emit)
        w.mousePressEvent = lambda e: _emit() if e.button() == Qt.LeftButton else None
        row.addWidget(btn)
        return w


# =====================================================================
# CsvImportDialog: CSV 导入向导（同名合并）
# =====================================================================
class CsvImportDialog(QDialog):
    def __init__(self, storage: CustomerStorage, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._path: Optional[str] = None
        self._result: Optional[Tuple[int, int, List[str]]] = None
        self.setWindowTitle("导入客户 CSV")
        self.setModal(True)
        self.resize(600, 480)
        self._build()

    def _build(self) -> None:
        self.setStyleSheet(
            "QDialog { background-color: #1e1e1e; color: #ffffff; }"
            " QLabel { color: #dddddd; }"
            " QLineEdit, QPlainTextEdit {"
            "   background-color: #2a2a2a; color: #ffffff; padding: 6px 8px;"
            "   border: 1px solid #444; border-radius: 4px; }"
            " QCheckBox { color: #dddddd; padding: 4px 0; }"
            " QPushButton { padding: 6px 18px; border-radius: 4px; }"
            " QPushButton#primary { background-color: #27ae60; color: #fff; border: none; font-weight: bold; }"
            " QPushButton#primary:hover { background-color: #219150; }"
            " QPushButton#primary:disabled { background-color: #555; color: #aaa; }"
            " QPushButton#secondary { background-color: #3a3a3a; color: #ddd; border: 1px solid #555; }"
            " QPushButton#secondary:hover { background-color: #4a4a4a; }"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        intro = QLabel(
            "请选择要导入的 CSV 文件。支持以下表头（不区分大小写，中英文均可）：<br>"
            "<i>公司/Company, 联系人/Contact_Name, 电话/Phone, 邮箱/Email, "
            "标签/Tags, 地址/Address, 备注/Notes, 下次跟进/Next_Follow_Up</i>"
        )
        intro.setTextFormat(Qt.RichText)
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #ddd;")
        outer.addWidget(intro)

        file_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择一个 CSV 文件...")
        file_row.addWidget(self.path_edit, 1)
        browse = QPushButton("浏览")
        browse.setObjectName("secondary")
        browse.clicked.connect(self._on_browse)
        file_row.addWidget(browse)
        outer.addLayout(file_row)

        self.merge_check = QCheckBox("同名公司合并（推荐：非空字段取新值，标签取并集）")
        self.merge_check.setChecked(True)
        outer.addWidget(self.merge_check)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("导入进度与结果信息显示在此处...")
        outer.addWidget(self.log, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close = QPushButton("关闭")
        close.setObjectName("secondary")
        close.clicked.connect(self.accept if self._result else self.reject)
        self.import_btn = QPushButton("开始导入")
        self.import_btn.setObjectName("primary")
        self.import_btn.clicked.connect(self._on_import)
        buttons.addWidget(close)
        buttons.addWidget(self.import_btn)
        outer.addLayout(buttons)

    def _on_browse(self) -> None:
        p, _ = QFileDialog.getOpenFileName(
            self, "选择 CSV 文件", str(Path.home()), "CSV 文件 (*.csv)"
        )
        if p:
            self._path = p
            self.path_edit.setText(p)

    def _on_import(self) -> None:
        if not self._path or not Path(self._path).exists():
            QMessageBox.warning(self, "提示", "请选择一个有效的 CSV 文件")
            return
        self.import_btn.setEnabled(False)
        self.log.appendPlainText(f"开始导入: {self._path}\n合并模式: {self.merge_check.isChecked()}\n")
        try:
            created, merged, messages = self._storage.import_csv(
                self._path, merge_same_company=self.merge_check.isChecked()
            )
            self._result = (created, merged, messages)
            self.log.appendPlainText("=" * 50)
            self.log.appendPlainText(f"✅ 导入完成")
            self.log.appendPlainText(f"  - 新增客户：{created} 位")
            self.log.appendPlainText(f"  - 合并客户：{merged} 位")
            if messages:
                self.log.appendPlainText(f"  - 提示消息：{len(messages)} 条")
                for m in messages[:30]:
                    self.log.appendPlainText(f"     · {m}")
                if len(messages) > 30:
                    self.log.appendPlainText(f"     ... 其余 {len(messages) - 30} 条省略")
            else:
                self.log.appendPlainText("  - 提示消息：无")
        except Exception as e:
            self.log.appendPlainText(f"❌ 导入失败：{e}")
            QMessageBox.critical(self, "导入失败", str(e))
        self.import_btn.setEnabled(True)

    def result_stats(self) -> Optional[Tuple[int, int, List[str]]]:
        return self._result
