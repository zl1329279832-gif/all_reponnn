import customtkinter as ctk
from tkinter import filedialog


class SearchBar(ctk.CTkFrame):
    def __init__(self, master, on_search=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_search = on_search
        self.grid_columnconfigure(1, weight=1)

        self.keyword_label = ctk.CTkLabel(self, text="搜索:", width=40)
        self.keyword_label.grid(row=0, column=0, padx=(8, 2), pady=6)

        self.keyword_var = ctk.StringVar()
        self.keyword_var.trace_add("write", self._on_change)
        self.keyword_entry = ctk.CTkEntry(
            self, textvariable=self.keyword_var, placeholder_text="文件名 / 标题 / 备注"
        )
        self.keyword_entry.grid(row=0, column=1, padx=4, pady=6, sticky="ew")

        self.date_from_label = ctk.CTkLabel(self, text="从:", width=24)
        self.date_from_label.grid(row=0, column=2, padx=(8, 2), pady=6)

        self.date_from_var = ctk.StringVar()
        self.date_from_var.trace_add("write", self._on_change)
        self.date_from_entry = ctk.CTkEntry(
            self,
            textvariable=self.date_from_var,
            placeholder_text="YYYY-MM-DD",
            width=110,
        )
        self.date_from_entry.grid(row=0, column=3, padx=2, pady=6)

        self.date_to_label = ctk.CTkLabel(self, text="到:", width=24)
        self.date_to_label.grid(row=0, column=4, padx=(4, 2), pady=6)

        self.date_to_var = ctk.StringVar()
        self.date_to_var.trace_add("write", self._on_change)
        self.date_to_entry = ctk.CTkEntry(
            self,
            textvariable=self.date_to_var,
            placeholder_text="YYYY-MM-DD",
            width=110,
        )
        self.date_to_entry.grid(row=0, column=5, padx=2, pady=6)

        self.clear_btn = ctk.CTkButton(
            self, text="清除", width=60, command=self._clear
        )
        self.clear_btn.grid(row=0, column=6, padx=(8, 8), pady=6)

    def _on_change(self, *_):
        if self.on_search:
            self.on_search(
                self.keyword_var.get().strip(),
                self.date_from_var.get().strip(),
                self.date_to_var.get().strip(),
            )

    def _clear(self):
        self.keyword_var.set("")
        self.date_from_var.set("")
        self.date_to_var.set("")

    def get_values(self):
        return (
            self.keyword_var.get().strip(),
            self.date_from_var.get().strip(),
            self.date_to_var.get().strip(),
        )
