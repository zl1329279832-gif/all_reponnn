import os
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image as PILImage
from ..scanner import (
    batch_move_to_album,
    batch_rename_by_date,
    _get_exif_data,
    _extract_capture_time,
)
from ..database import get_connection, update_filepath


class BatchDialog(ctk.CTkToplevel):
    MODE_NONE = None
    MODE_MOVE = "move"
    MODE_RENAME = "rename"

    def __init__(self, master, photos: list, **kwargs):
        super().__init__(master, **kwargs)
        self.title("批量操作")
        self.geometry("760x560")
        self.transient(master)
        self.grab_set()
        self.photos = photos
        self.selected_paths = [p["filepath"] for p in photos]
        self.mode = self.MODE_NONE
        self.preview_pairs = []
        self.target_dir = ""

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_top_bar()
        self._build_list_area()
        self._build_bottom_bar()
        self._populate_plain_list(self.selected_paths)

    def _build_top_bar(self):
        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            top, text=f"已选 {len(self.photos)} 张照片",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=8, pady=4, sticky="w")

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=8, pady=4, sticky="e")

        self.move_btn = ctk.CTkButton(
            btn_frame, text="步骤1: 选择移动目标", command=self._choose_move_target
        )
        self.move_btn.pack(side="left", padx=4)

        self.rename_btn = ctk.CTkButton(
            btn_frame, text="步骤1: 生成重命名预览", command=self._generate_rename_preview
        )
        self.rename_btn.pack(side="left", padx=4)

        self.mode_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12))
        self.mode_label.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 2))

    def _build_list_area(self):
        self.list_frame = ctk.CTkScrollableFrame(self, label_text="预览列表")
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.list_frame.grid_columnconfigure(0, weight=1)

    def _build_bottom_bar(self):
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        bottom.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(bottom, text="选择操作生成预览后可执行", text_color="gray")
        self.status_label.grid(row=0, column=0, sticky="w", padx=4)

        btn_wrap = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_wrap.grid(row=0, column=1, sticky="e")

        self.cancel_btn = ctk.CTkButton(
            btn_wrap, text="关闭", width=80, fg_color="gray", command=self.destroy
        )
        self.cancel_btn.pack(side="left", padx=4)

        self.execute_btn = ctk.CTkButton(
            btn_wrap, text="步骤2: 确认执行", width=120,
            state="disabled", command=self._execute
        )
        self.execute_btn.pack(side="left", padx=4)

    def _populate_plain_list(self, paths: list):
        for w in self.list_frame.winfo_children():
            w.destroy()
        for i, p in enumerate(paths):
            ctk.CTkLabel(self.list_frame, text=p, anchor="w").grid(
                row=i, column=0, sticky="w", padx=4, pady=1
            )

    def _populate_preview(self, pairs: list):
        for w in self.list_frame.winfo_children():
            w.destroy()
        for i, (old, new) in enumerate(pairs):
            line = f"{os.path.basename(old)}  →  {os.path.basename(new)}"
            if os.path.dirname(old) != os.path.dirname(new):
                line += f"   [{os.path.dirname(new)}]"
            ctk.CTkLabel(self.list_frame, text=line, anchor="w").grid(
                row=i, column=0, sticky="w", padx=4, pady=1
            )

    def _resolve_move_conflicts(self, pairs: list):
        seen = {}
        resolved = []
        for old, new in pairs:
            folder = os.path.dirname(new)
            base, ext = os.path.splitext(os.path.basename(new))
            candidate = new
            counter = 1
            key = os.path.normpath(candidate)
            while key in seen or (os.path.exists(candidate) and os.path.normpath(old) != os.path.normpath(candidate)):
                candidate = os.path.join(folder, f"{base}_{counter}{ext}")
                key = os.path.normpath(candidate)
                counter += 1
            seen[key] = True
            resolved.append((old, candidate))
        return resolved

    def _choose_move_target(self):
        album_dir = filedialog.askdirectory(title="选择移动到的目标相册目录")
        if not album_dir:
            return
        self.target_dir = album_dir
        self.mode = self.MODE_MOVE
        raw_pairs = [(p, os.path.join(album_dir, os.path.basename(p)))
                     for p in self.selected_paths]
        self.preview_pairs = self._resolve_move_conflicts(raw_pairs)
        self._populate_preview(self.preview_pairs)
        self.mode_label.configure(
            text=f"【移动】目标目录: {album_dir}",
            text_color=("#1a1a1a", "#dce4ee"),
        )
        self.execute_btn.configure(state="normal")
        self.status_label.configure(
            text=f"预览 {len(self.preview_pairs)} 项，确认无误请点「确认执行」",
            text_color="blue",
        )

    def _build_rename_preview_pairs(self):
        pairs = []
        for p in self.selected_paths:
            dirname = os.path.dirname(p)
            ext = os.path.splitext(p)[1]
            try:
                stat = os.stat(p)
                img = PILImage.open(p)
                exif = _get_exif_data(img)
                ct = _extract_capture_time(exif, stat.st_mtime)
                img.close()
            except Exception:
                stat = os.stat(p)
                ct = datetime.fromtimestamp(stat.st_mtime).isoformat()
            dt = datetime.fromisoformat(ct)
            new_name = dt.strftime("%Y%m%d_%H%M%S") + ext
            new_path = os.path.join(dirname, new_name)
            pairs.append((p, new_path))
        return self._resolve_move_conflicts(pairs)

    def _generate_rename_preview(self):
        self.mode = self.MODE_RENAME
        self.target_dir = ""
        try:
            self.preview_pairs = self._build_rename_preview_pairs()
        except Exception as e:
            messagebox.showerror("错误", f"生成预览失败: {e}")
            return
        self._populate_preview(self.preview_pairs)
        self.mode_label.configure(
            text="【按拍摄日期重命名】格式: YYYYMMDD_HHMMSS.ext",
            text_color=("#1a1a1a", "#dce4ee"),
        )
        self.execute_btn.configure(state="normal")
        self.status_label.configure(
            text=f"预览 {len(self.preview_pairs)} 项，确认无误请点「确认执行」",
            text_color="blue",
        )

    def _execute(self):
        if not self.preview_pairs:
            return
        confirm_msg = f"将对 {len(self.preview_pairs)} 张照片执行以下操作:\n"
        if self.mode == self.MODE_MOVE:
            confirm_msg += f"移动到: {self.target_dir}\n"
        elif self.mode == self.MODE_RENAME:
            confirm_msg += "按拍摄日期重命名\n"
        else:
            return
        confirm_msg += "确认执行？"
        if not messagebox.askyesno("确认执行", confirm_msg):
            return

        self.execute_btn.configure(state="disabled")
        self.move_btn.configure(state="disabled")
        self.rename_btn.configure(state="disabled")
        self.status_label.configure(text="执行中...", text_color="orange")
        self.update()

        old_paths = [p[0] for p in self.preview_pairs]
        if self.mode == self.MODE_MOVE:
            results = self._execute_move()
            action = "移动"
        elif self.mode == self.MODE_RENAME:
            results = self._execute_rename()
            action = "重命名"
        else:
            return

        conn = get_connection()
        for old, new in results["success"]:
            update_filepath(conn, old, new, os.path.basename(new))
        conn.close()

        self._show_results(results, action)

    def _execute_move(self):
        success = []
        failed = []
        for old, new in self.preview_pairs:
            try:
                if not os.path.exists(old):
                    failed.append((old, "源文件不存在"))
                    continue
                os.makedirs(os.path.dirname(new), exist_ok=True)
                if os.path.normpath(old) == os.path.normpath(new):
                    success.append((old, new))
                    continue
                if os.path.exists(new):
                    failed.append((old, f"目标已存在: {new}"))
                    continue
                os.rename(old, new)
                success.append((old, new))
            except Exception as e:
                failed.append((old, str(e)))
        return {"success": success, "failed": failed}

    def _execute_rename(self):
        success = []
        failed = []
        for old, new in self.preview_pairs:
            try:
                if not os.path.exists(old):
                    failed.append((old, "源文件不存在"))
                    continue
                if os.path.normpath(old) == os.path.normpath(new):
                    success.append((old, new))
                    continue
                if os.path.exists(new):
                    failed.append((old, f"目标已存在: {new}"))
                    continue
                os.rename(old, new)
                success.append((old, new))
            except Exception as e:
                failed.append((old, str(e)))
        return {"success": success, "failed": failed}

    def _show_results(self, results: dict, action: str):
        for w in self.list_frame.winfo_children():
            w.destroy()

        row_cursor = 0
        if results["success"]:
            ctk.CTkLabel(
                self.list_frame,
                text=f"✓ {action}成功 {len(results['success'])} 项",
                text_color="green",
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).grid(row=row_cursor, column=0, sticky="w", padx=4, pady=2)
            row_cursor += 1
            for old, new in results["success"]:
                ctk.CTkLabel(
                    self.list_frame,
                    text=f"  {os.path.basename(old)} → {os.path.basename(new)}",
                    anchor="w",
                ).grid(row=row_cursor, column=0, sticky="w", padx=4, pady=1)
                row_cursor += 1

        if results["failed"]:
            ctk.CTkLabel(
                self.list_frame,
                text=f"✗ {action}失败 {len(results['failed'])} 项（见下方）",
                text_color="red",
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).grid(row=row_cursor, column=0, sticky="w", padx=4, pady=(8, 2))
            row_cursor += 1
            for path, err in results["failed"]:
                ctk.CTkLabel(
                    self.list_frame,
                    text=f"  {os.path.basename(path)}: {err}",
                    anchor="w",
                    text_color="red",
                ).grid(row=row_cursor, column=0, sticky="w", padx=4, pady=1)
                row_cursor += 1

        self.status_label.configure(
            text=f"完成：成功 {len(results['success'])} / 失败 {len(results['failed'])}",
            text_color=("green" if not results["failed"] else "orange"),
        )
        self.execute_btn.configure(state="disabled")
        self.mode_label.configure(
            text=f"【{action}】执行完毕",
            text_color=("#1a1a1a", "#dce4ee"),
        )
