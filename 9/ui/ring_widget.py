from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import QWidget


class RingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self._remaining_text = "25:00"
        self._state_text = "准备专注"
        self._ring_color = QColor("#2d7ff9")
        self._bg_color = QColor("#e8edf3")
        self.setMinimumSize(240, 240)

    def set_progress(self, progress: float):
        self._progress = max(0.0, min(1.0, progress))
        self.update()

    def set_remaining(self, text: str):
        self._remaining_text = text
        self.update()

    def set_state_text(self, text: str):
        self._state_text = text
        self.update()

    def set_ring_color(self, color: QColor):
        self._ring_color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height()) - 20
        cx = self.width() / 2
        cy = self.height() / 2

        pen_width = 10
        radius = side / 2 - pen_width / 2
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        bg_pen = QPen(self._bg_color, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 360 * 16)

        if self._progress > 0:
            arc_pen = QPen(self._ring_color, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            span = int(self._progress * 360 * 16)
            painter.drawArc(rect, 90 * 16, -span)

        painter.setPen(QColor("#333333"))
        font = QFont("Segoe UI", 36, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._remaining_text)

        label_rect = QRectF(cx - radius, cy + radius * 0.35, radius * 2, 30)
        painter.setPen(QColor("#888888"))
        painter.setFont(QFont("Segoe UI", 12))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self._state_text)

        painter.end()
