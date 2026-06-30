"""
Channel Discovery UI
Tab 1: Search + score channels → add to watchlist
Tab 2: Account Warmer — follow channels + warm up
Tab 3: Feed Harvest — parse homepage feed for video opportunities
"""
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QFileDialog, QTextEdit,
    QSpinBox, QComboBox, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from services.channel_discovery import search_channels, save_channel
from services.account_warmer import warm_account, harvest_feed
from utils.logger import get_logger

log = get_logger("ui.discovery")


# ── Workers ──────────────────────────────────────────────────────────────────

class _SearchWorker(QThread):
    done  = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, keyword: str, max_subs: int):
        super().__init__()
        self.keyword  = keyword
        self.max_subs = max_subs

    def run(self):
        try:
            results = search_channels(self.keyword, max_subs=self.max_subs)
            self.done.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class _WarmWorker(QThread):
    status  = pyqtSignal(str)
    done    = pyqtSignal(dict)
    error   = pyqtSignal(str)

    def __init__(self, profile_path: str, channels: list[dict], watch: int):
        super().__init__()
        self.profile_path = profile_path
        self.channels     = channels
        self.watch        = watch

    def run(self):
        try:
            result = warm_account(
                chrome_profile_path=self.profile_path,
                channels_to_follow=self.channels,
                watch_videos=self.watch,
                on_status=lambda msg: self.status.emit(msg),
            )
            self.done.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class _HarvestWorker(QThread):
    status = pyqtSignal(str)
    done   = pyqtSignal(list)
    error  = pyqtSignal(str)

    def __init__(self, profile_path: str, view_min: int, view_max: int):
        super().__init__()
        self.profile_path = profile_path
        self.view_min     = view_min
        self.view_max     = view_max

    def run(self):
        try:
            videos = harvest_feed(
                chrome_profile_path=self.profile_path,
                view_min=self.view_min,
                view_max=self.view_max,
                on_status=lambda msg: self.status.emit(msg),
            )
            self.done.emit(videos)
        except Exception as e:
            self.error.emit(str(e))


# ── Main Widget ───────────────────────────────────────────────────────────────

