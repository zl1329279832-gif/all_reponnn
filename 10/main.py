import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from core.storage import CustomerStorage
from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("客户跟进工具")
    app.setOrganizationName("LocalCRM")

    font = QFont()
    font.setPointSize(10)
    app.setFont(font)

    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    storage = CustomerStorage(data_dir / "crm.db")

    window = MainWindow(storage)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
