import sys
sys.argv = ['screenshot']

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.main_window import MainWindow
from PyQt6.QtGui import QPixmap

app = QApplication(sys.argv)
w = MainWindow()
w.show()

def take_screenshot():
    pixmap = w.grab()
    pixmap.save("screenshot.png")
    print(f"Screenshot saved: {pixmap.width()}x{pixmap.height()}")
    app.quit()

QTimer.singleShot(1000, take_screenshot)
app.exec()
