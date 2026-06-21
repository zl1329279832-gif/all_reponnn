from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
rcParams["axes.unicode_minus"] = False


class HistoryPage(QWidget):
    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("最近 7 天专注统计")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        layout.addWidget(title)

        self._summary_frame = QFrame()
        self._summary_frame.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border-radius: 10px; }"
        )
        summary_layout = QHBoxLayout(self._summary_frame)
        summary_layout.setContentsMargins(20, 16, 20, 16)
        summary_layout.setSpacing(32)

        self._today_count_label = QLabel("今日完成: 0 个")
        self._today_count_label.setStyleSheet(
            "color: #ff6b6b; font-size: 14px; font-weight: bold;"
        )
        self._week_count_label = QLabel("本周完成: 0 个")
        self._week_count_label.setStyleSheet(
            "color: #4ecdc4; font-size: 14px; font-weight: bold;"
        )
        summary_layout.addWidget(self._today_count_label)
        summary_layout.addWidget(self._week_count_label)
        summary_layout.addStretch()

        layout.addWidget(self._summary_frame)

        self._chart_frame = QFrame()
        self._chart_frame.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border-radius: 10px; }"
        )
        chart_layout = QVBoxLayout(self._chart_frame)
        chart_layout.setContentsMargins(16, 16, 16, 16)

        self._figure = Figure(figsize=(7, 3.5), dpi=100, facecolor="#2a2a2a")
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setStyleSheet("background-color: #2a2a2a;")
        chart_layout.addWidget(self._canvas)

        layout.addWidget(self._chart_frame, 1)

    def refresh(self) -> None:
        stats = self._storage.get_last_7_days_stats()
        today_count = self._storage.get_today_completed_count()
        week_count = sum(s["count"] for s in stats)

        self._today_count_label.setText(f"今日完成: {today_count} 个")
        self._week_count_label.setText(f"本周完成: {week_count} 个")

        self._figure.clear()
        ax = self._figure.add_subplot(111)
        ax.set_facecolor("#2a2a2a")

        dates = [s["date"] for s in stats]
        counts = [s["count"] for s in stats]

        bars = ax.bar(dates, counts, color="#e74c3c", alpha=0.85, edgecolor="none")

        for bar, count in zip(bars, counts):
            if count > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    bar.get_height() + 0.15,
                    str(count),
                    ha="center",
                    va="bottom",
                    color="#ffffff",
                    fontsize=10,
                )

        ax.set_xlabel("日期", color="#cccccc", fontsize=10)
        ax.set_ylabel("完成番茄数", color="#cccccc", fontsize=10)
        ax.tick_params(colors="#aaaaaa", labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#444444")
        ax.set_ylim(0, max(max(counts) + 2, 4))
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax.grid(axis="y", linestyle="--", alpha=0.2, color="#666666")
        self._figure.tight_layout()
        self._canvas.draw_idle()
