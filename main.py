"""Entry point: launches QApplication + MainWindow."""

import os
import sys

os.environ["QT_API"] = "pyside6"

from PySide6.QtWidgets import QApplication

import db
from ui.main_window import MainWindow

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "harcama.db")


def main():
    app = QApplication(sys.argv)
    conn = db.connect(DB_PATH)
    window = MainWindow(conn)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
