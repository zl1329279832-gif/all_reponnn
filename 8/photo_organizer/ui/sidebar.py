import os
import customtkinter as ctk
from PIL import Image, ImageTk
from collections import defaultdict
from datetime import datetime


class ThumbnailButton(ctk.CTkButton):
    def __init__(self, master, photo: dict, thumb_size=120, on_click=None, **kwargs):
        self.photo_data = photo
        self.on_click_cb = on_click
        self.thumb_size = thumb_size

        thumb_img = None
        if photo.get("thumbnail_path") and os.path.exists(photo["thumbnail_path"]):
            try:
                thumb_img = ctk.CTkImage(
                    light_image=Image.open(photo["thumbnail_path"]),
                    size=(thumb_size, thumb_size),
                )
            except Exception:
                pass

        super().__init__(
            master,
            image=thumb_img,
            text="",
            width=thumb_size + 8,
            height=thumb_size + 8,
            fg_color="transparent",
            border_width=2,
            border_color="transparent",
            hover_color=("gray80", "gray30"),
            command=self._on_click,
            **kwargs,
        )
        self.thumb_img = thumb_img

    def _on_click(self):
        if self.on_click_cb:
            self.on_click_cb(self.photo_data)

    def set_selected(self, selected: bool):
        self.configure(
            border_color=("#3B82F6" if selected else "transparent")
        )


class Sidebar(ctk.CTkScrollableFrame):
    def __init__(self, master, on_photo_click=None, thumb_size=120, **kwargs):
        super().__init__(master, **kwargs)
        self.on_photo_click = on_photo_click
        self.thumb_size = thumb_size
        self.photos = []
        self.thumb_buttons = []
        self.selected_photo_id = None

    def load_photos(self, photos: list):
        for w in self.winfo_children():
            w.destroy()
        self.thumb_buttons.clear()
        self.photos = photos
        self.selected_photo_id = None

        groups = defaultdict(list)
        for p in photos:
            try:
                ct = p.get("capture_time", "")
                if ct:
                    dt = datetime.fromisoformat(ct)
                    key = dt.strftime("%Y-%m")
                else:
                    key = "未知日期"
            except (ValueError, TypeError):
                key = "未知日期"
            groups[key].append(p)

        sorted_keys = sorted(groups.keys(), reverse=True)

        cols = max(1, (self.winfo_width() - 20) // (self.thumb_size + 12)) if self.winfo_width() > 1 else 4

        for key in sorted_keys:
            label = ctk.CTkLabel(
                self, text=key, font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
            )
            label.pack(fill="x", padx=4, pady=(10, 2))

            grid_frame = ctk.CTkFrame(self, fg_color="transparent")
            grid_frame.pack(fill="x", padx=4, pady=2)

            for i, photo in enumerate(groups[key]):
                row, col = divmod(i, cols)
                btn = ThumbnailButton(
                    grid_frame,
                    photo=photo,
                    thumb_size=self.thumb_size,
                    on_click=self._on_thumb_click,
                )
                btn.grid(row=row, column=col, padx=3, pady=3)
                self.thumb_buttons.append(btn)

    def _on_thumb_click(self, photo):
        self.selected_photo_id = photo["id"]
        for btn in self.thumb_buttons:
            btn.set_selected(btn.photo_data["id"] == photo["id"])
        if self.on_photo_click:
            self.on_photo_click(photo)
