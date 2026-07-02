import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# ensure project root is on path when running as script or bundled exe
_root = Path(__file__).parent
sys.path.insert(0, str(_root))

load_dotenv(_root / ".env")

# load config.json into os.environ so agents can use os.getenv
_config_path = _root / "config.json"
if _config_path.exists():
    try:
        for k, v in json.loads(_config_path.read_text()).items():
            os.environ.setdefault(k, str(v))
    except (json.JSONDecodeError, OSError):
        pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from database.db import init_db
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VideoScout")
    app.setStyle("Fusion")

    # dark palette baseline
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1e293b"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#f1f5f9"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#0f172a"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1e293b"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#f1f5f9"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#334155"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#f1f5f9"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#38bdf8"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#0f172a"))
    app.setPalette(palette)

    init_db()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
