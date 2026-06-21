import sys
import os


def main() -> int:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from PyQt6.QtWidgets import QApplication

    from app.core.database import init_db, get_plugins_dir
    from app.ui.main_window import MainWindow

    init_db()
    get_plugins_dir()

    app = QApplication(sys.argv)
    app.setApplicationName("单机游戏存档管理器")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
