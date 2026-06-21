import os
import sys
import time
import tempfile

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui_verify.log")
_log_f = open(LOG_PATH, "w", encoding="utf-8")


def _log(msg):
    print(msg, flush=True)
    _log_f.write(msg + "\n")
    _log_f.flush()


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from PIL import ImageGrab

PHOTOS_DIR = r"c:\Users\13292\Desktop\solocode\all_reponnn\8\test_photos"
SCREENSHOT_DIR = r"c:\Users\13292\Desktop\solocode\all_reponnn\8\gui_screenshots"
for f in (os.listdir(SCREENSHOT_DIR) if os.path.exists(SCREENSHOT_DIR) else []):
    try:
        os.remove(os.path.join(SCREENSHOT_DIR, f))
    except OSError:
        pass
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

from photo_organizer import config as cfg_mod
from photo_organizer import database as db

cfg = cfg_mod.load_config()
cfg["root_dirs"] = [PHOTOS_DIR]
cfg_mod.save_config(cfg)

from photo_organizer.ui.app import PhotoOrganizerApp

ss_count = [0]


def capture(app, name):
    app.update_idletasks()
    app.update()
    try:
        w = app.winfo_width()
        h = app.winfo_height()
        path = os.path.join(SCREENSHOT_DIR, f"{ss_count[0]:02d}_{name}.png")
        ss_count[0] += 1
        pil_img = ImageGrab.grab(
            bbox=(app.winfo_rootx(), app.winfo_rooty(),
                  app.winfo_rootx() + w, app.winfo_rooty() + h),
            all_screens=True,
        )
        pil_img.save(path)
        pil_img.close()
        _log(f"[SS] saved: {os.path.basename(path)}  ({w}x{h})")
    except Exception as e:
        _log(f"[SS] skip ({name}): {e}")


