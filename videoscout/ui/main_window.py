from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.agent_tab import AgentTab
from ui.channel_discovery import ChannelDiscovery
from ui.daily_digest import DailyDigest
from ui.tiktok_checker import TikTokChecker
from ui.analytics import Analytics
from ui.settings import Settings
from services.scheduler_service import start as start_scheduler, update_schedule

NAV_ITEMS = [
    ("🤖  Agent Loop",    "agent"),
    ("🔍  Discovery",     "discovery"),
    ("📋  Daily Digest",  "digest"),
    ("🎯  TikTok Check",  "tiktok"),
    ("📊  Analytics",     "analytics"),
    ("⚙️  Settings",      "settings"),
]

NAV_STYLE = """
QPushButton {
    text-align: left;
    padding: 10px 16px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    color: #cbd5e1;
    background: transparent;
}
QPushButton:hover   { background: #1e293b; color: #f1f5f9; }
QPushButton:checked { background: #0f172a; color: #38bdf8; font-weight: bold; }
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VideoScout - Agentic Edition")
        self.setMinimumSize(1200, 750)
        self._build_ui()
        self._setup_scheduler()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background:#0f172a;")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(8, 8, 8, 8)
        sb.setSpacing(4)

        logo = QLabel("VideoScout")
        logo.setStyleSheet(
            "color:#38bdf8; font-size:18px; font-weight:bold; padding:16px;"
        )
        sb.addWidget(logo)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#334155;")
        sb.addWidget(sep)

        self._nav_btns: dict[str, QPushButton] = {}
        for label, key in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(NAV_STYLE)
            btn.clicked.connect(lambda _, k=key: self._switch(k))
            sb.addWidget(btn)
            self._nav_btns[key] = btn

        sb.addStretch()
        root.addWidget(sidebar)

        # ── Stack ─────────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background:#1e293b;")

        self._agent      = AgentTab()
        self._discovery  = ChannelDiscovery()
        self._digest     = DailyDigest()
        self._tiktok     = TikTokChecker()
        self._analytics  = Analytics()
        self._settings   = Settings()

        for w in [self._agent, self._discovery, self._digest, self._tiktok,
                  self._analytics, self._settings]:
            self.stack.addWidget(w)

        # feed videos from discovery → show in digest tab
        self._discovery.feed_videos_found.connect(self._on_feed_videos)

        root.addWidget(self.stack)
        self._switch("agent")

    def _switch(self, key: str):
        idx = {"agent": 0, "discovery": 1, "digest": 2, "tiktok": 3,
               "analytics": 4, "settings": 5}
        for k, btn in self._nav_btns.items():
            btn.setChecked(k == key)
        self.stack.setCurrentIndex(idx[key])

    def _setup_scheduler(self):
        self._settings.schedule_changed = self._on_schedule_changed
        start_scheduler(
            scan_fn=lambda: __import__(
                "services.scanner_service", fromlist=["scan_all_channels"]
            ).scan_all_channels(),
            hour=6,
            minute=0,
            on_complete=lambda _: self._digest._refresh_table(),
        )

    def _on_schedule_changed(self, hour: int, minute: int):
        update_schedule(hour, minute)

    def _on_feed_videos(self, videos: list[dict]):
        """Feed harvest results → switch to digest tab."""
        self._switch("digest")

    def closeEvent(self, event):
        from services.scheduler_service import stop
        stop()
        super().closeEvent(event)
