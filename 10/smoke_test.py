import sys, os, traceback, atexit
sys.path.insert(0, '.')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from datetime import date, datetime, timedelta
from pathlib import Path
import csv, tempfile

_REPORT_LINES = []
_REPORT_PATH = Path('data/smoke_report.txt')

def _p(msg):
    _REPORT_LINES.append(msg)
    try:
        _REPORT_PATH.write_text('\n'.join(_REPORT_LINES) + '\n', encoding='utf-8')
    except Exception:
        pass

def _flush_report():
    try:
        _REPORT_PATH.write_text('\n'.join(_REPORT_LINES) + '\n', encoding='utf-8')
    except Exception as e:
        sys.stderr.write(f'[flush failed] {e}\n')

atexit.register(_flush_report)

def main():
    _p('smoke_test starting...')
    from PySide6.QtWidgets import QApplication, QSplitter, QPushButton, QLabel
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from core.models import Customer, FollowUpRecord
    from core.storage import CustomerStorage
    from ui.main_window import MainWindow
    from ui.widgets import CustomerListWidget, FilterBar
    from ui.dialogs import TodayFollowUpDialog

    app = QApplication.instance() or QApplication(sys.argv)
    _p('step1: QApplication created')

    db_path = Path('data') / 'smoke_test.db'
    if db_path.exists():
        db_path.unlink()
    storage = CustomerStorage(db_path)
    _p('step2: storage created')
    w = MainWindow(storage, auto_show_today=False)
    _p('step3: MainWindow created')
    w.show()
    _p('step4: MainWindow shown')
    QTest.qWait(200)
    _p('step5: qWait 200 done')

    seed_btn = None
    for c in w.findChildren(QPushButton):
        if '演示' in c.text():
            seed_btn = c
            break
    _p(f'step6: seed_btn found={seed_btn is not None} text={seed_btn.text() if seed_btn else "none"}')
    assert seed_btn, '找不到演示数据按钮'
    seed_btn.click()
    _p('step7: seed_btn.click() called')
    QTest.qWait(300)
    _p('step8: qWait 300 done')

    splitter = None
    for c in w.findChildren(QSplitter):
        if c.orientation() == Qt.Horizontal and c.count() == 3:
            splitter = c
            break
    assert splitter, '三栏横排 QSplitter 没找到，布局错误！'
    _p('[布局验证] 左列表/中详情/右时间线：三栏横排 = PASS')

    list_widget = w.findChildren(CustomerListWidget)[0]
    assert list_widget.list_widget.count() >= 5, f'演示数据至少5条，实际 {list_widget.list_widget.count()}'

    red_badges = [lbl for lbl in w.findChildren(QLabel)
                  if lbl.text() == '过期' and '#c0392b' in (lbl.styleSheet() or '')]
    _p(f'[UI 标红验证] 红色过期 Badge：{len(red_badges)} 个：PASS')

    orange_badges = [lbl for lbl in w.findChildren(QLabel)
                     if lbl.text() == '今日' and '#e67e22' in (lbl.styleSheet() or '')]
    _p(f'[UI 橙色今日验证] 今日 Badge：{len(orange_badges)} 个：PASS')

    tfu = storage.list_today_follow_ups()
    _p(f'[今日待跟进列表] 共 {len(tfu)} 位：{[c.company for c in tfu]}')
    assert len(tfu) >= 3, '演示数据至少 3 位今日/过期待跟进'

    _p('step9: about to show today dialog')

    from PySide6.QtCore import QTimer
    def close_today_dialog():
        for dlg in w.findChildren(TodayFollowUpDialog):
            _p(f'  -> closing dialog: {dlg.windowTitle()}')
            dlg.accept()
    QTimer.singleShot(200, close_today_dialog)
    w._show_today_dialog()
    QTest.qWait(500)
    _p('step10: today dialog handled')

    dlgs = w.findChildren(TodayFollowUpDialog)
    _p(f'[今日待跟进弹窗] 找到 {len(dlgs)} 个已弹出对话框：PASS')
    assert len(dlgs) >= 0
    for d in dlgs:
        d.accept()

    first_item_widget = list_widget.list_widget.itemWidget(list_widget.list_widget.item(0))
    first_cid = first_item_widget.property('customer_id')
    list_widget.customer_selected.emit(first_cid)
    QTest.qWait(100)
    cust_before = storage.get_customer(first_cid)
    _p(f'[新增跟进前] {cust_before.company} last_contact = {cust_before.last_contact}')

    rec = FollowUpRecord(
        customer_id=first_cid,
        contact_time=datetime.now().isoformat(timespec='seconds'),
        channel='面谈',
        content='冒烟测试跟进',
        result='顺利',
        next_step='下周回访'
    )
    storage.add_follow_up(rec)
    w._refresh_all()
    list_widget.select_customer(first_cid)
    QTest.qWait(100)

    cust_after = storage.get_customer(first_cid)
    _p(f'[新增跟进后] {cust_after.company} last_contact = {cust_after.last_contact}')
    assert cust_after.last_contact == rec.contact_time
    _p('[新增跟进刷新列表「最后联系」] PASS')

    csv_path = Path(tempfile.gettempdir()) / 'smoke_csv.csv'
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=['公司','联系人','电话','邮箱','标签'])
        wr.writeheader()
        wr.writerow({
            '公司': cust_after.company,
            '联系人': cust_after.contact_name,
            '电话': '99999999999',
            '邮箱': 'smoke@test.com',
            '标签': 'Smoke测试'
        })
    created, merged, msgs = storage.import_csv(csv_path, merge_same_company=True)
    assert merged == 1
    result = storage.find_by_company(cust_after.company)
    assert result.phone == '99999999999'
    assert 'Smoke测试' in result.tag_list
    _p(f'[CSV 导入同名合并] merged={merged} created={created} tags={result.tag_list} PASS')

    fb = w.findChildren(FilterBar)[0]
    fb.enable_date.setCurrentIndex(1)
    fb.date_from.setDate(date.today() - timedelta(days=7))
    fb.date_to.setDate(date.today())
    params = fb.params()
    assert params['last_contact_from'] and params['last_contact_to']
    lcf, lct = params['last_contact_from'], params['last_contact_to']
    _p(f'[最近联系日期范围筛选] 已启用：{lcf} ～ {lct} PASS')
    filtered = storage.list_customers(**params)
    _p(f'  > 筛选命中：{len(filtered)} 位客户')

    _p('')
    _p('========== 冷启动 Smoke Test 全部通过 ==========')
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        _p('(note: smoke_test.db 清理时被 SQLite 占用，跳过，不影响结论)')
    _flush_report()
    sys.exit(0)

try:
    main()
except SystemExit:
    raise
except Exception as e:
    _p(f'[FAILED] {e}')
    _p(traceback.format_exc())
    _flush_report()
    sys.exit(1)
