from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QLinearGradient
from PyQt6.QtWidgets import QWidget

from core.models import DailyStat


class BarChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stats: list[DailyStat] = []
        self.setMinimumHeight(220)

    def set_stats(self, stats: list[DailyStat]):
        self._stats = stats
        self.update()

    def paintEvent(self, event):
        if not self._stats:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin_l, margin_r, margin_t, margin_b = 50, 20, 20, 40
        chart_w = w - margin_l - margin_r
        chart_h = h - margin_t - margin_b

        max_secs = max(
            (s.completed_seconds + s.abandoned_seconds + s.paused_abandoned_seconds for s in self._stats),
            default=1,
        )
        if max_secs == 0:
            max_secs = 3600

        painter.setPen(QColor("#cccccc"))
        painter.setFont(QFont("Segoe UI", 9))
        for i in range(5):
            y = margin_t + chart_h - (i / 4) * chart_h
            val = int(max_secs * i / 4)
            mins = val // 60
            painter.drawLine(int(margin_l), int(y), int(w - margin_r), int(y))
            painter.drawText(0, int(y - 8), int(margin_l - 4), 20, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{mins}m")

        n = len(self._stats)
        if n == 0:
            painter.end()
            return
        bar_group_w = chart_w / n
        bar_w = min(bar_group_w * 0.6, 40)

        colors = {
            "completed": QColor("#2e7d32"),
            "abandoned": QColor("#d93025"),
            "paused_abandoned": QColor("#f57c00"),
        }

        for i, stat in enumerate(self._stats):
            gx = margin_l + i * bar_group_w + (bar_group_w - bar_w) / 2

            segments = [
                ("completed", stat.completed_seconds),
                ("abandoned", stat.abandoned_seconds),
                ("paused_abandoned", stat.paused_abandoned_seconds),
            ]

            y_cursor = margin_t + chart_h
            for key, secs in segments:
                if secs <= 0:
                    continue
                bar_h = (secs / max_secs) * chart_h
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(colors[key])
                painter.drawRect(int(gx), int(y_cursor - bar_h), int(bar_w), int(bar_h))
                y_cursor -= bar_h

            painter.setPen(QColor("#666666"))
            painter.setFont(QFont("Segoe UI", 9))
            label = stat.date[5:]
            painter.drawText(
                int(gx - 10), int(margin_t + chart_h + 5), int(bar_w + 20), 25,
                Qt.AlignmentFlag.AlignCenter, label,
            )

        legend_y = h - 12
        legend_items = [
            ("完成", colors["completed"]),
            ("放弃", colors["abandoned"]),
            ("暂停后放弃", colors["paused_abandoned"]),
        ]
        lx = margin_l
        painter.setFont(QFont("Segoe UI", 9))
        for label, color in legend_items:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRect(int(lx), int(legend_y - 8), 12, 12)
            painter.setPen(QColor("#333333"))
            painter.drawText(int(lx + 16), int(legend_y + 4), label)
            lx += painter.fontMetrics().horizontalAdvance(label) + 32

        painter.end()
