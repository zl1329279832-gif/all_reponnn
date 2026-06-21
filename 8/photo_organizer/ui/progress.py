import customtkinter as ctk


class ProgressBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(self, text="就绪", anchor="w", width=120)
        self.status_label.grid(row=0, column=0, padx=(8, 4), pady=4, sticky="w")

        self.progress = ctk.CTkProgressBar(self, width=300)
        self.progress.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        self.progress.set(0)

        self.detail_label = ctk.CTkLabel(
            self, text="", anchor="w", wraplength=500
        )
        self.detail_label.grid(row=0, column=2, padx=(4, 8), pady=4, sticky="w")

    def update_progress(self, current: int, total: int, current_file: str = ""):
        if total > 0:
            ratio = current / total
            self.progress.set(ratio)
            self.status_label.configure(text=f"{current}/{total}")
        else:
            self.progress.set(0)
            self.status_label.configure(text="0/0")
        if current_file:
            display = current_file if len(current_file) <= 60 else "..." + current_file[-57:]
            self.detail_label.configure(text=display)

    def set_done(self):
        self.progress.set(1.0)
        self.status_label.configure(text="扫描完成")
        self.detail_label.configure(text="")

    def reset(self):
        self.progress.set(0)
        self.status_label.configure(text="就绪")
        self.detail_label.configure(text="")
