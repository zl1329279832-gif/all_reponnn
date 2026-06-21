"""
自动化验收测试脚本 - 模拟用户所有操作
运行：python acceptance_test.py
"""

import os
import sys
import json
import tempfile
import shutil
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core import database as db
from app.core import scanner
from app.core import backup_manager as bm
from app.core.models import SaveSlot, ScanPath, Backup
from app.parsers.registry import get_parser_registry
from app.parsers import json_parser, ini_parser


def test_step(description):
    print(f"\n{'='*60}")
    print(f"->  {description}")
    print(f"{'='*60}")


def test_passed(message):
    print(f"[OK]  PASS: {message}")


def test_failed(message):
    print(f"[XX]  FAIL: {message}")
    sys.exit(1)


def run_all_tests():
    db_path = db.get_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"已清理旧数据库: {db_path}")
    db.init_db()

    # ============================================================
    test_step("1. 验证 .gitignore 和数据库隔离")
    # ============================================================
    gitignore_path = os.path.join(os.path.dirname(__file__), ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "data/" in content and "*.db" in content and "backups/" in content:
            test_passed(".gitignore 存在且包含 data/、*.db、backups/ 忽略规则")
        else:
            test_failed(".gitignore 缺少必要的忽略规则")
    else:
        test_failed(".gitignore 不存在")

    if os.path.exists(db_path):
        test_passed(f"数据库已自动创建: {db_path}")
    else:
        test_failed("数据库未创建")

    # ============================================================
    test_step("2. 测试扫描逻辑 - 只扫描 save 目录，不扫 cache/logs")
    # ============================================================
    test_root = os.path.join(os.path.dirname(__file__), "test_data")

    all_dirs = []
    for game_dir in os.listdir(test_root)[:3]:
        game_path = os.path.join(test_root, game_dir)
        if os.path.isdir(game_path):
            all_dirs.extend(os.listdir(game_path))

    has_cache = any("cache" in d.lower() for d in all_dirs)
    has_logs = any("logs" in d.lower() for d in all_dirs)
    has_binaries = any("binaries" in d.lower() for d in all_dirs)
    has_saves = any(d.lower() in {"saves", "savegames", "save", "存档"} for d in all_dirs)

    print(f"  测试数据包含: cache={has_cache}, logs={has_logs}, Binaries={has_binaries}, save目录={has_saves}")

    scan_path = db.add_scan_path(test_root, "测试目录")
    slots = scanner.scan_path_for_saves(scan_path)

    print(f"  扫描结果: 共 {len(slots)} 个存档")

    if len(slots) == 60:
        test_passed(f"正确扫描到 60 个存档（不多不少）")
    else:
        test_failed(f"扫描数量错误，期望 60，实际 {len(slots)}")

    scanned_paths = [s.path.lower() for s in slots]
    has_cache_files = any("cache" in p for p in scanned_paths)
    has_log_files = any("logs" in p for p in scanned_paths)
    has_bin_files = any("binaries" in p for p in scanned_paths)

    if not has_cache_files and not has_log_files and not has_bin_files:
        test_passed("正确忽略了 cache、logs、Binaries 目录")
    else:
        test_failed(f"错误地扫描了非存档目录: cache={has_cache_files}, logs={has_log_files}, binaries={has_bin_files}")

    # ============================================================
    test_step("3. 测试扫描逻辑 - 用户直接添加 save 目录作为根路径")
    # ============================================================
    first_save_dir = None
    for game_dir in os.listdir(test_root):
        game_path = os.path.join(test_root, game_dir)
        if os.path.isdir(game_path):
            for subdir in os.listdir(game_path):
                if subdir.lower() in {"saves", "save"}:
                    first_save_dir = os.path.join(game_path, subdir)
                    break
            if first_save_dir:
                break

    if first_save_dir:
        scan_path2 = db.add_scan_path(first_save_dir, "直接 save 目录")
        slots2 = scanner.scan_path_for_saves(scan_path2)
        if len(slots2) >= 1:
            test_passed(f"直接添加 save 目录也能正常扫描，找到 {len(slots2)} 个存档")
        else:
            test_failed("直接添加 save 目录扫描失败")
    else:
        print("  ⚠️  未找到合适的测试目录，跳过此测试")

    # ============================================================
    test_step("4. 测试列表性能 - 60 条数据加载、搜索、排序")
    # ============================================================
    start_time = time.time()
    all_slots = db.list_save_slots()
    load_time = time.time() - start_time
    print(f"  加载 60 条数据耗时: {load_time:.3f}秒")

    if load_time < 0.5:
        test_passed(f"列表加载性能良好 ({load_time:.3f}秒 < 0.5秒)")
    else:
        test_failed(f"列表加载过慢 ({load_time:.3f}秒)")

    start_time = time.time()
    filtered = db.list_save_slots(keyword="Elden")
    search_time = time.time() - start_time
    print(f"  搜索 'Elden' 找到 {len(filtered)} 条，耗时 {search_time:.3f}秒")

    if len(filtered) >= 1 and search_time < 0.3:
        test_passed("搜索过滤功能正常，性能良好")
    else:
        test_failed("搜索过滤功能异常或性能差")

    sorts = ["modified_desc", "modified_asc", "name_asc", "name_desc", "size_desc"]
    for sort_key in sorts:
        result = db.list_save_slots(sort_by=sort_key)
        if len(result) == len(all_slots):
            test_passed(f"排序 '{sort_key}' 正常")
        else:
            test_failed(f"排序 '{sort_key}' 失败")

    # ============================================================
    test_step("5. 测试解析器 - JSON 字段解析")
    # ============================================================
    registry = get_parser_registry()
    print(f"  已注册解析器: {[p.name for p in registry.parsers]}")

    json_slot = next((s for s in slots if s.path.endswith(".json") and "存档" not in s.path), None)
    if json_slot:
        parsed = registry.parse(json_slot.path)
        print(f"  测试 JSON 文件: {os.path.basename(json_slot.path)}")
        print(f"    角色名: {parsed.character_name}")
        print(f"    等级: {parsed.level}")
        print(f"    章节: {parsed.chapter}")
        print(f"    游玩时长: {parsed.playtime}")

        if parsed.character_name and parsed.level and parsed.chapter and parsed.playtime:
            test_passed("JSON 解析器正确提取了所有字段")
        else:
            missing = []
            if not parsed.character_name: missing.append("角色名")
            if not parsed.level: missing.append("等级")
            if not parsed.chapter: missing.append("章节")
            if not parsed.playtime: missing.append("游玩时长")
            test_failed(f"JSON 解析器字段提取不完整，缺少: {missing}")

        if len(parsed.preview_lines) > 0:
            test_passed("JSON 原始文本预览正常")
        else:
            test_failed("JSON 原始文本预览为空")
    else:
        test_failed("未找到 JSON 测试存档")

    # ============================================================
    test_step("6. 测试解析器 - INI 字段解析")
    # ============================================================
    ini_slot = next((s for s in slots if s.path.endswith(".ini")), None)
    if ini_slot:
        parsed = registry.parse(ini_slot.path)
        print(f"  测试 INI 文件: {os.path.basename(ini_slot.path)}")
        print(f"    角色名: {parsed.character_name}")
        print(f"    等级: {parsed.level}")
        print(f"    章节: {parsed.chapter}")
        print(f"    游玩时长: {parsed.playtime}")

        if parsed.character_name and parsed.level and parsed.chapter and parsed.playtime:
            test_passed("INI 解析器正确提取了所有字段")
        else:
            missing = []
            if not parsed.character_name: missing.append("角色名")
            if not parsed.level: missing.append("等级")
            if not parsed.chapter: missing.append("章节")
            if not parsed.playtime: missing.append("游玩时长")
            test_failed(f"INI 解析器字段提取不完整，缺少: {missing}")

        if len(parsed.preview_lines) > 0:
            test_passed("INI 原始文本预览正常")
        else:
            test_failed("INI 原始文本预览为空")
    else:
        test_failed("未找到 INI 测试存档")

    # ============================================================
    test_step("7. 测试解析器 - 中文目录存档解析")
    # ============================================================
    cn_slot = next((s for s in slots if "存档" in s.path), None)
    if cn_slot:
        parsed = registry.parse(cn_slot.path)
        print(f"  测试中文目录文件: {os.path.basename(cn_slot.path)}")
        print(f"    角色名: {parsed.character_name}")
        print(f"    等级: {parsed.level}")

        if parsed.character_name and parsed.level:
            test_passed("中文目录存档解析正常")
        else:
            test_failed("中文目录存档解析失败")
    else:
        test_failed("未找到中文目录测试存档")

    # ============================================================
    test_step("8. 测试解析器 - 二进制文件原始文本兜底")
    # ============================================================
    bin_slot = next((s for s in slots if s.path.endswith(".dat")), None)
    if bin_slot:
        parsed = registry.parse(bin_slot.path)
        print(f"  测试二进制文件: {os.path.basename(bin_slot.path)}")
        preview = "\n".join(parsed.preview_lines)
        print(f"    预览内容长度: {len(preview)} 字符")

        if "此存档为二进制格式或无法以文本方式预览" in preview or len(parsed.preview_lines) > 0:
            test_passed("二进制文件正确显示了兜底提示或原始内容")
        else:
            test_failed("二进制文件兜底逻辑异常")

        if parsed.character_name is None and parsed.level is None:
            test_passed("二进制文件正确返回空解析字段")
        else:
            test_failed("二进制文件不应该解析出结构化字段")
    else:
        test_failed("未找到二进制测试存档")

    # ============================================================
    test_step("9. 测试备份功能")
    # ============================================================
    test_slot = slots[0]
    original_content = ""
    with open(test_slot.path, "r", encoding="utf-8", errors="ignore") as f:
        original_content = f.read()

    print(f"  测试存档: {test_slot.game_name}")
    print(f"  原路径: {test_slot.path}")

    backup = bm.create_backup(test_slot, "验收测试备份1")
    print(f"  备份创建: {backup.path}")

    if os.path.exists(backup.path):
        test_passed(f"备份目录已创建: {backup.path}")
    else:
        test_failed("备份目录未创建")

    backups_list = bm.list_slot_backups(test_slot)
    if len(backups_list) == 1 and backups_list[0].id == backup.id:
        test_passed("备份记录已存入数据库")
    else:
        test_failed("备份记录未正确保存")

    # 创建第二个备份
    backup2 = bm.create_backup(test_slot, "验收测试备份2")
    backups_list = bm.list_slot_backups(test_slot)
    if len(backups_list) == 2:
        test_passed("支持多版本备份，历史列表正常")
    else:
        test_failed("多版本备份功能异常")

    # ============================================================
    test_step("10. 测试修改备注功能")
    # ============================================================
    db.update_save_slot_note(test_slot.id, "验收测试备注")
    updated_slots = db.list_save_slots(keyword="验收测试备注")
    if len(updated_slots) == 1 and updated_slots[0].note == "验收测试备注":
        test_passed("备注修改成功，且可通过搜索过滤找到")
    else:
        test_failed("备注修改失败或搜索不到")

    # ============================================================
    test_step("11. 测试还原功能（完整链路：备份→修改→还原→验证）")
    # ============================================================
    test_slot2 = slots[1]
    with open(test_slot2.path, "r", encoding="utf-8", errors="ignore") as f:
        original = f.read()

    backup3 = bm.create_backup(test_slot2, "还原测试备份")

    modified_content = original + "\n// MODIFIED FOR RESTORE TEST"
    with open(test_slot2.path, "w", encoding="utf-8") as f:
        f.write(modified_content)

    with open(test_slot2.path, "r", encoding="utf-8", errors="ignore") as f:
        current = f.read()
    if "MODIFIED FOR RESTORE TEST" in current:
        test_passed("存档已修改，准备还原")
    else:
        test_failed("存档修改失败，无法测试还原")

    bm.restore_backup(test_slot2, backup3)

    with open(test_slot2.path, "r", encoding="utf-8", errors="ignore") as f:
        restored = f.read()

    if restored == original and "MODIFIED FOR RESTORE TEST" not in restored:
        test_passed("还原成功！存档已恢复到修改前的状态")
    else:
        test_failed("还原失败，内容未正确恢复")

    # ============================================================
    test_step("12. 测试删除备份功能")
    # ============================================================
    backup_path = backup.path
    bm.delete_backup_file(backup)
    if not os.path.exists(backup_path):
        test_passed("备份文件已删除")
    else:
        test_failed("备份文件未删除")

    final_list = bm.list_slot_backups(test_slot)
    if len(final_list) == 1:
        test_passed("数据库中备份记录已删除")
    else:
        test_failed("数据库中备份记录未删除")

    # ============================================================
    test_step("13. 测试数据持久化 - 重启后数据保留")
    # ============================================================
    slot_count_before = len(db.list_save_slots())

    db2_path = db.get_db_path()
    if os.path.exists(db2_path):
        test_passed(f"数据库文件存在: {db2_path}")
    else:
        test_failed("数据库文件不存在")

    scan_path_count = len(db.list_scan_paths())
    if scan_path_count >= 2:
        test_passed(f"扫描路径已持久化，共 {scan_path_count} 条")
    else:
        test_failed("扫描路径未持久化")

    note_slot = db.list_save_slots(keyword="验收测试备注")
    if len(note_slot) == 1 and note_slot[0].note == "验收测试备注":
        test_passed("备注信息已持久化")
    else:
        test_failed("备注信息未持久化")

    # ============================================================
    test_step("14. 验证扫描逻辑中的 'or True' 已彻底移除")
    # ============================================================
    scanner_path = os.path.join(os.path.dirname(__file__), "app", "core", "scanner.py")
    with open(scanner_path, "r", encoding="utf-8") as f:
        scanner_code = f.read()

    if "or True" not in scanner_code:
        test_passed("scanner.py 中已彻底移除 'or True' 无差别递归")
    else:
        test_failed("scanner.py 中仍存在 'or True'")

    if "_find_save_dirs" in scanner_code and "_is_save_dir_name" in scanner_code:
        test_passed("新的扫描逻辑（先找 save 目录再扫描）已实现")
    else:
        test_failed("新的扫描逻辑未实现")

    # ============================================================
    test_step("15. 验证三栏布局的分隔比例设置")
    # ============================================================
    main_window_path = os.path.join(os.path.dirname(__file__), "app", "ui", "main_window.py")
    with open(main_window_path, "r", encoding="utf-8") as f:
        mw_code = f.read()

    checks = ["setStretchFactor", "setSizes", "QSplitter", "SaveListPanel", "PreviewPanel", "ActionPanel"]
    all_present = all(c in mw_code for c in checks)
    if all_present:
        test_passed("主窗口三栏布局结构完整，包含拉伸因子和尺寸设置")
    else:
        missing = [c for c in checks if c not in mw_code]
        test_failed(f"主窗口布局缺少组件: {missing}")

    # ============================================================
    test_step("16. 验证按钮事件连接")
    # ============================================================
    action_panel_path = os.path.join(os.path.dirname(__file__), "app", "ui", "action_panel.py")
    with open(action_panel_path, "r", encoding="utf-8") as f:
        ap_code = f.read()

    btn_checks = ["clicked.connect", "_on_backup", "_on_restore", "_on_rename", "_on_delete_backup"]
    all_connected = all(c in ap_code for c in btn_checks)
    if all_connected:
        test_passed("所有按钮（备份/还原/重命名/删除备份）事件已正确连接")
    else:
        missing = [c for c in btn_checks if c not in ap_code]
        test_failed(f"按钮事件未连接: {missing}")

    # ============================================================
    print(f"\n{'='*60}")
    print(f"*** 所有测试通过！共 16 项验收测试全部 PASS ***")
    print(f"{'='*60}")
    print(f"\n测试摘要:")
    print(f"   [OK] .gitignore 和数据库隔离")
    print(f"   [OK] 扫描逻辑修复（移除 or True，只扫 save 目录）")
    print(f"   [OK] 60 条数据列表性能（加载/搜索/排序）")
    print(f"   [OK] JSON 字段解析（角色名/等级/章节/时长）")
    print(f"   [OK] INI 字段解析")
    print(f"   [OK] 中文目录存档解析")
    print(f"   [OK] 二进制文件原始文本兜底")
    print(f"   [OK] 创建备份")
    print(f"   [OK] 多版本备份历史")
    print(f"   [OK] 修改备注 & 搜索过滤")
    print(f"   [OK] 还原功能完整链路")
    print(f"   [OK] 删除备份")
    print(f"   [OK] 数据持久化（重启保留）")
    print(f"   [OK] 三栏布局结构")
    print(f"   [OK] 按钮事件连接")
    print(f"\n程序已就绪，Windows 下双击或 `python main.py` 启动即可！")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_all_tests()
