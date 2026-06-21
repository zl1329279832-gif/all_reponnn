import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QFontMetrics, QRadialGradient


class CircleTimer(QWidget):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self._time_text = "25:00"
        self._label_text = "准备开始"
        self._ring_width = 14
        self._bg_color = QColor("#2c2c2c")
        self._progress_color = QColor("#e74c3c")
        self._text_color = QColor("#ffffff")
        self._label_color = QColor("#aaaaaa")
        self.setMinimumSize(260, 260)

    def set_progress(self, progress: float) -> None:
        self._progress = max(0.0, min(1.0, progress))
        self.update()

    def set_time_text(self, text: str) -> None:
        self._time_text = text
        self.update()

    def set_label_text(self, text: str) -> None:
        self._label_text = text
        self.update()

    def set_progress_color(self, color: QColor) -> None:
        self._progress_color = color
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        side = min(self.width(), self.height())
        x = (self.width() - side) / 2
        y = (self.height() - side) / 2
        rect = QRectF(x, y, side, side)
        margin = self._ring_width + 6
        inner_rect = rect.adjusted(margin, margin, -margin, -margin)

        self._draw_background(painter, inner_rect)
        self._draw_ring(painter, rect)
        self._draw_progress(painter, rect)
        self._draw_text(painter, inner_rect)

    def _draw_background(self, painter: QPainter, rect: QRectF) -> None:
        gradient = QRadialGradient(rect.center(), rect.width() / 2)
        gradient.setColorAt(0.0, QColor("#3a3a3a"))
        gradient.setColorAt(1.0, QColor("#1e1e1e"))
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rect)

    def _draw_ring(self, painter: QPainter, rect: QRectF) -> None:
        pen = QPen(self._bg_color)
        pen.setWidth(self._ring_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        margin = self._ring_width / 2
        painter.drawArc(
            rect.adjusted(margin, margin, -margin, -margin), 0, 360 * 16
        )

    def _draw_progress(self, painter: QPainter, rect: QRectF) -> None:
        if self._progress <= 0:
            return
        pen = QPen(self._progress_color)
        pen.setWidth(self._ring_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        margin = self._ring_width / 2
        span = int(-self._progress * 360 * 16)
        painter.drawArc(
            rect.adjusted(margin, margin, -margin, -margin),
            90 * 16,
            span,
        )

    def _draw_text(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(self._text_color)
        time_font_size = int(rect.height() * 0.22)
        time_font = QFont()
        time_font.setPointSize(time_font_size)
        time_font.setBold(True)
        painter.setFont(time_font)
        fm = QFontMetrics(time_font)
        time_rect = fm.boundingRect(self._time_text)
        time_y = rect.center().y() - fm.ascent() / 2 - 4
        painter.drawText(
            int(rect.center().x() - time_rect.width() / 2),
            int(time_y),
            self._time_text,
        )

        painter.setPen(self._label_color)
        label_font_size = int(rect.height() * 0.07)
        label_font = QFont()
        label_font.setPointSize(label_font_size)
        painter.setFont(label_font)
        fm2 = QFontMetrics(label_font)
        label_rect = fm2.boundingRect(self._label_text)
        label_y = rect.center().y() + fm2.ascent() + 10
        painter.drawText(
            int(rect.center().x() - label_rect.width() / 2),
            int(label_y),
            self._label_text,
        )