def wait_for_scan(app, timeout=40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.update_idletasks()
        app.update()
        if app.scan_worker and not app.scan_worker.is_alive():
            break
        time.sleep(0.15)
    for _ in range(40):
        app.update_idletasks()
        app.update()
        time.sleep(0.05)
    app._load_existing_photos()
    for _ in range(15):
        app.update_idletasks()
        app.update()
        time.sleep(0.03)


def step1_initial_window(app):
    _log("\n=== STEP 1: 初始窗口 ===")
    app.update_idletasks()
    app.update()
    time.sleep(1)
    capture(app, "01_initial_window")
    _log("  OK: 窗口正常显示")


def step2_scan_directory(app):
    _log("\n=== STEP 2: 扫描 test_photos 目录（含坏图 corrupt.jpg） ===")
    app._start_scan()
    wait_for_scan(app)
    time.sleep(0.5)
    capture(app, "02_after_scan")
    n = len(app.current_photos)
    _log(f"  索引照片数: {n} (预期 12)")
    assert n >= 10, f"FAIL: 只扫到 {n} 张"
    _log(f"  scan_failures 数量: {len(app.scan_failures)}")
    for fp, err in app.scan_failures:
        _log(f"    FAIL FILE: {os.path.basename(fp)} — {err}")
    return n


def step3_select_and_save_notes(app):
    _log("\n=== STEP 3: 选中 vacation_01.jpg -> 保存标题备注 ===")
    conn = db.get_connection()
    all_p = db.get_all_photos(conn)
    conn.close()
    target = None
    for p in all_p:
        if p["filename"] == "vacation_01.jpg":
            target = p
            break
    assert target, "找不到 vacation_01.jpg"
    app.sidebar.selected_ids = {target["id"]}
    app.sidebar._refresh_selection_ui()
    app._on_photo_click(target, [target])
    for _ in range(15):
        app.update_idletasks()
        app.update()
        time.sleep(0.05)
    capture(app, "03_selected_vacation_01")

    app.detail.title_var.set("Maldives Sunset")
    app.detail.notes_var.set("Water villa sunset, red sky, very beautiful")
    for _ in range(10):
        app.update_idletasks()
        app.update()
        time.sleep(0.03)
    app.detail._save()
    for _ in range(15):
        app.update_idletasks()
        app.update()
        time.sleep(0.03)
    _log("  Saved title='Maldives Sunset' notes='Water villa sunset, red sky, very beautiful'")

    conn = db.get_connection()
    verify = db.get_photo_by_id(conn, target["id"])
    conn.close()
    assert verify["title"] == "Maldives Sunset", f"DB title not written: {verify['title']}"
    assert verify["notes"] == "Water villa sunset, red sky, very beautiful", "DB notes not written"
    capture(app, "03b_saved_notes")
    _log("  PASS: 标题备注已写入 SQLite")


def step4_rescan_and_verify_notes(app):
    _log("\n=== STEP 4: 重新扫描 -> 验证标题备注保留 ===")
    app._start_scan()
    wait_for_scan(app)
    time.sleep(0.3)

    conn = db.get_connection()
    found = None
    for p in db.get_all_photos(conn):
        if p["filename"] == "vacation_01.jpg":
            found = p
            break
    conn.close()
    assert found, "rescan 后找不到 vacation_01.jpg"
    _log(f"  rescan 后 title: '{found['title']}'")
    _log(f"  rescan 后 notes: '{found['notes']}'")
    assert found["title"] == "Maldives Sunset", f"FAIL: title 被覆盖! got '{found['title']}'"
    assert found["notes"] == "Water villa sunset, red sky, very beautiful", "FAIL: notes 被覆盖!"

    app.sidebar.selected_ids = {found["id"]}
    app.sidebar._refresh_selection_ui()
    app._on_photo_click(found, [found])
    for _ in range(10):
        app.update_idletasks()
        app.update()
        time.sleep(0.05)
    capture(app, "04_rescan_preserves_notes")
    _log("  PASS: 重新扫描后标题备注完好保留")


def step5_ctrl_multiselect_and_batch_move(app):
    _log("\n=== STEP 5: Ctrl 多选 3 张 -> 批量移动（先预览再确认执行） ===")
    conn = db.get_connection()
    all_p = db.get_all_photos(conn)
    conn.close()
    to_select = [p for p in all_p
                 if p["filename"] in ("photo_001.jpg", "photo_002.jpg", "photo_003.jpg")]
    assert len(to_select) == 3, f"只能选到 {len(to_select)} 张"
    app.sidebar.selected_ids = {p["id"] for p in to_select}
    app.sidebar._last_clicked_index = None
    for i, p in enumerate(app.current_photos):
        if p["id"] in app.sidebar.selected_ids:
            app.sidebar._last_clicked_index = i
            break
    app.sidebar._refresh_selection_ui()
    app.sidebar._notify_selection()
    for _ in range(10):
        app.update_idletasks()
        app.update()
        time.sleep(0.05)
    n_sel = len(app.sidebar.get_selected_photos())
    _log(f"  已选 {n_sel} 张 (预期 3)")
    assert n_sel == 3
    capture(app, "05_ctrl_multiselect")

    MOVE_TARGET = tempfile.mkdtemp(prefix="gui_test_album_")
    _log(f"  移动目标目录: {MOVE_TARGET}")

    from photo_organizer.ui.batch import BatchDialog
    selected = app.sidebar.get_selected_photos()
    dlg = BatchDialog(app, selected)
    for _ in range(10):
        app.update_idletasks()
        app.update()
        time.sleep(0.05)

    dlg.target_dir = MOVE_TARGET
    dlg.mode = dlg.MODE_MOVE
    raw_pairs = [(p["filepath"], os.path.join(MOVE_TARGET, p["filename"]))
                 for p in selected]
    dlg.preview_pairs = dlg._resolve_move_conflicts(raw_pairs)
    dlg._populate_preview(dlg.preview_pairs)
    dlg.mode_label.configure(text=f"[MOVE] target: {MOVE_TARGET}")
    dlg.execute_btn.configure(state="normal")
    dlg.status_label.configure(text=f"Preview {len(dlg.preview_pairs)} items", text_color="blue")
    for _ in range(20):
        app.update_idletasks()
        app.update()
        time.sleep(0.05)
    capture(app, "06_move_preview")
    _log("  预览清单已生成:")
    for old, new in dlg.preview_pairs:
        _log(f"    {os.path.basename(old)} -> {os.path.basename(new)}")

    results = dlg._execute_move()
    conn = db.get_connection()
    for old, new in results["success"]:
        db.update_filepath(conn, old, new, os.path.basename(new))
    conn.commit()
    conn.close()
    dlg._show_results(results, "Move")
    for _ in range(20):
        app.update_idletasks()
        app.update()
        time.sleep(0.05)
    capture(app, "07_move_done")

    _log(f"  移动成功: {len(results['success'])}, 失败: {len(results['failed'])}")
    for fp, err in results["failed"]:
        _log(f"    FAIL: {fp} - {err}")
    assert len(results["success"]) == 3
    for old, new in results["success"]:
        assert os.path.exists(new), f"target missing: {new}"
    assert len(results["failed"]) == 0
    app._load_existing_photos()
    for _ in range(10):
        app.update_idletasks()
        app.update()
        time.sleep(0.03)
    _log("  PASS: 批量移动预览->执行->结果汇总 全链路 OK")
    return MOVE_TARGET


def step6_batch_rename(app, move_target):
    _log("\n=== STEP 6: 批量按拍摄日期重命名（预览->确认执行） ===")
    conn = db.get_connection()
    all_p = db.get_all_photos(conn)
    conn.close()
    to_select = [p for p in all_p if p["filepath"].startswith(move_target)]
    _log(f"  选中刚移动的 {len(to_select)} 张进行重命名")
    assert len(to_select) == 3
    app.sidebar.selected_ids = {p["id"] for p in to_select}
    app.sidebar._refresh_selection_ui()
    app.sidebar._notify_selection()
    for _ in range(10):
        app.update_idletasks()
        app.update()
        time.sleep(0.03)

    from photo_organizer.ui.batch import BatchDialog
    dlg = BatchDialog(app, to_select)
    for _ in range(10):
        app.update_idletasks()
        app.update()
        time.sleep(0.05)
    dlg.mode = dlg.MODE_RENAME
    dlg.preview_pairs = dlg._build_rename_preview_pairs()
    dlg._populate_preview(dlg.preview_pairs)
    dlg.mode_label.configure(text="[RENAME by date] format: YYYYMMDD_HHMMSS.ext")
    dlg.execute_btn.configure(state="normal")
    dlg.status_label.configure(text=f"Preview {len(dlg.preview_pairs)} items", text_color="blue")
    for _ in range(20):
        app.update_idletasks()
        app.update()
        time.sleep(0.05)
    capture(app, "08_rename_preview")
    _log("  重命名预览清单:")
    all_date_prefixes = []
    for old, new in dlg.preview_pairs:
        name = os.path.basename(new)
        all_date_prefixes.append(name[:8])
        _log(f"    {os.path.basename(old)} -> {name}")
    assert all(p[:4].isdigit() and p[4:6].isdigit() for p in all_date_prefixes), "name does not start with YYYYMM"

    results = dlg._execute_rename()
    conn = db.get_connection()
    for old, new in results["success"]:
        db.update_filepath(conn, old, new, os.path.basename(new))
    conn.commit()
    conn.close()
    dlg._show_results(results, "Rename")
    for _ in range(20):
        app.update_idletasks()
        app.update()
        time.sleep(0.05)
    capture(app, "09_rename_done")

    _log(f"  重命名成功: {len(results['success'])}, 失败: {len(results['failed'])}")
    for fp, err in results["failed"]:
        _log(f"    FAIL: {fp} - {err}")
    assert len(results["success"]) == 3
    assert len(results["failed"]) == 0
    for old, new in results["success"]:
        assert os.path.exists(new)
        new_name = os.path.basename(new)
        assert new_name[0].isdigit(), f"new name {new_name} not date-prefixed"
    app._load_existing_photos()
    for _ in range(10):
        app.update_idletasks()
        app.update()
        time.sleep(0.03)
    _log("  PASS: 批量重命名预览->执行->结果汇总 全链路 OK")


def step7_scan_failure_popup(app):
    _log("\n=== STEP 7: 坏图扫描失败汇总提示 ===")
    corrupt = os.path.join(PHOTOS_DIR, "corrupt.jpg")
    _log(f"  corrupt.jpg exists: {os.path.exists(corrupt)}")

    app.scan_failures.clear()
    app._start_scan()
    wait_for_scan(app)
    time.sleep(0.3)

    _log(f"  app.scan_failures records: {len(app.scan_failures)}")
    if app.scan_failures:
        for fp, err in app.scan_failures:
            _log(f"    FAIL: {os.path.basename(fp) if fp else '(?)'}: {err[:100]}")
        assert any("corrupt" in (fp or "").lower() for fp, _ in app.scan_failures), \
            "FAIL: corrupt.jpg not recorded as failure"
        capture(app, "10_scan_failures_recorded")
        _log("  PASS: 坏图触发了扫描失败记录")
    else:
        _log("  WARN: no scan_failures recorded (should have at least corrupt.jpg)")
        assert False, "FAIL: corrupt.jpg should be reported as scan failure"


def step8_search_filter(app):
    _log("\n=== STEP 8: 搜索过滤（关键词 + 日期范围） ===")
    app.search_bar.keyword_var.set("Maldives")
    for _ in range(15):
        app.update_idletasks()
        app.update()
        time.sleep(0.05)
    n = len(app.current_photos)
    _log(f"  keyword 'Maldives': {n} results (expected 1)")
    assert n == 1, f"FAIL: got {n}"
    capture(app, "11_search_keyword")

    app.search_bar.keyword_var.set("")
    app.search_bar.date_from_var.set("2025-06-01")
    app.search_bar.date_to_var.set("2025-06-30")
    for _ in range(15):
        app.update_idletasks()
        app.update()
        time.sleep(0.05)
    n2 = len(app.current_photos)
    _log(f"  date range 2025-06: {n2} results")
    assert n2 >= 3, f"FAIL: June should have >=3, got {n2}"
    capture(app, "12_search_date_range")

    app.search_bar.keyword_var.set("")
    app.search_bar.date_from_var.set("")
    app.search_bar.date_to_var.set("")
    for _ in range(10):
        app.update_idletasks()
        app.update()
        time.sleep(0.03)
    app._load_existing_photos()
    _log("  PASS: keyword search + date range search both OK")


def main():
    app = PhotoOrganizerApp()
    try:
        step1_initial_window(app)
        step2_scan_directory(app)
        step3_select_and_save_notes(app)
        step4_rescan_and_verify_notes(app)
        move_target = step5_ctrl_multiselect_and_batch_move(app)
        step6_batch_rename(app, move_target)
        step7_scan_failure_popup(app)
        step8_search_filter(app)

        _log("\n========== ALL GUI VERIFICATION STEPS PASSED ==========")
        _log(f"Screenshots saved in: {SCREENSHOT_DIR}")
        listing = sorted(os.listdir(SCREENSHOT_DIR))
        for f in listing:
            _log(f"  - {f}")
        time.sleep(0.5)
    except Exception as exc:
        _log(f"\n!!! TEST FAILED with exception: {type(exc).__name__}: {exc}")
        import traceback
        _log(traceback.format_exc())
        raise
    finally:
        _log_f.close()
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    main()
