import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from config.settings import SettingsManager
from core.storage import Storage
from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Pomodoro")
    app.setOrganizationName("PomodoroApp")
    app.setQuitOnLastWindowClosed(False)

    settings_manager = SettingsManager()
    storage = Storage(settings_manager.get_db_path())

    window = MainWindow(settings_manager, storage)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
