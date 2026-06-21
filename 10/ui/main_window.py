from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QIcon, QPixmap, QPainter, QBrush, QPen, QColor, QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSplitter,
    QMessageBox,
    QStatusBar,
    QFileDialog,
    QToolBar,
    QSizePolicy,
    QApplication,
    QMenu,
)

from core.models import Customer, FollowUpRecord
from core.storage import CustomerStorage
from ui.widgets import FilterBar, CustomerListWidget, CustomerDetailWidget, TimelineWidget
from ui.dialogs import (
    CustomerEditDialog,
    FollowUpDialog,
    TodayFollowUpDialog,
    CsvImportDialog,
)


def _app_icon() -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QBrush(QColor("#3498db")))
    p.setPen(QPen(QColor("#ffffff"), 3))
    p.drawEllipse(6, 6, 52, 52)
    p.setPen(QPen(QColor("#ffffff")))
    f = p.font()
    f.setBold(True)
    f.setPointSize(26)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, "客")
    p.end()
    return QIcon(pm)


class MainWindow(QMainWindow):
    def __init__(self, storage: CustomerStorage, auto_show_today: bool = True):
        super().__init__()
        self._storage = storage
        self._current_customer: Optional[Customer] = None
        self._seeded_sample = False
        self._auto_show_today_flag = auto_show_today

        self.setWindowTitle("客户跟进工具 · CRM")
        self.setWindowIcon(_app_icon())
        self.resize(1400, 820)
        self.setMinimumSize(1100, 680)
        self._build_style()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

        self._refresh_tags()
        self._refresh_list()

    # ---------------------------------------------------------------- UI
    def _build_style(self) -> None:
        self.setStyleSheet(
            "QMainWindow { background-color: #1e1e1e; }"
            " QToolBar { background-color: #232323; border-bottom: 1px solid #333; padding: 4px; spacing: 6px; }"
            " QToolBar QToolButton, QToolBar QPushButton {"
            "   background-color: #2d2d2d; color: #e6e6e6; padding: 6px 14px;"
            "   border: 1px solid #3d3d3d; border-radius: 4px; }"
            " QToolBar QToolButton:hover, QToolBar QPushButton:hover {"
            "   background-color: #3a3a3a; }"
            " QToolBar #primary {"
            "   background-color: #3498db; color: #fff; border: none; font-weight: bold; }"
            " QToolBar #primary:hover { background-color: #2980b9; }"
            " QToolBar #success {"
            "   background-color: #27ae60; color: #fff; border: none; font-weight: bold; }"
            " QToolBar #success:hover { background-color: #219150; }"
            " QStatusBar { background-color: #232323; color: #aaa; border-top: 1px solid #333; padding: 0 8px; }"
            " QSplitter::handle { background-color: #333; }"
            " QSplitter::handle:horizontal { width: 2px; }"
        )

    def _build_toolbar(self) -> None:
        tb = QToolBar("主工具栏", self)
        tb.setMovable(False)
        tb.setIconSize(tb.iconSize())
        self.addToolBar(tb)

        add_btn = QPushButton("➕ 新增客户")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._on_add_customer)
        tb.addWidget(add_btn)

        today_btn = QPushButton("📌 今日待跟进")
        today_btn.clicked.connect(self._show_today_dialog)
        tb.addWidget(today_btn)

        import_btn = QPushButton("📥 导入 CSV")
        import_btn.clicked.connect(self._on_import_csv)
        tb.addWidget(import_btn)

        export_btn = QPushButton("📤 导出 CSV")
        export_btn.clicked.connect(self._on_export_csv)
        tb.addWidget(export_btn)

        tb.addSeparator()

        seed_btn = QPushButton("🧪 加载演示数据")
        seed_btn.setObjectName("success")
        seed_btn.clicked.connect(self._seed_sample_data)
        tb.addWidget(seed_btn)

        tb.addSeparator()

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._refresh_all)
        tb.addWidget(refresh_btn)

        tb.addSeparator()

        del_btn = QPushButton("🗑️ 删除客户")
        del_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #e74c3c; padding: 6px 14px;"
            " border: 1px solid #e74c3c; border-radius: 4px; }"
            " QPushButton:hover { background-color: rgba(231,76,60,0.15); }"
        )
        del_btn.clicked.connect(self._on_delete_current)
        tb.addWidget(del_btn)

    def _build_body(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.filter_bar = FilterBar()
        self.filter_bar.filters_changed.connect(self._refresh_list)
        self.filter_bar.reset_requested.connect(self._refresh_tags)
        root.addWidget(self.filter_bar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(2)

        # 左栏：客户列表
        left_frame = QFrame()
        left_frame.setStyleSheet(
            "QFrame { background-color: #1e1e1e; border-right: 1px solid #333; }"
        )
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.customer_list = CustomerListWidget()
        self.customer_list.customer_selected.connect(self._on_customer_selected)
        self.customer_list.customer_context_menu.connect(self._on_customer_context)
        left_layout.addWidget(self.customer_list)
        left_frame.setMinimumWidth(300)

        # 中栏：客户详情
        mid_frame = QFrame()
        mid_frame.setStyleSheet(
            "QFrame { background-color: #1e1e1e; border-right: 1px solid #333; }"
        )
        mid_layout = QVBoxLayout(mid_frame)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        self.customer_detail = CustomerDetailWidget()
        self.customer_detail.edit_requested.connect(self._on_edit_current)
        self.customer_detail.add_followup_requested.connect(self._on_add_followup)
        self.customer_detail.delete_requested.connect(self._on_delete_current)
        mid_layout.addWidget(self.customer_detail)
        mid_frame.setMinimumWidth(380)

        # 右栏：跟进时间线
        right_frame = QFrame()
        right_frame.setStyleSheet("QFrame { background-color: #1e1e1e; }")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline = TimelineWidget()
        right_layout.addWidget(self.timeline)
        right_frame.setMinimumWidth(360)

        splitter.addWidget(left_frame)
        splitter.addWidget(mid_frame)
        splitter.addWidget(right_frame)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 4)
        splitter.setSizes([360, 520, 520])

        root.addWidget(splitter, 1)

    def _build_statusbar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_label = QLabel("就绪")
        sb.addWidget(self._status_label, 1)

        self._today_stat = QLabel("今日待跟进：加载中…")
        self._today_stat.setStyleSheet("color: #f39c12; padding: 0 6px;")
        sb.addPermanentWidget(self._today_stat)

    # --------------------------------------------------------- data flow
    def _refresh_tags(self) -> None:
        tags = self._storage.all_tags()
        self.filter_bar.set_tags(tags)

    def _refresh_list(self) -> None:
        params = self.filter_bar.params()
        customers = self._storage.list_customers(**params)
        self.customer_list.populate(customers)
        n = self._storage.get_today_count() if hasattr(self._storage, "get_today_count") else None
        if n is None:
            today_list = self._storage.list_today_follow_ups()
            n = len(today_list)
        self._today_stat.setText(f"今日/过期待跟进：{n} 位")
        if not self._current_customer and customers:
            self.customer_list.select_customer(customers[0].id)
        elif self._current_customer:
            self.customer_list.select_customer(self._current_customer.id)
        self._status(f"已加载 {len(customers)} 位客户" + (
            f"（筛选：{params.get('search') or '无'} / 标签：{params.get('tag') or '全部'}）"
        ))

    def _refresh_all(self) -> None:
        self._refresh_tags()
        self._refresh_list()
        if self._current_customer:
            c = self._storage.get_customer(self._current_customer.id)
            if c:
                self._populate_customer(c)
            else:
                self._populate_customer(None)

    def _populate_customer(self, customer: Optional[Customer]) -> None:
        self._current_customer = customer
        self.customer_detail.set_customer(customer)
        records = self._storage.list_follow_ups(customer.id) if customer else []
        self.timeline.set_records(customer, records)

    def _on_customer_selected(self, customer_id: int) -> None:
        customer = self._storage.get_customer(customer_id)
        self._populate_customer(customer)

    def _on_customer_context(self, customer_id: int, action) -> None:
        if action.text() == "删除客户":
            c = self._storage.get_customer(customer_id)
            if not c:
                return
            r = QMessageBox.question(
                self,
                "删除客户",
                f"确定要删除客户「{c.company}」吗？\n所有跟进记录将被级联删除。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if r == QMessageBox.Yes:
                self._storage.delete_customer(customer_id)
                if self._current_customer and self._current_customer.id == customer_id:
                    self._populate_customer(None)
                self._refresh_all()
                self._status(f"已删除客户：{c.company}")

    # --------------------------------------------------------- actions
    def _on_add_customer(self) -> None:
        dlg = CustomerEditDialog(self._storage, parent=self)
        if dlg.exec():
            c = dlg.result_customer()
            if c:
                self._refresh_all()
                self.customer_list.select_customer(c.id)
                self._status(f"已新增客户：{c.company}")

    def _on_edit_current(self) -> None:
        if not self._current_customer:
            return
        dlg = CustomerEditDialog(self._storage, self._current_customer, self)
        if dlg.exec():
            c = dlg.result_customer()
            if c:
                self._refresh_all()
                self.customer_list.select_customer(c.id)
                self._status(f"已更新客户：{c.company}")

    def _on_delete_current(self) -> None:
        if not self._current_customer:
            return
        self._on_customer_context(self._current_customer.id, type("A", (), {"text": lambda s: "删除客户"})())

    def _on_add_followup(self) -> None:
        if not self._current_customer:
            return
        dlg = FollowUpDialog(self._current_customer, self)
        if dlg.exec():
            rec = dlg.result_record()
            if rec:
                self._storage.add_follow_up(rec)
                if dlg.should_update_next_follow_up():
                    c = self._storage.get_customer(self._current_customer.id)
                    if c:
                        new_next = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d 09:30:00")
                        c.next_follow_up = new_next
                        self._storage.update_customer(c)
                self._refresh_all()
                self.customer_list.select_customer(self._current_customer.id)
                self._status(f"已为「{self._current_customer.company}」新增 1 条跟进记录")

    def _show_today_dialog(self) -> None:
        today_list = self._storage.list_today_follow_ups()
        dlg = TodayFollowUpDialog(today_list, self)
        dlg.open_customer.connect(
            lambda cid: (self.customer_list.select_customer(cid), self._on_customer_selected(cid))
        )
        dlg.exec()

    def _on_import_csv(self) -> None:
        dlg = CsvImportDialog(self._storage, self)
        if dlg.exec():
            stats = dlg.result_stats()
            if stats:
                created, merged, _ = stats
                self._refresh_all()
                self._status(f"CSV 导入完成：新增 {created}，合并 {merged}")
                QMessageBox.information(
                    self,
                    "导入完成",
                    f"新增客户：{created} 位\n合并客户：{merged} 位",
                )

    def _on_export_csv(self) -> None:
        default_name = f"customers_{date.today().isoformat()}.csv"
        p, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", str(Path.home() / default_name), "CSV 文件 (*.csv)"
        )
        if not p:
            return
        try:
            n = self._storage.export_csv(p)
            self._status(f"已导出 {n} 位客户到 {p}")
            QMessageBox.information(self, "导出完成", f"成功导出 {n} 位客户。")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    # --------------------------------------------------------- seeding
    def _seed_sample_data(self) -> None:
        if self._seeded_sample:
            r = QMessageBox.question(
                self, "提示", "演示数据已加载过，是否再次补充一批？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if r != QMessageBox.Yes:
                return
        self._seeded_sample = True
        today = date.today()

        def d(offset_days, hour=9, minute=30):
            dt = datetime.combine(today, datetime.min.time()) + timedelta(days=offset_days, hours=hour, minutes=minute)
            return dt.isoformat(timespec="seconds")

        seed = [
            ("星海科技有限公司", "张明", "13800138000", "zhang@xinghai.com", "重点,互联网", "深圳", "近期关注SaaS方案", d(-3), d(-1)),
            ("北辰贸易", "李经理", "13900139001", "li@beichen.cn", "老客户", "广州", "下月准备续签", d(0), d(10, 14, 0)),
            ("云峰咨询", "王总", "13700137002", "wang@yunfeng.cn", "潜在", "北京", "需要定制化方案", d(-12), d(0)),
            ("绿洲环保科技", "赵工", "13600136003", "", "新客户", "上海", "", d(2), d(5, 10, 0)),
            ("蓝海文化传媒", "孙女士", "13500135004", "sun@lanhai.com", "重点,传媒", "杭州", "对视频方案有兴趣", d(-20), d(-10)),
            ("鸿远建材", "陈老板", "13400134005", "", "建材", "成都", "", d(5), d(8, 11, 30)),
            ("智联信息技术", "刘总", "13300133006", "liu@zhilian.com", "重点", "南京", "有一个百万级项目", d(0, 15, 0), d(1)),
            ("恒运物流", "周经理", "", "zhou@hengyun.cn", "物流,老客户", "武汉", "", d(1), d(-2)),
            ("星辰教育集团", "吴主任", "13100131008", "wu@star.edu", "教育", "西安", "暑期招生", d(7), d(3)),
            ("盛泰金融", "郑总", "13000130009", "", "金融,高意向", "北京", "合规评估中", d(0, 11, 0), d(-5)),
        ]
        fu_seed = [
            ("星海科技有限公司", d(-1, 10, 30), "电话", "介绍SaaS年付方案，对方要求演示PPT", "客户回复下周提供内部排期", "下周三前发送资料包"),
            ("星海科技有限公司", d(-10, 15, 0), "微信", "初次添加好友，交换名片", "对产品比较认可", None),
            ("北辰贸易", d(10, 14, 30), "面谈", "续签合同细节敲定", "同意原合同8%涨点", None),
            ("北辰贸易", d(5, 9, 0), "电话", "提醒合同到期，客户要求面谈", "约了10号见", None),
            ("云峰咨询", d(0, 16, 0), "邮件", "发送定制化方案v1", "客户回复已阅读并转内部评估", "下周二跟进反馈"),
            ("绿洲环保科技", d(5, 10, 15), "电话", "确认需求后安排技术对接", "需要约技术同事", "技术对接时间确认中"),
            ("蓝海文化传媒", d(-10, 11, 30), "面谈", "视频方案初步沟通", "客户偏好短视频方案", None),
            ("蓝海文化传媒", d(-2, 14, 0), "微信", "发送方案给客户", "客户反馈需内部讨论", "下周再跟进"),
            ("智联信息技术", d(1, 10, 30), "电话", "与采购确认招标时间", "预计月底有消息", "月底跟进"),
            ("恒运物流", d(-2, 9, 0), "电话", "确认新年度框架合同", "客户说内部走流程", "月底回签"),
            ("星辰教育集团", d(3, 15, 0), "微信", "讨论暑期招生方案", "客户说需要下周校长拍板", None),
            ("盛泰金融", d(-5, 10, 0), "面谈", "合规评估初次见面", "客户说2周内反馈", None),
            ("盛泰金融", d(0, 11, 10), "电话", "合规评估进度跟进", "已通过内部评审，商务推进中", "本周签合同"),
        ]

        for row in seed:
            company, contact, phone, email, tags, addr, notes, created, next_fu = row
            existing = self._storage.find_by_company(company)
            if existing:
                continue
            c = Customer(
                company=company, contact_name=contact, phone=phone, email=email,
                tags=tags, address=addr, notes=notes, next_follow_up=next_fu, created_at=created,
            )
            cid = self._storage.add_customer(c)

            for fu_row in fu_seed:
                if fu_row[0] == company:
                    _, ct_time, ch, content, result, next_step = fu_row
                    cust = self._storage.get_customer(cid)
                    if cust and (cust.last_contact is None or ct_time > cust.last_contact):
                        cust.last_contact = ct_time
                        self._storage.update_customer(cust)
                    rec = FollowUpRecord(
                        customer_id=cid, contact_time=ct_time, channel=ch,
                        content=content, result=result, next_step=next_step or "",
                    )
                    self._storage.add_follow_up(rec)

        self._refresh_all()
        self._status("演示数据加载完成")

    # --------------------------------------------------------- utils
    def _status(self, msg: str) -> None:
        self._status_label.setText(msg)
        self.statusBar().showMessage(msg, 5000)

    # --------------------------------------------------------- today count
    def showEvent(self, event) -> None:
        super().showEvent(event)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(300, self._auto_show_today_if_any)

    def _auto_show_today_if_any(self) -> None:
        if not self._auto_show_today_flag:
            return
        today_list = self._storage.list_today_follow_ups()
        if today_list:
            self._show_today_dialog()
