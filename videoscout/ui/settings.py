import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QPushButton, QLabel, QMessageBox, QGroupBox,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

ENV_PATH = Path(__file__).parent.parent / ".env"

def _read_env() -> dict:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def _write_env(data: dict):
    lines = [f"{k}={v}" for k, v in data.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n")

class Settings(QWidget):
    schedule_changed = None  # set by MainWindow

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("Settings")
        title.setFont(QFont("", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        # ========== YouTube API Section ==========
        yt_group = QGroupBox("YouTube API")
        yt_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        yt_form = QFormLayout(yt_group)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("YouTube Data API v3 key")
        yt_form.addRow("API Key:", self.api_key_input)

        layout.addWidget(yt_group)

        # ========== LLM Configuration Section ==========
        llm_group = QGroupBox("LLM Configuration (for AI Agent)")
        llm_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        llm_form = QFormLayout(llm_group)

        self.llm_base_url = QLineEdit()
        self.llm_base_url.setPlaceholderText("http://localhost:20128/v1")
        llm_form.addRow("Base URL:", self.llm_base_url)

        self.llm_api_key = QLineEdit()
        self.llm_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.llm_api_key.setPlaceholderText("sk-xxxxx")
        llm_form.addRow("API Key:", self.llm_api_key)

        self.llm_model = QLineEdit()
        self.llm_model.setPlaceholderText("gpt-4o-mini")
        llm_form.addRow("Model:", self.llm_model)

        layout.addWidget(llm_group)

        # ========== Scanning Configuration Section ==========
        scan_group = QGroupBox("Scanning Configuration")
        scan_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        scan_form = QFormLayout(scan_group)

        self.scan_hour = QSpinBox()
        self.scan_hour.setRange(0, 23)
        self.scan_hour.setValue(6)
        scan_form.addRow("Auto-scan hour (0-23):", self.scan_hour)

        self.scan_minute = QSpinBox()
        self.scan_minute.setRange(0, 59)
        self.scan_minute.setValue(0)
        scan_form.addRow("Auto-scan minute:", self.scan_minute)

        layout.addWidget(scan_group)

        # ========== Filter Configuration Section ==========
        filter_group = QGroupBox("Video Filters")
        filter_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        filter_form = QFormLayout(filter_group)

        self.view_min = QSpinBox()
        self.view_min.setRange(0, 10_000_000)
        self.view_min.setSingleStep(10_000)
        self.view_min.setValue(150_000)
        filter_form.addRow("Min views:", self.view_min)

        self.view_max = QSpinBox()
        self.view_max.setRange(0, 10_000_000)
        self.view_max.setSingleStep(10_000)
        self.view_max.setValue(200_000)
        filter_form.addRow("Max views:", self.view_max)

        self.max_subs = QSpinBox()
        self.max_subs.setRange(0, 10_000_000)
        self.max_subs.setSingleStep(1_000)
        self.max_subs.setValue(50_000)
        filter_form.addRow("Max channel subs:", self.max_subs)

        self.days = QSpinBox()
        self.days.setRange(1, 90)
        self.days.setValue(30)
        filter_form.addRow("Uploaded within (days):", self.days)

        layout.addWidget(filter_group)

        # ========== Save Button ==========
        save_btn = QPushButton("💾 Save All Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #38bdf8;
                color: #0f172a;
                padding: 10px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #0ea5e9;
            }
        """)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #4ade80; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()

    def _load(self):
        env = _read_env()
        
        # YouTube
        self.api_key_input.setText(env.get("YOUTUBE_API_KEY", ""))
        
        # LLM
        self.llm_base_url.setText(env.get("LLM_BASE_URL", "http://localhost:20128/v1"))
        self.llm_api_key.setText(env.get("LLM_API_KEY", "sk-local"))
        self.llm_model.setText(env.get("LLM_MODEL", "gpt-4o-mini"))
        
        # Scanning
        self.scan_hour.setValue(int(env.get("SCAN_HOUR", 6)))
        self.scan_minute.setValue(int(env.get("SCAN_MINUTE", 0)))
        
        # Filters
        self.view_min.setValue(int(env.get("VIEW_MIN", 150_000)))
        self.view_max.setValue(int(env.get("VIEW_MAX", 200_000)))
        self.max_subs.setValue(int(env.get("MAX_SUBS", 50_000)))
        self.days.setValue(int(env.get("DAYS", 30)))

    def _save(self):
        data = {
            # YouTube
            "YOUTUBE_API_KEY": self.api_key_input.text().strip(),
            
            # LLM
            "LLM_BASE_URL": self.llm_base_url.text().strip(),
            "LLM_API_KEY": self.llm_api_key.text().strip(),
            "LLM_MODEL": self.llm_model.text().strip(),
            
            # Scanning
            "SCAN_HOUR": str(self.scan_hour.value()),
            "SCAN_MINUTE": str(self.scan_minute.value()),
            
            # Filters
            "VIEW_MIN": str(self.view_min.value()),
            "VIEW_MAX": str(self.view_max.value()),
            "MAX_SUBS": str(self.max_subs.value()),
            "DAYS": str(self.days.value()),
        }
        
        _write_env(data)
        
        # Update environment variables for current process
        for k, v in data.items():
            os.environ[k] = v
        
        self.status_label.setText("✅ Settings saved successfully!")
        
        if self.schedule_changed:
            self.schedule_changed(self.scan_hour.value(), self.scan_minute.value())

    def get_filter_config(self) -> dict:
        return {
            "view_min": self.view_min.value(),
            "view_max": self.view_max.value(),
            "max_subs": self.max_subs.value(),
            "days": self.days.value(),
        }
