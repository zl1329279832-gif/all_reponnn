import os
import customtkinter as ctk
from PIL import Image, ImageTk
from collections import defaultdict
from datetime import datetime
import tkinter as tk


class ThumbnailButton(ctk.CTkFrame):
    def __init__(self, master, photo: dict, thumb_size=120, on_click=None, **kwargs):
        self.photo_data = photo
        self.on_click_cb = on_click
        self.thumb_size = thumb_size
        self._selected = False
        self._app = master.winfo_toplevel()
        self._bg_normal = self._get_canvas_bg()

        super().__init__(
            master,
            width=thumb_size + 12,
            height=thumb_size + 12,
            fg_color="transparent",
            **kwargs,
        )
        self.grid_propagate(False)

        thumb_img = None
        self._tk_image = None
        if photo.get("thumbnail_path") and os.path.exists(photo["thumbnail_path"]):
            try:
                from PIL import ImageTk as PIL_ImageTk
                pil_img = Image.open(photo["thumbnail_path"])
                pil_img.thumbnail((thumb_size, thumb_size), Image.LANCZOS)
                self._tk_image = PIL_ImageTk.PhotoImage(pil_img)
                thumb_img = self._tk_image
            except Exception:
                pass

        self.canvas_bg = ctk.CTkCanvas(
            self,
            width=thumb_size + 8,
            height=thumb_size + 8,
            highlightthickness=2,
            bd=0,
            bg=self._bg_normal,
            highlightbackground=self._bg_normal,
            highlightcolor=self._bg_normal,
            cursor="hand2",
        )
        self.canvas_bg.grid(row=0, column=0, padx=0, pady=0)

        if thumb_img:
            self.image_id = self.canvas_bg.create_image(
                (thumb_size + 8) // 2,
                (thumb_size + 8) // 2,
                image=thumb_img,
            )
        else:
            self.image_id = None
            self.canvas_bg.create_text(
                (thumb_size + 8) // 2,
                (thumb_size + 8) // 2,
                text=os.path.splitext(photo.get("filename", ""))[0][:8],
                fill="#666",
            )
        self.thumb_img = thumb_img

        for widget in (self, self.canvas_bg):
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Control-Button-1>", self._on_ctrl_click)
            widget.bind("<Shift-Button-1>", self._on_shift_click)

    def _on_click(self, event):
        if self.on_click_cb:
            self.on_click_cb(self.photo_data, modifiers=set())

    def _on_ctrl_click(self, event):
        if self.on_click_cb:
            self.on_click_cb(self.photo_data, modifiers={"ctrl"})
        return "break"

    def _on_shift_click(self, event):
        if self.on_click_cb:
            self.on_click_cb(self.photo_data, modifiers={"shift"})
        return "break"

    def _get_canvas_bg(self):
        try:
            mode = ctk.get_appearance_mode()
            return "#1F1F1F" if mode.lower() == "dark" else "#F5F5F5"
        except Exception:
            return "#F5F5F5"

    def set_selected(self, selected: bool):
        self._selected = selected
        color = "#3B82F6" if selected else self._bg_normal
        try:
            self.canvas_bg.configure(
                highlightbackground=color,
                highlightcolor=color,
            )
        except Exception:
            pass

    def is_selected(self):
        return self._selected


class Sidebar(ctk.CTkScrollableFrame):
    def __init__(self, master, on_photo_click=None, on_selection_change=None,
                 thumb_size=120, **kwargs):
        super().__init__(master, **kwargs)
        self.on_photo_click = on_photo_click
        self.on_selection_change = on_selection_change
        self.thumb_size = thumb_size
        self.photos = []
        self.thumb_buttons = []
        self.selected_ids = set()
        self._last_clicked_index = None

    def load_photos(self, photos: list):
        for w in self.winfo_children():
            w.destroy()
        self.thumb_buttons.clear()
        self.photos = list(photos)
        self.selected_ids = set()
        self._last_clicked_index = None

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

        width = self.winfo_width()
        cols = max(1, (width - 20) // (self.thumb_size + 16)) if width > 1 else 4

        global_index = 0
        for key in sorted_keys:
            label = ctk.CTkLabel(
                self, text=key, font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
            )
            label.pack(fill="x", padx=4, pady=(10, 2))

            grid_frame = ctk.CTkFrame(self, fg_color="transparent")
            grid_frame.pack(fill="x", padx=4, pady=2)

            group_photos = groups[key]
            for i, photo in enumerate(group_photos):
                row, col = divmod(i, cols)
                btn = ThumbnailButton(
                    grid_frame,
                    photo=photo,
                    thumb_size=self.thumb_size,
                    on_click=self._make_handler(global_index),
                )
                btn.grid(row=row, column=col, padx=3, pady=3)
                self.thumb_buttons.append(btn)
                global_index += 1

        self._notify_selection()

    def _make_handler(self, index):
        def handler(photo, modifiers):
            self._handle_click(index, photo, modifiers)
        return handler

    def _handle_click(self, index: int, photo: dict, modifiers: set):
        if "ctrl" in modifiers:
            pid = photo["id"]
            if pid in self.selected_ids:
                self.selected_ids.discard(pid)
            else:
                self.selected_ids.add(pid)
            self._last_clicked_index = index
        elif "shift" in modifiers and self._last_clicked_index is not None:
            start = min(self._last_clicked_index, index)
            end = max(self._last_clicked_index, index)
            for i in range(start, end + 1):
                if 0 <= i < len(self.photos):
                    self.selected_ids.add(self.photos[i]["id"])
        else:
            self.selected_ids.clear()
            self.selected_ids.add(photo["id"])
            self._last_clicked_index = index

        self._refresh_selection_ui()
        self._notify_selection(photo)

    def _refresh_selection_ui(self):
        for btn in self.thumb_buttons:
            btn.set_selected(btn.photo_data["id"] in self.selected_ids)

    def _notify_selection(self, clicked_photo=None):
        selected = self.get_selected_photos()
        if self.on_selection_change:
            self.on_selection_change(selected)
        if self.on_photo_click and clicked_photo is not None:
            self.on_photo_click(clicked_photo, selected)

    def get_selected_photos(self):
        return [p for p in self.photos if p["id"] in self.selected_ids]
