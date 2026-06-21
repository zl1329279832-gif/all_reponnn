"""
GUI 集成测试 - 使用 PyQt6 QTest 模拟真实用户操作
启动：python gui_integration_test.py
⚠️  必须在有图形界面的本地环境运行，会真实弹出窗口。
CI/流水线/headless 环境会自动检测并退出（建议在 CI 中只跑 acceptance_test.py）。
"""

import os
import sys
import time
import tempfile
import shutil


def _check_gui_environment():
    """检查是否有图形环境，没有则友好退出"""
    qt_platform = os.environ.get("QT_QPA_PLATFORM", "").lower()
    ci_env = any(os.environ.get(m, "").lower() in ("1", "true")
                 for m in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL"])
    is_offscreen = qt_platform == "offscreen"
    is_linux_no_display = sys.platform.startswith("linux") and not os.environ.get("DISPLAY")

    if ci_env or is_offscreen or is_linux_no_display:
        print("=" * 70)
        print("⚠️  GUI 集成测试无法在此环境运行")
        print("=" * 70)
        if ci_env:
            print("  原因：检测到 CI 环境（GitHub Actions / GitLab CI 等）")
        if is_offscreen:
            print("  原因：QT_QPA_PLATFORM=offscreen（offscreen 平台无法模拟真实交互）")
        if is_linux_no_display:
            print("  原因：Linux 环境未设置 DISPLAY 变量")
        print()
        print("  此测试需要真实图形环境（Windows / macOS / Linux 带 X11/Wayland）。")
        print("  CI 环境请运行：python acceptance_test.py  （核心逻辑无头测试）")
        print("  本地开发请运行：python gui_integration_test.py  （真实弹窗交互）")
        print("=" * 70)
        sys.exit(0)  # 正常退出，不报错，CI 不把它当失败


_check_gui_environment()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QModelIndex, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox, QStackedWidget, QInputDialog, QDialog
from PyQt6.QtGui import QColor, QBrush

from app.core import database as db
from app.core import scanner
from app.core import backup_manager as bm
from app.core.models import SaveSlot
from app.ui.main_window import MainWindow
from app.ui.compare_panel import ComparePanel
from app.ui.preview_panel import PreviewPanel
from app.ui.field_compare_panel import FieldComparePanel
from app.ui.text_diff_panel import TextDiffPanel


PASS = "[OK]  PASS"
FAIL = "[XX]  FAIL"
passed_count = 0
failed_count = 0


def step(title):
    print(f"\n{'='*70}")
    print(f"->  {title}")
    print(f"{'='*70}")


def check(description, condition):
    global passed_count, failed_count
    if condition:
        passed_count += 1
        print(f"{PASS}: {description}")
        return True
    else:
        failed_count += 1
        print(f"{FAIL}: {description}")
        return False


def wait_process_events(ms=200):
    QTest.qWait(ms)
    QApplication.processEvents()


def auto_close_dialog_after(ms=300, action="ok", input_text=None):
    """定时自动关闭即将弹出的各种模态对话框
    action: ok | yes | cancel | accept | reject
    input_text: 如果是 QInputDialog，要填入的文本
    """
    def _close():
        for w in QApplication.topLevelWidgets():
            if isinstance(w, QInputDialog):
                if input_text is not None:
                    w.setTextValue(input_text)
                if action in ("ok", "yes", "accept"):
                    w.accept()
                else:
                    w.reject()
                return
            if isinstance(w, QMessageBox):
                if action == "yes":
                    if w.button(QMessageBox.StandardButton.Yes):
                        w.button(QMessageBox.StandardButton.Yes).click()
                        return
                if action in ("ok", "yes", "accept"):
                    if w.button(QMessageBox.StandardButton.Ok):
                        w.button(QMessageBox.StandardButton.Ok).click()
                    else:
                        w.accept()
                else:
                    w.reject()
                return
            if isinstance(w, QDialog) and w.isModal():
                if action in ("ok", "yes", "accept"):
                    w.accept()
                else:
                    w.reject()
                return
    QTimer.singleShot(ms, _close)


def main():
    test_root = os.path.join(os.path.dirname(__file__), "test_data")
    if not os.path.isdir(test_root):
        print(f"{FAIL}: test_data/ 不存在，请先运行 generate_test_data.py")
        sys.exit(1)

    db_path = db.get_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
    db.init_db()

    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    wait_process_events(500)

    # ============================================================
    step("1. 添加扫描路径 + 重新扫描")
    # ============================================================
    scan_path = db.add_scan_path(test_root, "GUI 集成测试目录")
    slots = scanner.scan_path_for_saves(scan_path)
    check(f"扫描返回 {len(slots)} 个存档，期望 >= 50", len(slots) >= 50)
    mw.save_list.reload()
    wait_process_events(300)
    row_count = mw.save_list._model.rowCount()
    check(f"列表模型加载完成，行数 = {row_count}", row_count == len(slots))

    # ============================================================
    step("2. 单选预览 - 点击第 0 行，验证中间为预览面板")
    # ============================================================
    idx0 = mw.save_list._model.index(0, 0)
    mw.save_list.list_view.setCurrentIndex(idx0)
    mw.save_list.list_view.clicked.emit(idx0)
    wait_process_events(200)

    check("当前中间面板是 PreviewPanel（单选默认视图）",
          mw.center_stack.currentWidget() is mw.preview_panel)

    slot0: SaveSlot = idx0.data(Qt.ItemDataRole.UserRole)
    check(f"PreviewPanel 的 slot 已设置（game_name={slot0.game_name}）",
          mw.preview_panel._current_slot is not None and
          mw.preview_panel._current_slot.game_name == slot0.game_name)
    check("ActionPanel 的 slot 已同步",
          mw.action_panel._current_slot is not None and
          mw.action_panel._current_slot.id == slot0.id)

    # ============================================================
    step("3. 预览内容验证 - 解析字段显示 + 原始文本兜底")
    # ============================================================
    pp: PreviewPanel = mw.preview_panel
    parsed_ok = False
    if hasattr(pp, "_parsed") and pp._parsed is not None:
        parsed_ok = pp._parsed.character_name is not None or pp._parsed.level is not None
    # 退一步检查 preview_lines 是否有内容
    lines_ok = False
    if hasattr(pp, "_parsed") and pp._parsed is not None:
        lines_ok = len(pp._parsed.preview_lines) > 0
    check(f"预览解析内容非空（character_name/level 或 preview_lines）",
          parsed_ok or lines_ok)

    # ============================================================
    step("4. Ctrl 多选 - 选中第 0 行和第 1 行")
    # ============================================================
    idx1 = mw.save_list._model.index(1, 0)
    mw.save_list.list_view.clearSelection()
    mw.save_list.list_view.setCurrentIndex(idx0)
    mw.save_list.list_view.selectionModel().select(
        idx0, mw.save_list.list_view.selectionModel().SelectionFlag.Select
    )
    wait_process_events(50)
    mw.save_list.list_view.selectionModel().select(
        idx1, mw.save_list.list_view.selectionModel().SelectionFlag.Select
    )
    wait_process_events(200)

    selected = mw.save_list.selected_slots()
    check(f"选中数量 = {len(selected)}（期望 2）", len(selected) == 2)
    btn_text = mw.save_list.btn_compare.text()
    check(f"对比按钮文字变为 '{btn_text}'（包含 '(2)'）", "(2)" in btn_text)

    # ============================================================
    step("5. 点击「对比选中」按钮 - 验证切到对比视图")
    # ============================================================
    auto_close_dialog_after(300, "ok")
    mw.save_list.btn_compare.click()
    wait_process_events(800)

    check("点击后切换到 ComparePanel（中间 QStackedWidget）",
          isinstance(mw.center_stack.currentWidget(), ComparePanel))

    cp: ComparePanel = mw.compare_panel
    check("ComparePanel 已持有 CompareResult（非 None）",
          cp.result is not None)
    check(f"CompareResult 字段数 = {len(cp.result.field_diffs)}（期望 >= 4）",
          len(cp.result.field_diffs) >= 4)
    check(f"CompareResult 文本行级 diff 数 = {len(cp.result.line_diffs)}（期望 > 0）",
          len(cp.result.line_diffs) > 0)

    # ============================================================
    step("6. 字段对比 Tab - 验证表格内容和差异高亮样式")
    # ============================================================
    fcp: FieldComparePanel = cp.field_panel
    check("字段对比 Tab 表格行数 >= 4（标准 4 字段）",
          fcp.table.rowCount() >= 4)
    first_label = fcp.table.item(0, 0).text() if fcp.table.item(0, 0) else ""
    check(f"第 0 行字段名是 '{first_label}'（角色名）",
          first_label in ("角色名", "character_name"))

    # 找一行为 is_different=True 的，检查样式
    any_diff_row = -1
    for row in range(len(cp.result.field_diffs)):
        if cp.result.field_diffs[row].is_different:
            any_diff_row = row
            break
    if any_diff_row >= 0:
        a_item = fcp.table.item(any_diff_row, 1)
        bg_color: QColor = a_item.background().color() if a_item.background() else QColor()
        fg_color: QColor = a_item.foreground().color() if a_item.foreground() else QColor()
        hex_bg = bg_color.name().lower()
        hex_fg = fg_color.name().lower()
        check(f"差异行（第 {any_diff_row} 行）背景色 = {hex_bg}（期望 #ffebee）",
              hex_bg == "#ffebee")
        check(f"差异行（第 {any_diff_row} 行）前景色 = {hex_fg}（期望 #c62828）",
              hex_fg == "#c62828")
        check(f"差异行字体加粗", a_item.font().bold())
    else:
        check(f"没找到差异行（字段全部相同），跳过样式检查", True)

    diff_summary = fcp.summary_label.text()
    check(f"字段差异统计 label 有内容: '{diff_summary[:40]}...'",
          len(diff_summary) > 0)

    # ============================================================
    step("7. 切换到文本 Diff Tab - 验证表格填充")
    # ============================================================
    cp.tabs.setCurrentIndex(1)  # 文本 Diff Tab
    wait_process_events(100)
    tdp: TextDiffPanel = cp.text_panel
    check(f"文本 Diff 表格行数 = {tdp.table.rowCount()}（期望 > 0）",
          tdp.table.rowCount() > 0)
    check("文本 Diff 4 列（行号A/行号B/变更/内容）",
          tdp.table.columnCount() == 4)

    # 检查至少有一行是 add 或 delete 带颜色
    has_colored = False
    for r in range(min(tdp.table.rowCount(), 30)):
        content_item = tdp.table.item(r, 3)
        if content_item and content_item.background().color().isValid():
            cname = content_item.background().color().name().lower()
            if cname in ("#e8f5e9", "#ffebee", "#fff8e1"):
                has_colored = True
                break
    check("文本 Diff 有行带增/删颜色（绿/红/黄）", has_colored)

    # ============================================================
    step("8. 点击「← 返回预览」- 切回单选预览模式")
    # ============================================================
    cp.tabs.setCurrentIndex(0)  # 回到字段 Tab 方便点返回按钮
    wait_process_events(50)
    cp.btn_back.click()
    wait_process_events(200)

    check("返回后中间面板切回 PreviewPanel",
          mw.center_stack.currentWidget() is mw.preview_panel)
    check("ComparePanel 的 result 已被 clear（为空）",
          cp.result is None)
    check("PreviewPanel 当前 slot 非空（恢复为当前选中）",
          mw.preview_panel._current_slot is not None)

    # ============================================================
    step("9. 单选不同存档 - 预览跟随切换（回归测试）")
    # ============================================================
    idx5 = mw.save_list._model.index(5, 0)
    mw.save_list.list_view.clearSelection()
    mw.save_list.list_view.setCurrentIndex(idx5)
    mw.save_list.list_view.clicked.emit(idx5)
    wait_process_events(250)
    check("切换选中后仍在 PreviewPanel 视图",
          mw.center_stack.currentWidget() is mw.preview_panel)
    slot5: SaveSlot = idx5.data(Qt.ItemDataRole.UserRole)
    check(f"PreviewPanel 跟随切换到第 5 行（{slot5.game_name}）",
          mw.preview_panel._current_slot is not None and
          mw.preview_panel._current_slot.path == slot5.path)

    # ============================================================
    step("10. 创建备份 → 备份列表刷新（回归测试）")
    # ============================================================
    # 当前选中是 slot5，直接调用 action_panel 的备份
    auto_close_dialog_after(300, "ok")  # QInputDialog 点 OK 为空备注
    mw.action_panel._on_backup()
    wait_process_events(500)

    backups_list_count = mw.action_panel.backup_list.count()
    check(f"备份历史列表刷新后有 {backups_list_count} 条（期望 >= 1）",
          backups_list_count >= 1)

    # 选中第一个备份项
    for i in range(backups_list_count):
        item = mw.action_panel.backup_list.item(i)
        if item.data(Qt.ItemDataRole.UserRole) is not None:
            mw.action_panel.backup_list.setCurrentRow(i)
            break
    wait_process_events(150)
    check("选中备份后「与当前对比」按钮已启用",
          mw.action_panel.btn_compare_backup.isEnabled())
    check("选中备份后「还原」按钮已启用",
          mw.action_panel.btn_restore.isEnabled())

    # ============================================================
    step("11. 备份与当前对比 - 点击「与当前对比」")
    # ============================================================
    auto_close_dialog_after(300, "ok")
    mw.action_panel.btn_compare_backup.click()
    wait_process_events(800)

    check("点击后切到 ComparePanel（备份 vs 当前）",
          isinstance(mw.center_stack.currentWidget(), ComparePanel))
    res = cp.result
    check(f"备份对比有结果，字段差异 {res.field_diff_count} / 文本差异 {res.line_diff_count}",
          res is not None and len(res.field_diffs) >= 4)

    # 检查两个来源标签 - 一个是 [当前] 一个是 [备份]
    lbl_a_text = cp.field_panel.lbl_a.text()
    lbl_b_text = cp.field_panel.lbl_b.text()
    both_sides_ok = ("[当前]" in lbl_a_text or "[当前]" in lbl_b_text) and \
                    ("[备份]" in lbl_a_text or "[备份]" in lbl_b_text)
    check(f"两个来源分别带 [当前] 和 [备份] 标签", both_sides_ok)

    # 再测试返回按钮
    cp.btn_back.click()
    wait_process_events(200)
    check("返回后切回 PreviewPanel",
          mw.center_stack.currentWidget() is mw.preview_panel)

    # ============================================================
    step("12. 备份还原完整链路 - 修改→备份→修改→还原（回归测试）")
    # ============================================================
    # 选中一个 JSON 存档以便读写
    json_idx = None
    for row in range(mw.save_list._model.rowCount()):
        s: SaveSlot = mw.save_list._model.index(row, 0).data(Qt.ItemDataRole.UserRole)
        if s.path.endswith(".json"):
            json_idx = mw.save_list._model.index(row, 0)
            break

    if json_idx is not None:
        mw.save_list.list_view.clearSelection()
        mw.save_list.list_view.setCurrentIndex(json_idx)
        wait_process_events(150)
        js: SaveSlot = json_idx.data(Qt.ItemDataRole.UserRole)

        with open(js.path, "r", encoding="utf-8") as f:
            original = f.read()
        check(f"选中 JSON 存档用于还原测试: {os.path.basename(js.path)}",
              len(original) > 0)

        # 创建还原基准备份
        auto_close_dialog_after(300, "ok")
        mw.action_panel._on_backup()
        wait_process_events(400)

        # 修改文件
        modified = original + "\n// RESTORE_INTEGRATION_TEST_MARKER"
        with open(js.path, "w", encoding="utf-8") as f:
            f.write(modified)
        with open(js.path, "r", encoding="utf-8") as f:
            current = f.read()
        check("存档已成功修改（准备还原）",
              "RESTORE_INTEGRATION_TEST_MARKER" in current)

        # 选中刚创建的备份（最新的在第一行非占位）
        for i in range(mw.action_panel.backup_list.count()):
            item = mw.action_panel.backup_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) is not None:
                mw.action_panel.backup_list.setCurrentRow(i)
                break

        # 确认还原
        auto_close_dialog_after(400, "yes")
        auto_close_dialog_after(800, "ok")  # 完成提示
        mw.action_panel._on_restore()
        wait_process_events(1200)

        with open(js.path, "r", encoding="utf-8") as f:
            restored = f.read()
        check("还原成功！文件内容与原始一致，标记已清除",
              restored == original and "RESTORE_INTEGRATION_TEST_MARKER" not in restored)
    else:
        check("未找到 JSON 存档，跳过还原链路测试", True)

    # ============================================================
    step("13. 对比边界：选中 1 个时点对比 → 弹提示（不崩溃）")
    # ============================================================
    mw.save_list.list_view.clearSelection()
    mw.save_list.list_view.setCurrentIndex(
        mw.save_list._model.index(0, 0)
    )
    wait_process_events(100)
    auto_close_dialog_after(300, "ok")
    mw.save_list.btn_compare.click()
    wait_process_events(400)
    check("只选 1 个点对比按钮后视图未切换（仍在 PreviewPanel），无崩溃",
          mw.center_stack.currentWidget() is mw.preview_panel)

    # ============================================================
    step("14. 对比边界：选中 >2 个时点对比 → 弹提示（不崩溃）")
    # ============================================================
    mw.save_list.list_view.clearSelection()
    for r in range(min(3, mw.save_list._model.rowCount())):
        idx = mw.save_list._model.index(r, 0)
        mw.save_list.list_view.selectionModel().select(
            idx, mw.save_list.list_view.selectionModel().SelectionFlag.Select
        )
    wait_process_events(100)
    auto_close_dialog_after(300, "ok")
    mw.save_list.btn_compare.click()
    wait_process_events(400)
    check("选 3 个点对比按钮后视图未切换，无崩溃",
          mw.center_stack.currentWidget() is mw.preview_panel)

    # 清理选择
    mw.save_list.clear_selection()
    wait_process_events(100)

    # ============================================================
    # 总结
    # ============================================================
    print(f"\n{'='*70}")
    print(f"*** GUI 集成测试结束：{passed_count} PASS / {failed_count} FAIL ***")
    print(f"{'='*70}")

    total = passed_count + failed_count
    if total > 0:
        rate = passed_count / total * 100
        print(f"通过率: {rate:.1f}% ({passed_count}/{total})")

    mw.close()
    wait_process_events(200)

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
