import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from .search import SearchBar
from .sidebar import Sidebar
from .detail import DetailPanel
from .progress import ProgressBar
from .batch import BatchDialog
from .. import config as config_mod
from .. import database as db
from ..scanner import ScanWorker


class PhotoOrganizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("照片整理工具")
        self.geometry("1280x800")
        self.minsize(960, 600)

        self.cfg = config_mod.load_config()
        if self.cfg.get("window_width"):
            self.geometry(
                f"{self.cfg['window_width']}x{self.cfg['window_height']}"
            )

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        db.init_db()

        self.scan_worker = None
        self.selected_photos = []
        self.scan_failures = []

        self._build_menu()
        self._build_ui()
        self._load_existing_photos()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_menu(self):
        menubar = ctk.CTkFrame(self, height=32, fg_color=("gray90", "gray20"))
        menubar.grid(row=0, column=0, sticky="ew")
        menubar.grid_columnconfigure(3, weight=1)

        ctk.CTkButton(
            menubar, text="📁 添加目录", width=100, height=28,
            command=self._add_dir,
        ).grid(row=0, column=0, padx=4, pady=2)

        ctk.CTkButton(
            menubar, text="🔄 重新扫描", width=100, height=28,
            command=self._rescan,
        ).grid(row=0, column=1, padx=4, pady=2)

        ctk.CTkButton(
            menubar, text="⚡ 批量操作", width=100, height=28,
            command=self._batch_op,
        ).grid(row=0, column=2, padx=4, pady=2)

        self.sel_label = ctk.CTkLabel(
            menubar, text="已选 0 张", anchor="e", width=80,
            text_color="gray",
        )
        self.sel_label.grid(row=0, column=3, padx=8, pady=2, sticky="e")

        self.dir_label = ctk.CTkLabel(
            menubar, text=self._dir_summary(), anchor="e"
        )
        self.dir_label.grid(row=0, column=4, padx=8, pady=2, sticky="e")

        ctk.CTkButton(
            menubar, text="⚙", width=32, height=28,
            command=self._settings,
        ).grid(row=0, column=5, padx=4, pady=2)

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.search_bar = SearchBar(self, on_search=self._on_search)
        self.search_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        main_frame.grid_columnconfigure(0, weight=2)
        main_frame.grid_columnconfigure(1, weight=3)
        main_frame.grid_rowconfigure(0, weight=1)

        sidebar_w = self.cfg.get("sidebar_width", 480)
        self.sidebar = Sidebar(
            main_frame,
            on_photo_click=self._on_photo_click,
            on_selection_change=self._on_selection_change,
            thumb_size=self.cfg.get("thumbnail_size", 120),
            width=sidebar_w,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 2))

        self.detail = DetailPanel(main_frame, db_module=db, on_save=self._on_detail_save)
        self.detail.grid(row=0, column=1, sticky="nsew", padx=(2, 0))

        self.progress_bar = ProgressBar(self)
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=4, pady=2)

    def _dir_summary(self):
        dirs = self.cfg.get("root_dirs", [])
        if not dirs:
            return "未添加目录"
        return f"监控目录: {len(dirs)} 个"

    def _add_dir(self):
        new_dir = filedialog.askdirectory(title="选择照片根目录")
        if not new_dir:
            return
        dirs = self.cfg.get("root_dirs", [])
        if new_dir not in dirs:
            dirs.append(new_dir)
            self.cfg["root_dirs"] = dirs
            config_mod.save_config(self.cfg)
            self.dir_label.configure(text=self._dir_summary())
            self._start_scan()

    def _rescan(self):
        dirs = self.cfg.get("root_dirs", [])
        if not dirs:
            self._add_dir()
            return
        self._start_scan()

    def _start_scan(self):
        if self.scan_worker and self.scan_worker.is_alive():
            self.scan_worker.cancel()
            self.scan_worker.join(timeout=2)

        self.scan_failures.clear()
        self.progress_bar.reset()
        self.scan_worker = ScanWorker(
            self.cfg.get("root_dirs", []),
            db,
            on_progress=self._on_scan_progress,
            on_done=self._on_scan_done,
            on_error=self._on_scan_error,
        )
        self.scan_worker.start()

    def _on_scan_progress(self, current, total, filepath):
        self.after(0, lambda: self.progress_bar.update_progress(current, total, filepath))

    def _on_scan_done(self):
        self.after(0, self._scan_finished)

    def _on_scan_error(self, filepath, error):
        self.scan_failures.append((filepath, error))

    def _scan_finished(self):
        failures = list(self.scan_failures)
        if failures:
            self.progress_bar.set_done_with_failures(len(failures))
            self.after(
                100,
                lambda: messagebox.showwarning(
                    "扫描完成（有错误）",
                    f"扫描完成，但有 {len(failures)} 个文件处理失败:\n\n"
                    + "\n".join(
                        f"• {os.path.basename(fp) if fp else '(未知)'}: {err}"
                        for fp, err in failures[:20]
                    )
                    + ("\n…" if len(failures) > 20 else ""),
                ),
            )
        else:
            self.progress_bar.set_done()
        self._load_existing_photos()

    def _load_existing_photos(self):
        conn = db.get_connection()
        keyword, date_from, date_to = self.search_bar.get_values()
        if keyword or date_from or date_to:
            photos = db.search_photos(conn, keyword, date_from, date_to)
        else:
            photos = db.get_all_photos(conn)
        conn.close()
        self.current_photos = photos
        self.sidebar.load_photos(photos)
        self._update_sel_label()

    def _on_search(self, keyword, date_from, date_to):
        conn = db.get_connection()
        photos = db.search_photos(conn, keyword, date_from, date_to)
        conn.close()
        self.current_photos = photos
        self.sidebar.load_photos(photos)

    def _on_photo_click(self, photo, selected):
        self.selected_photos = list(selected) if selected else [photo]
        conn = db.get_connection()
        full = db.get_photo_by_id(conn, photo["id"])
        conn.close()
        if full:
            self.detail.show_photo(full)
        self._update_sel_label()

    def _on_selection_change(self, selected):
        self.selected_photos = list(selected)
        self._update_sel_label()

    def _update_sel_label(self):
        n = len(self.selected_photos)
        self.sel_label.configure(
            text=f"已选 {n} 张",
            text_color=("gray" if n == 0 else "#3B82F6"),
        )

    def _on_detail_save(self, photo):
        pass

    def _batch_op(self):
        photos = self.sidebar.get_selected_photos()
        if not photos:
            messagebox.showinfo("提示", "请先在左侧选择照片（支持 Ctrl/Shift 多选）")
            return
        BatchDialog(self, photos)

    def _settings(self):
        dialog = SettingsDialog(self, self.cfg)
        self.wait_window(dialog)
        if dialog.saved:
            self.cfg = config_mod.load_config()
            self.dir_label.configure(text=self._dir_summary())

    def _on_close(self):
        self.cfg["window_width"] = self.winfo_width()
        self.cfg["window_height"] = self.winfo_height()
        config_mod.save_config(self.cfg)
        if self.scan_worker and self.scan_worker.is_alive():
            self.scan_worker.cancel()
        self.destroy()


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, cfg: dict, **kwargs):
        super().__init__(master, **kwargs)
        self.title("设置")
        self.geometry("500x400")
        self.transient(master)
        self.grab_set()
        self.cfg = cfg
        self.saved = False

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="监控目录:", anchor="e", width=70).grid(
            row=0, column=0, padx=8, pady=8, sticky="e"
        )

        dir_frame = ctk.CTkFrame(self, fg_color="transparent")
        dir_frame.grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        dir_frame.grid_columnconfigure(0, weight=1)

        self.dir_list = ctk.CTkScrollableFrame(dir_frame, height=180)
        self.dir_list.grid(row=0, column=0, sticky="nsew")
        self.dir_list.grid_columnconfigure(0, weight=1)

        btn_frame = ctk.CTkFrame(dir_frame, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="w", pady=4)

        ctk.CTkButton(btn_frame, text="添加", width=60, command=self._add_dir).pack(
            side="left", padx=2
        )
        ctk.CTkButton(btn_frame, text="移除选中", width=80, command=self._remove_dir).pack(
            side="left", padx=2
        )

        self._refresh_dirs()

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=1, column=0, columnspan=2, padx=8, pady=8, sticky="e")

        ctk.CTkButton(bottom, text="取消", width=80, fg_color="gray", command=self.destroy).pack(
            side="left", padx=4
        )
        ctk.CTkButton(bottom, text="保存", width=80, command=self._save).pack(
            side="left", padx=4
        )

    def _refresh_dirs(self):
        for w in self.dir_list.winfo_children():
            w.destroy()
        self.dir_checkboxes = []
        for d in self.cfg.get("root_dirs", []):
            var = ctk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(self.dir_list, text=d, variable=var)
            cb.grid(row=len(self.dir_checkboxes), column=0, sticky="w", padx=4, pady=2)
            self.dir_checkboxes.append((d, var))

    def _add_dir(self):
        from tkinter import filedialog
        new = filedialog.askdirectory(title="添加目录")
        if new and new not in self.cfg.get("root_dirs", []):
            self.cfg.setdefault("root_dirs", []).append(new)
            self._refresh_dirs()

    def _remove_dir(self):
        to_remove = [d for d, v in self.dir_checkboxes if v.get()]
        for d in to_remove:
            self.cfg["root_dirs"].remove(d)
        self._refresh_dirs()

    def _save(self):
        config_mod.save_config(self.cfg)
        self.saved = True
        self.destroy()
