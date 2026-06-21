import os
import customtkinter as ctk
from PIL import Image


class DetailPanel(ctk.CTkFrame):
    def __init__(self, master, db_module=None, on_save=None, **kwargs):
        super().__init__(master, **kwargs)
        self.db_module = db_module
        self.on_save = on_save
        self.current_photo = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(self.preview_frame, text="选择一张照片查看详情")
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.preview_image = None

        self.info_frame = ctk.CTkScrollableFrame(self, label_text="元数据")
        self.info_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.info_frame.grid_columnconfigure(1, weight=1)

        self.meta_labels = {}
        meta_fields = [
            ("文件名", "filename"),
            ("拍摄时间", "capture_time"),
            ("相机型号", "camera_model"),
            ("文件大小", "file_size"),
            ("修改时间", "file_mtime"),
            ("分辨率", "resolution"),
            ("路径", "filepath"),
        ]
        for i, (display, key) in enumerate(meta_fields):
            lbl = ctk.CTkLabel(self.info_frame, text=f"{display}:", anchor="e", width=70)
            lbl.grid(row=i, column=0, padx=(4, 8), pady=2, sticky="e")
            val = ctk.CTkLabel(self.info_frame, text="", anchor="w", wraplength=400)
            val.grid(row=i, column=1, padx=4, pady=2, sticky="w")
            self.meta_labels[key] = val

        self.edit_frame = ctk.CTkFrame(self)
        self.edit_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.edit_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.edit_frame, text="标题:", width=50).grid(
            row=0, column=0, padx=4, pady=4
        )
        self.title_var = ctk.StringVar()
        self.title_entry = ctk.CTkEntry(self.edit_frame, textvariable=self.title_var)
        self.title_entry.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        ctk.CTkLabel(self.edit_frame, text="备注:", width=50).grid(
            row=1, column=0, padx=4, pady=4
        )
        self.notes_var = ctk.StringVar()
        self.notes_entry = ctk.CTkEntry(self.edit_frame, textvariable=self.notes_var)
        self.notes_entry.grid(row=1, column=1, padx=4, pady=4, sticky="ew")

        self.save_btn = ctk.CTkButton(
            self.edit_frame, text="保存", width=80, command=self._save
        )
        self.save_btn.grid(row=1, column=2, padx=4, pady=4)

    def show_photo(self, photo: dict):
        self.current_photo = photo

        if photo.get("filepath") and os.path.exists(photo["filepath"]):
            try:
                img = Image.open(photo["filepath"])
                w, h = img.size
                max_w = self.preview_frame.winfo_width() - 20 or 500
                max_h = self.preview_frame.winfo_height() - 20 or 400
                scale = min(max_w / w, max_h / h, 1.0)
                new_w = int(w * scale)
                new_h = int(h * scale)
                if new_w > 0 and new_h > 0:
                    img.thumbnail((new_w, new_h), Image.LANCZOS)
                    self.preview_image = ctk.CTkImage(
                        light_image=img, size=(new_w, new_h)
                    )
                    self.preview_label.configure(image=self.preview_image, text="")
                img.close()
            except Exception:
                self.preview_label.configure(image=None, text="无法加载图片")
                self.preview_image = None
        else:
            self.preview_label.configure(image=None, text="文件不存在")
            self.preview_image = None

        self.meta_labels["filename"].configure(text=photo.get("filename", ""))
        self.meta_labels["capture_time"].configure(text=photo.get("capture_time", ""))
        self.meta_labels["camera_model"].configure(text=photo.get("camera_model", ""))

        size_bytes = photo.get("file_size", 0)
        if size_bytes:
            size_str = f"{size_bytes:,} bytes"
            if size_bytes > 1024 * 1024:
                size_str += f" ({size_bytes / 1024 / 1024:.1f} MB)"
            elif size_bytes > 1024:
                size_str += f" ({size_bytes / 1024:.1f} KB)"
        else:
            size_str = ""
        self.meta_labels["file_size"].configure(text=size_str)

        self.meta_labels["file_mtime"].configure(text=photo.get("file_mtime", ""))

        res = ""
        if photo.get("width") and photo.get("height"):
            res = f"{photo['width']} x {photo['height']}"
        self.meta_labels["resolution"].configure(text=res)

        self.meta_labels["filepath"].configure(text=photo.get("filepath", ""))

        self.title_var.set(photo.get("title", ""))
        self.notes_var.set(photo.get("notes", ""))

    def _save(self):
        if not self.current_photo or not self.db_module:
            return
        photo_id = self.current_photo["id"]
        title = self.title_var.get().strip()
        notes = self.notes_var.get().strip()
        conn = self.db_module.get_connection()
        self.db_module.update_title_notes(conn, photo_id, title, notes)
        conn.close()
        self.current_photo["title"] = title
        self.current_photo["notes"] = notes
        if self.on_save:
            self.on_save(self.current_photo)

    def clear(self):
        self.current_photo = None
        self.preview_label.configure(image=None, text="选择一张照片查看详情")
        self.preview_image = None
        for val in self.meta_labels.values():
            val.configure(text="")
        self.title_var.set("")
        self.notes_var.set("")
