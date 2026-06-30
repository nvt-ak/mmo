from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QLabel, QComboBox, QMessageBox,
    QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from database.db import get_connection
from services.youtube_service import extract_channel_id, fetch_channel_info


class _FetchWorker(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        channel_id = extract_channel_id(self.url)
        if not channel_id:
            self.error.emit("Cannot resolve channel ID from URL.")
            return
        info = fetch_channel_info(channel_id)
        if not info:
            self.error.emit("Channel not found or API error.")
            return
        self.done.emit(info)


class ChannelManager(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load_channels()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ── Add channel row ──────────────────────────────────────────────
        add_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "YouTube channel URL or ID  (e.g. https://youtube.com/@aespa)"
        )
        self.niche_input = QComboBox()
        self.niche_input.setEditable(True)
        self.niche_input.addItems(["kpop", "idol", "entertainment", "gaming", "sports"])
        self.niche_input.setCurrentText("kpop")
        self.add_btn = QPushButton("Add Channel")
        self.add_btn.clicked.connect(self._on_add)
        add_row.addWidget(self.url_input, 4)
        add_row.addWidget(QLabel("Niche:"))
        add_row.addWidget(self.niche_input, 1)
        add_row.addWidget(self.add_btn)
        layout.addLayout(add_row)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # ── Table ────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Channel Name", "Niche", "Subscribers", "Last Scanned", "Active", "Actions"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def _load_channels(self):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM channels ORDER BY added_at DESC"
        ).fetchall()
        conn.close()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["name"]))
            self.table.setItem(i, 1, QTableWidgetItem(r["niche_tag"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(f"{r['subscribers']:,}"))
            self.table.setItem(i, 3, QTableWidgetItem(
                (r["last_scanned"] or "Never")[:16]
            ))
            active = "✅" if r["is_active"] else "⏸"
            self.table.setItem(i, 4, QTableWidgetItem(active))

            btn_row = QWidget()
            btn_layout = QHBoxLayout(btn_row)
            btn_layout.setContentsMargins(2, 2, 2, 2)

            toggle_btn = QPushButton("Pause" if r["is_active"] else "Resume")
            toggle_btn.setFixedWidth(70)
            ch_id = r["id"]
            toggle_btn.clicked.connect(lambda _, cid=ch_id: self._toggle(cid))

            del_btn = QPushButton("Delete")
            del_btn.setFixedWidth(60)
            del_btn.clicked.connect(lambda _, cid=ch_id: self._delete(cid))

            btn_layout.addWidget(toggle_btn)
            btn_layout.addWidget(del_btn)
            self.table.setCellWidget(i, 5, btn_row)

    def _on_add(self):
        url = self.url_input.text().strip()
        if not url:
            return
        self.add_btn.setEnabled(False)
        self.status_label.setText("Fetching channel info…")
        self._worker = _FetchWorker(url)
        self._worker.done.connect(self._on_fetch_done)
        self._worker.error.connect(self._on_fetch_error)
        self._worker.start()

    def _on_fetch_done(self, info: dict):
        niche = self.niche_input.currentText().strip() or "kpop"
        conn = get_connection()
        conn.execute(
            """INSERT OR IGNORE INTO channels (id, name, url, niche_tag, subscribers)
               VALUES (?,?,?,?,?)""",
            (info["id"], info["name"], info["url"], niche, info["subscribers"]),
        )
        conn.commit()
        conn.close()
        self.url_input.clear()
        self.status_label.setText(f"✅ Added: {info['name']} ({info['subscribers']:,} subs)")
        self.add_btn.setEnabled(True)
        self._load_channels()

    def _on_fetch_error(self, msg: str):
        self.status_label.setText(f"❌ {msg}")
        self.add_btn.setEnabled(True)

    def _toggle(self, channel_id: str):
        conn = get_connection()
        conn.execute(
            "UPDATE channels SET is_active = NOT is_active WHERE id = ?",
            (channel_id,),
        )
        conn.commit()
        conn.close()
        self._load_channels()

    def _delete(self, channel_id: str):
        reply = QMessageBox.question(
            self, "Delete Channel",
            "Delete this channel and all its videos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            conn = get_connection()
            conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
            conn.commit()
            conn.close()
            self._load_channels()
