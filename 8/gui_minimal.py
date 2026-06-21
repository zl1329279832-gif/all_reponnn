import os
import sys
import time
import tempfile
import shutil

LOG = open("gui_minimal.log", "w", encoding="utf-8")
def L(msg):
    print(msg, flush=True)
    LOG.write(msg + "\n")
    LOG.flush()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from photo_organizer import config as cfg_mod
from photo_organizer import database as db

PHOTOS_DIR = r"c:\Users\13292\Desktop\solocode\all_reponnn\8\test_photos"
cfg = cfg_mod.load_config()
cfg["root_dirs"] = [PHOTOS_DIR]
cfg_mod.save_config(cfg)

import customtkinter as ctk
from photo_organizer.ui.app import PhotoOrganizerApp

def run_event(app, ticks=20):
    for _ in range(ticks):
        app.update_idletasks()
        app.update()
        time.sleep(0.03)

def wait_scan(app, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.update_idletasks()
        app.update()
        if app.scan_worker and not app.scan_worker.is_alive():
            break
        time.sleep(0.1)
    run_event(app, 60)

app = PhotoOrganizerApp()
try:
    L("[1] initial window created")
    run_event(app, 30)

    L("[2] starting scan (11 good + 1 corrupt)...")
    app._start_scan()
    wait_scan(app)
    app._load_existing_photos()
    run_event(app, 30)
    L(f"[3] scan done. photos loaded: {len(app.current_photos)}, failures: {len(app.scan_failures)}")
    for fp, err in app.scan_failures:
        L(f"      FAIL: {os.path.basename(fp)} -> {err[:100]}")
    assert len(app.current_photos) >= 10, f"expect >=10 photos, got {len(app.current_photos)}"
    assert any("corrupt" in (fp or "").lower() for fp, _ in app.scan_failures), "corrupt.jpg should be in scan_failures"

    conn = db.get_connection()
    all_p = db.get_all_photos(conn)
    target = next((p for p in all_p if p["filename"] == "vacation_01.jpg"), None)
    conn.close()
    assert target, "vacation_01.jpg not in DB"

    app.sidebar.selected_ids = {target["id"]}
    app.sidebar._refresh_selection_ui()
    app._on_photo_click(target, [target])
    run_event(app, 20)
    L("[4] selected vacation_01. setting title/notes='Maldives Sunset' / 'Water villa sunset red sky'")
    app.detail.title_var.set("Maldives Sunset")
    app.detail.notes_var.set("Water villa sunset red sky")
    run_event(app, 10)
    app.detail._save()
    run_event(app, 10)
    conn = db.get_connection()
    v = db.get_photo_by_id(conn, target["id"])
    conn.close()
    L(f"[5] DB: title='{v['title']}' notes='{v['notes']}'")
    assert v["title"] == "Maldives Sunset"
    assert v["notes"] == "Water villa sunset red sky"
    L("    PASS: title/notes saved")

    L("[6] rescan — expect title/notes preserved...")
    app.scan_failures.clear()
    app._start_scan()
    wait_scan(app)
    app._load_existing_photos()
    run_event(app, 20)
    conn = db.get_connection()
    v2 = next((p for p in db.get_all_photos(conn) if p["filename"] == "vacation_01.jpg"), None)
    conn.close()
    L(f"[7] after rescan: title='{v2['title']}' notes='{v2['notes']}'")
    assert v2["title"] == "Maldives Sunset", f"FAIL title lost: {v2['title']!r}"
    assert v2["notes"] == "Water villa sunset red sky", f"FAIL notes lost: {v2['notes']!r}"
    L("    PASS: title/notes preserved after rescan!")

    L("[8] search keyword='Maldives' -> 1 result")
    app.search_bar.keyword_var.set("Maldives")
    run_event(app, 15)
    L(f"    results: {len(app.current_photos)}")
    assert len(app.current_photos) == 1
    app.search_bar.keyword_var.set("")
    run_event(app, 5)

    L("[9] search date 2025-06-01..2025-06-30 -> at least 4 results")
    app.search_bar.date_from_var.set("2025-06-01")
    app.search_bar.date_to_var.set("2025-06-30")
    run_event(app, 15)
    L(f"    results: {len(app.current_photos)}")
    assert len(app.current_photos) >= 4
    app.search_bar.date_from_var.set("")
    app.search_bar.date_to_var.set("")
    run_event(app, 5)
    L("    PASS: search keyword + date range")

    L("[10] Ctrl multi-select photo_001/002/003 -> 3 selected")
    conn = db.get_connection()
    all_p = db.get_all_photos(conn)
    conn.close()
    to_select = [p for p in all_p if p["filename"] in ("photo_001.jpg", "photo_002.jpg", "photo_003.jpg")]
    assert len(to_select) == 3, f"should have 3, got {len(to_select)}"
    app.sidebar.selected_ids = {p["id"] for p in to_select}
    app.sidebar._refresh_selection_ui()
    app.sidebar._notify_selection()
    run_event(app, 15)
    selected = app.sidebar.get_selected_photos()
    L(f"    sidebar selection count: {len(selected)}")
    assert len(selected) == 3
    L("    PASS: multi-select 3")

    move_target = tempfile.mkdtemp(prefix="gui_album_")
    from photo_organizer.ui.batch import BatchDialog

    L(f"[11] batch move preview -> {move_target}")
    dlg = BatchDialog(app, selected)
    run_event(app, 10)
    dlg.mode = dlg.MODE_MOVE
    dlg.target_dir = move_target
    raw = [(p["filepath"], os.path.join(move_target, p["filename"])) for p in selected]
    dlg.preview_pairs = dlg._resolve_move_conflicts(raw)
    dlg._populate_preview(dlg.preview_pairs)
    dlg.execute_btn.configure(state="normal")
    run_event(app, 15)
    L(f"    preview {len(dlg.preview_pairs)} pairs")
    for old, new in dlg.preview_pairs:
        L(f"      {os.path.basename(old)} -> {os.path.basename(new)}")
    assert len(dlg.preview_pairs) == 3
    L("    PASS: move preview generated")

    results = dlg._execute_move()
    conn = db.get_connection()
    for old, new in results["success"]:
        db.update_filepath(conn, old, new, os.path.basename(new))
    conn.commit()
    conn.close()
    dlg._show_results(results, "Move")
    run_event(app, 20)
    L(f"[12] move executed: success={len(results['success'])}, failed={len(results['failed'])}")
    for old, new in results["success"]:
        L(f"      OK: {os.path.basename(new)} exists={os.path.exists(new)}")
    assert len(results["success"]) == 3
    assert len(results["failed"]) == 0
    for old, new in results["success"]:
        assert os.path.exists(new)
    L("    PASS: batch move executed")

    L("[13] batch rename by date (the 3 just moved)...")
    conn = db.get_connection()
    all_p = db.get_all_photos(conn)
    conn.close()
    to_select2 = [p for p in all_p if p["filepath"].startswith(move_target)]
    assert len(to_select2) == 3
    app.sidebar.selected_ids = {p["id"] for p in to_select2}
    app.sidebar._refresh_selection_ui()
    app.sidebar._notify_selection()
    dlg2 = BatchDialog(app, to_select2)
    run_event(app, 10)
    dlg2.mode = dlg2.MODE_RENAME
    dlg2.preview_pairs = dlg2._build_rename_preview_pairs()
    dlg2._populate_preview(dlg2.preview_pairs)
    dlg2.execute_btn.configure(state="normal")
    run_event(app, 15)
    L(f"    rename preview {len(dlg2.preview_pairs)} pairs")
    for old, new in dlg2.preview_pairs:
        L(f"      {os.path.basename(old)} -> {os.path.basename(new)}")
        bn = os.path.basename(new)
        assert bn[:8].isdigit() or bn.split("_")[0].isdigit(), f"not date-prefixed: {bn}"

    results2 = dlg2._execute_rename()
    conn = db.get_connection()
    for old, new in results2["success"]:
        db.update_filepath(conn, old, new, os.path.basename(new))
    conn.commit()
    conn.close()
    dlg2._show_results(results2, "Rename")
    run_event(app, 20)
    L(f"[14] rename executed: success={len(results2['success'])}, failed={len(results2['failed'])}")
    for old, new in results2["success"]:
        L(f"      OK: {os.path.basename(new)} exists={os.path.exists(new)}")
    assert len(results2["success"]) == 3
    assert len(results2["failed"]) == 0
    L("    PASS: batch rename executed")

    L("\n========== ALL GUI MINIMAL TESTS PASSED ==========")
except Exception as exc:
    L(f"\n!!! TEST FAILED: {type(exc).__name__}: {exc}")
    import traceback
    L(traceback.format_exc())
    raise
finally:
    LOG.close()
    try:
        app.destroy()
    except Exception:
        pass
