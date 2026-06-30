from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtGui import QFont
from services.scanner_service import get_channel_stats
from database.db import get_connection


class Analytics(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Analytics")
        title.setFont(QFont("", 13, QFont.Weight.Bold))
        layout.addWidget(title)

        refresh_btn = QPushButton("↺ Refresh")
        refresh_btn.setFixedWidth(100)
        refresh_btn.clicked.connect(self._load)
        layout.addWidget(refresh_btn)

        layout.addWidget(QLabel("Channel Performance"))
        self.channel_table = QTableWidget()
        self.channel_table.setColumnCount(5)
        self.channel_table.setHorizontalHeaderLabels(
            ["Channel", "Niche", "Subs", "Videos Found", "Avg Score"]
        )
        self.channel_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.channel_table)

        layout.addWidget(QLabel("Scan History (last 10)"))
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(
            ["Time", "Channels", "Videos Found", "Top Score"]
        )
        self.history_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.history_table)

    def _load(self):
        # channel stats
        stats = get_channel_stats()
        self.channel_table.setRowCount(len(stats))
        for i, r in enumerate(stats):
            self.channel_table.setItem(i, 0, QTableWidgetItem(r["name"]))
            self.channel_table.setItem(i, 1, QTableWidgetItem(r["niche_tag"] or ""))
            self.channel_table.setItem(i, 2, QTableWidgetItem(f"{r['subscribers']:,}"))
            self.channel_table.setItem(i, 3, QTableWidgetItem(str(r["video_count"])))
            avg = r["avg_score"]
            self.channel_table.setItem(i, 4, QTableWidgetItem(
                f"{avg:.1f}" if avg else "—"
            ))

        # scan history
        conn = get_connection()
        history = conn.execute(
            """SELECT * FROM scan_history ORDER BY scanned_at DESC LIMIT 10"""
        ).fetchall()
        conn.close()
        self.history_table.setRowCount(len(history))
        for i, r in enumerate(history):
            self.history_table.setItem(i, 0, QTableWidgetItem(r["scanned_at"][:16]))
            self.history_table.setItem(i, 1, QTableWidgetItem(str(r["channels_scanned"])))
            self.history_table.setItem(i, 2, QTableWidgetItem(str(r["videos_found"])))
            self.history_table.setItem(i, 3, QTableWidgetItem(str(r["top_score"])))