class ChannelDiscovery(QWidget):
    feed_videos_found = pyqtSignal(list)  # → DailyDigest can consume

    def __init__(self):
        super().__init__()
        self._channels: list[dict] = []
        self._feed_videos: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Channel Agent")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._build_discover_tab(), "🔍 Discover Channels")
        tabs.addTab(self._build_warm_tab(),     "🔥 Warm Account")
        tabs.addTab(self._build_harvest_tab(),  "🌾 Harvest Feed")
        layout.addWidget(tabs)

    # ── Tab 1: Discover ───────────────────────────────────────────────────

    def _build_discover_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(QLabel(
            "Search YouTube for channels matching your niche.\n"
            "Score based on: avg views 150K-200K, small subs, upload consistency."
        ))

        # search row
        row = QHBoxLayout()
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText("keyword, e.g. kpop idol fancam")
        self.kw_input.returnPressed.connect(self._search)

        self.niche_combo = QComboBox()
        self.niche_combo.setEditable(True)
        self.niche_combo.addItems(["kpop", "idol", "entertainment", "fancam"])

        self.max_subs_spin = QSpinBox()
        self.max_subs_spin.setRange(1_000, 500_000)
        self.max_subs_spin.setSingleStep(5_000)
        self.max_subs_spin.setValue(50_000)
        self.max_subs_spin.setPrefix("Max subs: ")

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._search)

        row.addWidget(self.kw_input, 3)
        row.addWidget(self.niche_combo, 1)
        row.addWidget(self.max_subs_spin)
        row.addWidget(self.search_btn)
        layout.addLayout(row)

        self.search_status = QLabel("")
        layout.addWidget(self.search_status)

        # results table
        self.ch_table = QTableWidget()
        self.ch_table.setColumnCount(6)
        self.ch_table.setHorizontalHeaderLabels(
            ["Score", "Channel", "Subs", "Avg Views", "Videos", "Status"]
        )
        hdr = self.ch_table.horizontalHeader()
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in [0, 2, 3, 4, 5]:
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.ch_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ch_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.ch_table)

        # action row
        action_row = QHBoxLayout()
        add_sel_btn = QPushButton("✅ Add Selected to Watchlist")
        add_sel_btn.clicked.connect(self._add_selected)
        add_all_btn = QPushButton("➕ Add All")
        add_all_btn.clicked.connect(self._add_all)
        action_row.addWidget(add_sel_btn)
        action_row.addWidget(add_all_btn)
        action_row.addStretch()
        layout.addLayout(action_row)

        return w

    # ── Tab 2: Warm Account ───────────────────────────────────────────────

    def _build_warm_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(QLabel(
            "Warm up a YouTube account using an existing Chrome profile.\n"
            "This will follow channels from your watchlist and watch videos\n"
            "to train the YouTube algorithm for idol/kpop content."
        ))

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # profile path
        profile_row = QHBoxLayout()
        self.profile_input = QLineEdit()
        self.profile_input.setPlaceholderText(
            "Chrome profile path, e.g. C:/Users/you/AppData/Local/Google/Chrome/User Data/Profile 1"
        )
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_profile)
        profile_row.addWidget(QLabel("Profile:"))
        profile_row.addWidget(self.profile_input, 4)
        profile_row.addWidget(browse_btn)
        layout.addLayout(profile_row)

        # options
        opts = QHBoxLayout()
        self.watch_spin = QSpinBox()
        self.watch_spin.setRange(1, 20)
        self.watch_spin.setValue(3)
        self.watch_spin.setPrefix("Watch videos: ")
        opts.addWidget(self.watch_spin)
        opts.addStretch()
        layout.addLayout(opts)

        self.warm_btn = QPushButton("🔥 Start Warm Session")
        self.warm_btn.setFixedHeight(36)
        self.warm_btn.clicked.connect(self._start_warm)
        layout.addWidget(self.warm_btn)

        layout.addWidget(QLabel("Session Log:"))
        self.warm_log = QTextEdit()
        self.warm_log.setReadOnly(True)
        self.warm_log.setStyleSheet(
            "background:#0f172a; color:#94a3b8; "
            "font-family:monospace; font-size:11px;"
        )
        layout.addWidget(self.warm_log)

        return w

    # ── Tab 3: Harvest Feed ───────────────────────────────────────────────

    def _build_harvest_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(QLabel(
            "Open YouTube homepage with your warmed account,\n"
            "parse video cards that match view criteria,\n"
            "and export URLs for cloning."
        ))

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # profile + filters
        profile_row2 = QHBoxLayout()
        self.harvest_profile = QLineEdit()
        self.harvest_profile.setPlaceholderText("Chrome profile path")
        browse2 = QPushButton("Browse")
        browse2.clicked.connect(
            lambda: self.harvest_profile.setText(
                QFileDialog.getExistingDirectory(self, "Select Chrome Profile")
            )
        )
        profile_row2.addWidget(QLabel("Profile:"))
        profile_row2.addWidget(self.harvest_profile, 4)
        profile_row2.addWidget(browse2)
        layout.addLayout(profile_row2)

        filter_row = QHBoxLayout()
        self.h_view_min = QSpinBox()
        self.h_view_min.setRange(0, 10_000_000)
        self.h_view_min.setSingleStep(10_000)
        self.h_view_min.setValue(150_000)
        self.h_view_min.setPrefix("Min views: ")

        self.h_view_max = QSpinBox()
        self.h_view_max.setRange(0, 10_000_000)
        self.h_view_max.setSingleStep(10_000)
        self.h_view_max.setValue(200_000)
        self.h_view_max.setPrefix("Max views: ")

        filter_row.addWidget(self.h_view_min)
        filter_row.addWidget(self.h_view_max)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.harvest_btn = QPushButton("🌾 Harvest Feed Now")
        self.harvest_btn.setFixedHeight(36)
        self.harvest_btn.clicked.connect(self._start_harvest)
        layout.addWidget(self.harvest_btn)

        self.harvest_status = QLabel("")
        layout.addWidget(self.harvest_status)

        # results table
        self.feed_table = QTableWidget()
        self.feed_table.setColumnCount(4)
        self.feed_table.setHorizontalHeaderLabels(
            ["Title", "Channel", "Views", "URL"]
        )
        self.feed_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.feed_table)

        copy_btn = QPushButton("📋 Copy All URLs")
        copy_btn.clicked.connect(self._copy_feed_urls)
        layout.addWidget(copy_btn)

        return w

    # ── Search ────────────────────────────────────────────────────────────

    def _search(self):
        kw = self.kw_input.text().strip()
        if not kw:
            return
        self.search_btn.setEnabled(False)
        self.search_status.setText(f"Searching '{kw}'…")
        self._search_worker = _SearchWorker(kw, self.max_subs_spin.value())
        self._search_worker.done.connect(self._on_search_done)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.start()

    def _on_search_done(self, channels: list[dict]):
        self._channels = channels
        self.search_btn.setEnabled(True)
        self.search_status.setText(f"Found {len(channels)} channels")
        self.ch_table.setRowCount(len(channels))
        for i, ch in enumerate(channels):
            score = ch["score"]
            s_item = QTableWidgetItem(str(score))
            s_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color = "#22c55e" if score >= 70 else "#f59e0b" if score >= 40 else "#ef4444"
            s_item.setForeground(QColor(color))
            self.ch_table.setItem(i, 0, s_item)
            self.ch_table.setItem(i, 1, QTableWidgetItem(ch["name"]))
            self.ch_table.setItem(i, 2, QTableWidgetItem(f"{ch['subscribers']:,}"))
            self.ch_table.setItem(i, 3, QTableWidgetItem(f"{ch['avg_views']:,}"))
            self.ch_table.setItem(i, 4, QTableWidgetItem(str(ch["video_count"])))
            tracked = "✅ Tracked" if ch["already_tracked"] else "—"
            self.ch_table.setItem(i, 5, QTableWidgetItem(tracked))

    def _on_search_error(self, msg: str):
        self.search_btn.setEnabled(True)
        self.search_status.setText(f"❌ {msg}")

    def _add_selected(self):
        rows = {idx.row() for idx in self.ch_table.selectedIndexes()}
        niche = self.niche_combo.currentText().strip() or "kpop"
        count = 0
        for row in rows:
            ch = self._channels[row]
            if not ch["already_tracked"]:
                save_channel(ch, niche_tag=niche)
                self._channels[row]["already_tracked"] = True
                count += 1
        self.search_status.setText(f"✅ Added {count} channels to watchlist")
        self._on_search_done(self._channels)

    def _add_all(self):
        niche = self.niche_combo.currentText().strip() or "kpop"
        count = 0
        for ch in self._channels:
            if not ch["already_tracked"]:
                save_channel(ch, niche_tag=niche)
                ch["already_tracked"] = True
                count += 1
        self.search_status.setText(f"✅ Added {count} channels to watchlist")
        self._on_search_done(self._channels)

    # ── Warm ─────────────────────────────────────────────────────────────

    def _browse_profile(self):
        path = QFileDialog.getExistingDirectory(self, "Select Chrome Profile Directory")
        if path:
            self.profile_input.setText(path)

    def _start_warm(self):
        profile = self.profile_input.text().strip()
        if not profile:
            self.warm_log.append("❌ Please set Chrome profile path first")
            return

        from database.db import get_connection
        conn = get_connection()
        channels = [
            dict(r) for r in
            conn.execute("SELECT id, name, url FROM channels WHERE is_active=1").fetchall()
        ]
        conn.close()

        if not channels:
            self.warm_log.append("❌ No channels in watchlist — discover channels first")
            return

        self.warm_btn.setEnabled(False)
        self.warm_log.append(
            f"Starting warm session — {len(channels)} channels, "
            f"watch {self.watch_spin.value()} videos"
        )

        self._warm_worker = _WarmWorker(profile, channels, self.watch_spin.value())
        self._warm_worker.status.connect(lambda m: self.warm_log.append(m))
        self._warm_worker.done.connect(self._on_warm_done)
        self._warm_worker.error.connect(lambda e: self.warm_log.append(f"❌ {e}"))
        self._warm_worker.start()

    def _on_warm_done(self, result: dict):
        self.warm_btn.setEnabled(True)
        self.warm_log.append(
            f"✅ Session complete — "
            f"followed={result['followed']} "
            f"watched={result['watched']} "
            f"errors={len(result['errors'])}"
        )

    # ── Harvest ───────────────────────────────────────────────────────────

    def _start_harvest(self):
        profile = self.harvest_profile.text().strip()
        if not profile:
            self.harvest_status.setText("❌ Set Chrome profile path first")
            return
        self.harvest_btn.setEnabled(False)
        self.harvest_status.setText("Harvesting feed…")
        self._harvest_worker = _HarvestWorker(
            profile,
            self.h_view_min.value(),
            self.h_view_max.value(),
        )
        self._harvest_worker.status.connect(
            lambda m: self.harvest_status.setText(m)
        )
        self._harvest_worker.done.connect(self._on_harvest_done)
        self._harvest_worker.error.connect(
            lambda e: self.harvest_status.setText(f"❌ {e}")
        )
        self._harvest_worker.start()

    def _on_harvest_done(self, videos: list[dict]):
        self.harvest_btn.setEnabled(True)
        self._feed_videos = videos
        self.harvest_status.setText(
            f"✅ Found {len(videos)} videos matching criteria"
        )
        self.feed_table.setRowCount(len(videos))
        for i, v in enumerate(videos):
            self.feed_table.setItem(i, 0, QTableWidgetItem(v["title"]))
            self.feed_table.setItem(i, 1, QTableWidgetItem(v.get("channel", "")))
            self.feed_table.setItem(i, 2, QTableWidgetItem(f"{v['view_count']:,}"))
            self.feed_table.setItem(i, 3, QTableWidgetItem(v["youtube_url"]))
        if videos:
            self.feed_videos_found.emit(videos)

    def _copy_feed_urls(self):
        from PyQt6.QtWidgets import QApplication
        urls = "\n".join(v["youtube_url"] for v in self._feed_videos)
        QApplication.clipboard().setText(urls)
        self.harvest_status.setText(f"📋 {len(self._feed_videos)} URLs copied")
