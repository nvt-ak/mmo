from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QColor
from services.tiktok_service import check_saturation

STATUS_COLORS = {
    "fresh":     "#22c55e",
    "medium":    "#f59e0b",
    "saturated": "#ef4444",
    "error":     "#94a3b8",
    "unknown":   "#94a3b8",
}
STATUS_EMOJI = {"fresh": "🟢", "medium": "🟡", "saturated": "🔴", "error": "⚪", "unknown": "⚪"}


class _CheckWorker(QThread):
    result = pyqtSignal(dict)

    def __init__(self, keyword: str):
        super().__init__()
        self.keyword = keyword

    def run(self):
        self.result.emit(check_saturation(self.keyword))


class TikTokChecker(QWidget):
    def __init__(self):
        super().__init__()
        self._results: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Check how saturated a keyword is on TikTok DE.\n"
            "🟢 FRESH < 20 videos/7d   🟡 MEDIUM 20-100   🔴 SATURATED > 100"
        ))

        input_row = QHBoxLayout()
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText("Enter keyword, e.g. aespa winter fancam")
        self.kw_input.returnPressed.connect(self._check)
        self.check_btn = QPushButton("Check")
        self.check_btn.clicked.connect(self._check)
        input_row.addWidget(self.kw_input)
        input_row.addWidget(self.check_btn)
        layout.addLayout(input_row)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Keyword", "Videos (7d)", "Status", "Cached"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)

    def _check(self):
        kw = self.kw_input.text().strip()
        if not kw:
            return
        self.check_btn.setEnabled(False)
        self.status_label.setText(f"Checking '{kw}'…")
        self._worker = _CheckWorker(kw)
        self._worker.result.connect(self._on_result)
        self._worker.start()

    def _on_result(self, data: dict):
        self.check_btn.setEnabled(True)
        self.kw_input.clear()
        self._results.insert(0, data)
        self.status_label.setText(
            f"{STATUS_EMOJI.get(data['status'], '⚪')} "
            f"'{data['keyword']}' → {data['status'].upper()} "
            f"({data['video_count_7d']} videos)"
        )
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(len(self._results))
        for i, r in enumerate(self._results):
            self.table.setItem(i, 0, QTableWidgetItem(r["keyword"]))
            count = r["video_count_7d"]
            self.table.setItem(i, 1, QTableWidgetItem(
                str(count) if count >= 0 else "error"
            ))
            status = r.get("status", "unknown")
            s_item = QTableWidgetItem(
                f"{STATUS_EMOJI.get(status, '⚪')} {status.upper()}"
            )
            s_item.setForeground(QColor(STATUS_COLORS.get(status, "#94a3b8")))
            self.table.setItem(i, 2, s_item)
            self.table.setItem(i, 3, QTableWidgetItem(
                "✓ cached" if r.get("cached") else "live"
            ))
