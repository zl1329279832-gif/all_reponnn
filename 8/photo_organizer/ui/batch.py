import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ..scanner import batch_move_to_album, batch_rename_by_date
from ..database import get_connection, update_filepath


class BatchDialog(ctk.CTkToplevel):
    def __init__(self, master, photos: list, **kwargs):
        super().__init__(master, **kwargs)
        self.title("批量操作")
        self.geometry("700x500")
        self.transient(master)
        self.grab_set()
        self.photos = photos
        self.selected_paths = [p["filepath"] for p in photos]

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text=f"已选 {len(photos)} 张照片", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=8, pady=4, sticky="w"
        )

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=8, pady=4, sticky="e")

        self.move_btn = ctk.CTkButton(
            btn_frame, text="移动到相册目录", command=self._move_to_album
        )
        self.move_btn.pack(side="left", padx=4)

        self.rename_btn = ctk.CTkButton(
            btn_frame, text="按拍摄日期重命名", command=self._rename_by_date
        )
        self.rename_btn.pack(side="left", padx=4)

        self.list_frame = ctk.CTkScrollableFrame(self, label_text="预览列表")
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.list_frame.grid_columnconfigure(0, weight=1)

        self._populate_list(self.selected_paths)

    def _populate_list(self, paths: list, new_paths: list = None):
        for w in self.list_frame.winfo_children():
            w.destroy()
        for i, p in enumerate(paths):
            new_p = new_paths[i] if new_paths and i < len(new_paths) else None
            if new_p:
                text = f"{os.path.basename(p)}  →  {os.path.basename(new_p)}"
            else:
                text = p
            ctk.CTkLabel(self.list_frame, text=text, anchor="w").grid(
                row=i, column=0, sticky="w", padx=4, pady=1
            )

    def _move_to_album(self):
        album_dir = filedialog.askdirectory(title="选择目标相册目录")
        if not album_dir:
            return
        preview = []
        for p in self.selected_paths:
            fname = os.path.basename(p)
            preview.append(os.path.join(album_dir, fname))

        confirm = ConfirmDialog(
            self, "确认移动", f"将 {len(self.selected_paths)} 张照片移动到:\n{album_dir}"
        )
        self.wait_window(confirm)
        if not confirm.confirmed:
            return

        self._populate_list(self.selected_paths, preview)

        results = batch_move_to_album(self.selected_paths, album_dir)

        conn = get_connection()
        for old, new in results["success"]:
            update_filepath(conn, old, new, os.path.basename(new))
        conn.close()

        self._show_results(results, "移动")

    def _rename_by_date(self):
        preview = []
        rename_map = []
        for p in self.selected_paths:
            dirname = os.path.dirname(p)
            ext = os.path.splitext(p)[1]
            stat = os.stat(p)
            try:
                from PIL import Image as PILImage
                from ..scanner import _get_exif_data, _extract_capture_time
                img = PILImage.open(p)
                exif = _get_exif_data(img)
                ct = _extract_capture_time(exif, stat.st_mtime)
                img.close()
            except Exception:
                from datetime import datetime
                ct = datetime.fromtimestamp(stat.st_mtime).isoformat()

            from datetime import datetime
            dt = datetime.fromisoformat(ct)
            new_name = dt.strftime("%Y%m%d_%H%M%S") + ext
            new_path = os.path.join(dirname, new_name)
            preview.append(new_path)
            rename_map.append((p, new_path))

        confirm = ConfirmDialog(
            self, "确认重命名", f"将 {len(self.selected_paths)} 张照片按拍摄日期重命名"
        )
        self.wait_window(confirm)
        if not confirm.confirmed:
            return

        self._populate_list(self.selected_paths, preview)

        results = batch_rename_by_date(self.selected_paths)

        conn = get_connection()
        for old, new in results["success"]:
            update_filepath(conn, old, new, os.path.basename(new))
        conn.close()

        self._show_results(results, "重命名")

    def _show_results(self, results: dict, action: str):
        for w in self.list_frame.winfo_children():
            w.destroy()

        if results["success"]:
            ctk.CTkLabel(
                self.list_frame,
                text=f"✓ {action}成功 {len(results['success'])} 项",
                text_color="green",
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=4, pady=2)
            for i, (old, new) in enumerate(results["success"]):
                ctk.CTkLabel(
                    self.list_frame,
                    text=f"  {os.path.basename(old)} → {os.path.basename(new)}",
                    anchor="w",
                ).grid(row=i + 1, column=0, sticky="w", padx=4, pady=1)

        fail_start = len(results["success"]) + 1
        if results["failed"]:
            ctk.CTkLabel(
                self.list_frame,
                text=f"✗ {action}失败 {len(results['failed'])} 项",
                text_color="red",
                anchor="w",
            ).grid(row=fail_start, column=0, sticky="w", padx=4, pady=2)
            for i, (path, err) in enumerate(results["failed"]):
                ctk.CTkLabel(
                    self.list_frame,
                    text=f"  {os.path.basename(path)}: {err}",
                    anchor="w",
                    text_color="red",
                ).grid(row=fail_start + i + 1, column=0, sticky="w", padx=4, pady=1)


class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str, message: str, **kwargs):
        super().__init__(master, **kwargs)
        self.title(title)
        self.geometry("400x200")
        self.transient(master)
        self.grab_set()
        self.confirmed = False

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=message, wraplength=360, justify="left").grid(
            row=0, column=0, padx=16, pady=16, sticky="w"
        )

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, padx=16, pady=8, sticky="e")

        ctk.CTkButton(
            btn_frame, text="取消", width=80, fg_color="gray",
            command=self._cancel
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame, text="确认", width=80, command=self._confirm
        ).pack(side="left", padx=4)

    def _confirm(self):
        self.confirmed = True
        self.destroy()

    def _cancel(self):
        self.confirmed = False
        self.destroy()
