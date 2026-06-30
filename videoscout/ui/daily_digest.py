import webbrowser
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFileDialog, QProgressBar, QFrame, QTextEdit, QSplitter,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont

from services.scanner_service import (
    scan_all_channels, get_daily_digest, mark_video_used,
    DEFAULT_VIEW_MIN, DEFAULT_VIEW_MAX, DEFAULT_DAYS, DEFAULT_MAX_SUBS,
)
from utils.export import to_clipboard, to_csv
from utils.logger import get_logger

log = get_logger("ui.digest")

STATUS_COLORS = {
    "fresh":     "#22c55e",
    "medium":    "#f59e0b",
    "saturated": "#ef4444",
    "unknown":   "#94a3b8",
    "error":     "#94a3b8",
}


# ── Log forwarder → captures log output to UI ────────────────────────────────
import logging

class _QtLogHandler(logging.Handler, QObject):
    new_line = pyqtSignal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.new_line.emit(msg)


# ── Worker ───────────────────────────────────────────────────────────────────
class _ScanWorker(QThread):
    progress  = pyqtSignal(int, int, str)   # current, total, channel_name
    finished  = pyqtSignal(object)          # ScanResult
    error_sig = pyqtSignal(str)

    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg

    def run(self):
        try:
            result = scan_all_channels(
                view_min=self.cfg.get("view_min", DEFAULT_VIEW_MIN),
                view_max=self.cfg.get("view_max", DEFAULT_VIEW_MAX),
                days=self.cfg.get("days",     DEFAULT_DAYS),
                max_subs=self.cfg.get("max_subs", DEFAULT_MAX_SUBS),
                progress_callback=lambda cur, tot, name: self.progress.emit(cur, tot, name),
            )
            self.finished.emit(result)
        except Exception as e:
            log.error(f"Scan worker crashed: {e}", exc_info=True)
            self.error_sig.emit(str(e))


# ── Widget ───────────────────────────────────────────────────────────────────
class DailyDigest(QWidget):
    def __init__(self):
        super().__init__()
        self._videos: list[dict] = []
        self._filter_cfg: dict   = {}
        self._build_ui()
        self._attach_log_handler()
        self._refresh_table()

    # ── Build UI ─────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # header
        header = QHBoxLayout()
        title = QLabel("Daily Digest")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()

        self.scan_btn = QPushButton("🔍  Scan Now")
        self.scan_btn.setFixedHeight(34)
        self.scan_btn.setMinimumWidth(120)
        self.scan_btn.clicked.connect(self._start_scan)

        self.refresh_btn = QPushButton("↺  Refresh")
        self.refresh_btn.setFixedHeight(34)
        self.refresh_btn.clicked.connect(self._refresh_table)

        header.addWidget(self.scan_btn)
        header.addWidget(self.refresh_btn)
        root.addLayout(header)

        # progress (hidden until scan)
        self.progress_bar   = QProgressBar()
        self.progress_label = QLabel("")
        self.progress_bar.hide()
        self.progress_label.hide()
        root.addWidget(self.progress_bar)
        root.addWidget(self.progress_label)

        self.summary_label = QLabel("Press 'Scan Now' to fetch videos.")
        root.addWidget(self.summary_label)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # splitter: table on top, log on bottom
        splitter = QSplitter(Qt.Orientation.Vertical)

        # ── Video table ──────────────────────────────────────────────────
        table_widget = QWidget()
        tv_layout = QVBoxLayout(table_widget)
        tv_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Score", "Title", "Channel", "Subs", "Views", "Date", "TikTok"]
        )
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in [0, 2, 3, 4, 5, 6]:
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._open_video)
        tv_layout.addWidget(self.table)

        # export row
        export_row = QHBoxLayout()
        self._btn("📋 Copy All URLs", export_row, self._export_clipboard)
        self._btn("📋 Copy Top 10",   export_row, lambda: self._export_clipboard(10))
        self._btn("💾 Export CSV",    export_row, self._export_csv)
        self._btn("✅ Mark Used",     export_row, self._mark_used)
        export_row.addStretch()
        tv_layout.addLayout(export_row)

        hint = QLabel("💡 Double-click row to open in browser")
        hint.setStyleSheet("color:#64748b; font-size:11px;")
        tv_layout.addWidget(hint)

        splitter.addWidget(table_widget)

        # ── Log panel ────────────────────────────────────────────────────
        log_widget = QWidget()
        lv = QVBoxLayout(log_widget)
        lv.setContentsMargins(0, 4, 0, 0)
        lv.addWidget(QLabel("Debug Log"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(200)
        self.log_box.setStyleSheet(
            "background:#0f172a; color:#94a3b8; font-family:monospace; font-size:11px;"
        )
        clear_btn = QPushButton("Clear Log")
        clear_btn.setFixedWidth(90)
        clear_btn.clicked.connect(self.log_box.clear)
        lv.addWidget(self.log_box)
        lv.addWidget(clear_btn)
        splitter.addWidget(log_widget)

        splitter.setSizes([480, 200])
        root.addWidget(splitter)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _btn(self, label, layout, slot):
        b = QPushButton(label)
        b.clicked.connect(slot)
        layout.addWidget(b)
        return b

    def _attach_log_handler(self):
        self._log_handler = _QtLogHandler()
        self._log_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                              datefmt="%H:%M:%S")
        )
        self._log_handler.new_line.connect(self._append_log)
        logging.getLogger().addHandler(self._log_handler)

    def _append_log(self, msg: str):
        self.log_box.append(msg)
        self.log_box.verticalScrollBar().setValue(
            self.log_box.verticalScrollBar().maximum()
        )

    # ── Data ─────────────────────────────────────────────────────────────

    def _refresh_table(self):
        self._videos = get_daily_digest(limit=20)
        self.summary_label.setText(
            f"Showing top {len(self._videos)} unused opportunities"
        )
        self.table.setRowCount(len(self._videos))
        for i, v in enumerate(self._videos):
            score = v["opportunity_score"]
            s_item = QTableWidgetItem(str(score))
            s_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444"
            s_item.setForeground(QColor(color))
            self.table.setItem(i, 0, s_item)
            self.table.setItem(i, 1, QTableWidgetItem(v["title"]))
            self.table.setItem(i, 2, QTableWidgetItem(v.get("channel_name", "")))
            subs = v.get("channel_subscribers") or 0
            self.table.setItem(i, 3, QTableWidgetItem(f"{subs:,}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{v['view_count']:,}"))
            self.table.setItem(i, 5, QTableWidgetItem(v["upload_date"]))
            status = v.get("tiktok_status", "unknown")
            st_item = QTableWidgetItem(status.upper())
            st_item.setForeground(QColor(STATUS_COLORS.get(status, "#94a3b8")))
            st_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 6, st_item)

    # ── Scan ─────────────────────────────────────────────────────────────

    def _start_scan(self):
        log.info("=== Scan triggered by user ===")
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("⏳  Scanning…")
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.show()
        self._worker = _ScanWorker(self._filter_cfg)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_done)
        self._worker.error_sig.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int, name: str):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"Scanning {current}/{total}: {name}")

    def _on_done(self, result):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("🔍  Scan Now")
        self.progress_bar.hide()
        self.progress_label.hide()
        self.summary_label.setText(
            f"✅ Done — {result.channels_scanned} channels scanned, "
            f"{result.videos_found} new videos (top score: {result.top_score})"
        )
        self._refresh_table()

    def _on_error(self, msg: str):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("🔍  Scan Now")
        self.progress_bar.hide()
        self.progress_label.hide()
        self.summary_label.setText(f"❌ Scan error: {msg}")

    # ── Actions ──────────────────────────────────────────────────────────

    def _open_video(self, index):
        v = self._videos[index.row()]
        webbrowser.open(v["youtube_url"])

    def _export_clipboard(self, limit: int = 0):
        videos = self._videos[:limit] if limit else self._videos
        to_clipboard(videos)
        self.summary_label.setText(f"📋 {len(videos)} URLs copied to clipboard")

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "digest.csv", "CSV files (*.csv)"
        )
        if path:
            to_csv(self._videos, Path(path))
            self.summary_label.setText(f"💾 Saved: {path}")

    def _mark_used(self):
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        for row in rows:
            mark_video_used(self._videos[row]["id"])
        self._refresh_table()

    def set_filter_config(self, cfg: dict):
        """Called by MainWindow when settings change."""
        self._filter_cfg = cfg

    def trigger_scan(self):
        """Called by scheduler."""
        self._start_scan()
