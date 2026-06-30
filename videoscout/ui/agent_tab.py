"""
Agent Tab — UI for Agentic Loop control and results.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QMessageBox, QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import json
from datetime import datetime
from agents import orchestrator
from utils.logger import get_logger

log = get_logger("agent_ui")


class AgentLoopThread(QThread):
    """Background thread for running agent loop."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, loop_type="discovery", auto_follow=10):
        super().__init__()
        self.loop_type = loop_type
        self.auto_follow = auto_follow
    
    def run(self):
        try:
            if self.loop_type == "discovery":
                result = orchestrator.run_discovery_cycle(auto_follow_top_n=self.auto_follow)
            elif self.loop_type == "learning":
                result = orchestrator.run_learning_cycle()
            else:
                result = orchestrator.run_full_loop(auto_follow_top_n=self.auto_follow)
            self.finished.emit(result)
        except Exception as e:
            log.error(f"Agent loop error: {e}", exc_info=True)
            self.error.emit(str(e))


class AgentTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._thread = None
        self._last_learning_result = None
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QLabel("🤖 Agentic Loop")
        header.setFont(QFont("", 20, QFont.Weight.Bold))
        header.setStyleSheet("color:#38bdf8;")
        layout.addWidget(header)
        
        desc = QLabel("Discover → Evaluate → Learn workflow with LLM-powered channel assessment")
        desc.setStyleSheet("color:#94a3b8; font-size:13px;")
        layout.addWidget(desc)
        
        # Controls
        controls = self._build_controls()
        layout.addWidget(controls)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { border: 1px solid #334155; border-radius: 4px; text-align: center; }
            QProgressBar::chunk { background: #38bdf8; }
        """)
        layout.addWidget(self.progress)
        
        # Results
        results = self._build_results()
        layout.addWidget(results, 1)
    
    def _build_controls(self) -> QWidget:
        group = QGroupBox("Controls")
        group.setStyleSheet("QGroupBox { font-weight: bold; color:#f1f5f9; }")
        layout = QHBoxLayout(group)
        
        self.btn_discovery = QPushButton("🔍 Run Discovery")
        self.btn_discovery.clicked.connect(lambda: self._run_loop("discovery"))
        
        self.btn_learning = QPushButton("📊 Run Learning")
        self.btn_learning.clicked.connect(lambda: self._run_loop("learning"))
        
        self.btn_full = QPushButton("🔄 Run Full Loop")
        self.btn_full.clicked.connect(lambda: self._run_loop("full"))

        self.btn_approve = QPushButton("✅ Approve Suggestions")
        self.btn_approve.clicked.connect(self._approve_suggestions)
        self.btn_approve.setVisible(False)

        for btn in [self.btn_discovery, self.btn_learning, self.btn_full]:
            btn.setStyleSheet("""
                QPushButton {
                    background: #334155; color: #f1f5f9; border: none;
                    padding: 8px 16px; border-radius: 4px; font-size: 13px;
                }
                QPushButton:hover { background: #475569; }
                QPushButton:disabled { background: #1e293b; color: #64748b; }
            """)
            layout.addWidget(btn)

        self.btn_approve.setStyleSheet("""
            QPushButton {
                background: #16a34a; color: #f1f5f9; border: none;
                padding: 8px 16px; border-radius: 4px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #15803d; }
        """)
        layout.addWidget(self.btn_approve)

        layout.addStretch()
        return group
    
    def _build_results(self) -> QWidget:
        group = QGroupBox("Results")
        group.setStyleSheet("QGroupBox { font-weight: bold; color:#f1f5f9; }")
        layout = QVBoxLayout(group)
        
        # Summary
        self.summary = QLabel("No results yet")
        self.summary.setStyleSheet("color:#94a3b8; font-size:13px; padding:8px;")
        layout.addWidget(self.summary)
        
        # Details
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setStyleSheet("""
            QTextEdit {
                background: #0f172a; color: #cbd5e1; border: 1px solid #334155;
                border-radius: 4px; padding: 8px; font-family: monospace; font-size: 12px;
            }
        """)
        layout.addWidget(self.details)
        
        return group
    
    def _run_loop(self, loop_type: str):
        if self._thread and self._thread.isRunning():
            QMessageBox.warning(self, "Busy", "Agent loop already running")
            return
        
        self._set_buttons_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # indeterminate
        self.summary.setText(f"Running {loop_type} cycle...")
        
        self._thread = AgentLoopThread(loop_type=loop_type, auto_follow=10)
        self._thread.finished.connect(self._on_loop_finished)
        self._thread.error.connect(self._on_loop_error)
        self._thread.start()
    
    def _on_loop_finished(self, result: dict):
        self._set_buttons_enabled(True)
        self.progress.setVisible(False)
        
        # Format summary
        if "discovery" in result:
            d = result["discovery"]
            summary = (
                f"✅ Discovery: {d['discovered']} found, "
                f"{d['evaluated']} evaluated, "
                f"{d['recommended']} recommended, "
                f"{d['auto_followed']} auto-followed"
            )
            self.btn_approve.setVisible(False)
        elif "analysis" in result:
            n_success = len(result['analysis'].get('successful_channels', []))
            suggestions = result.get("suggestions", {})
            n_kw = len(suggestions.get("keyword_suggestions", []))
            summary = f"✅ Learning: {n_success} successful channels, {n_kw} keyword suggestions"
            self._last_learning_result = result
            self.btn_approve.setVisible(n_kw > 0 or suggestions.get("filter_adjustments"))
        else:
            summary = f"✅ Completed at {result.get('timestamp', 'unknown')}"
            self.btn_approve.setVisible(False)

        self.summary.setText(summary)
        
        # Show details
        details = json.dumps(result, indent=2, ensure_ascii=False)
        self.details.setText(details)
        
        log.info(f"Agent loop finished: {summary}")
    
    def _on_loop_error(self, error: str):
        self._set_buttons_enabled(True)
        self.progress.setVisible(False)
        self.summary.setText(f"❌ Error: {error}")
        QMessageBox.critical(self, "Agent Error", f"Loop failed:\n{error}")
    
    def _approve_suggestions(self):
        if not self._last_learning_result:
            return
        suggestions = self._last_learning_result.get("suggestions", {})
        approved = {}
        kw = suggestions.get("keyword_suggestions", [])
        if kw:
            approved["keywords"] = kw
        filters = suggestions.get("filter_adjustments", {})
        if filters:
            approved["filters"] = filters

        if not approved:
            QMessageBox.information(self, "Nothing to approve", "No suggestions to apply.")
            return

        try:
            orchestrator.apply_learning_suggestions(approved)
            kw_list = "\n".join(f"  + {k}" for k in kw)
            msg = f"Strategy updated!\n\nKeywords added:\n{kw_list}"
            if filters:
                msg += f"\n\nFilters updated:\n{json.dumps(filters, indent=2)}"
            QMessageBox.information(self, "✅ Approved", msg)
            self.btn_approve.setVisible(False)
            self._last_learning_result = None
            log.info(f"Suggestions approved: {approved}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply suggestions:\n{e}")

    def _set_buttons_enabled(self, enabled: bool):
        self.btn_discovery.setEnabled(enabled)
        self.btn_learning.setEnabled(enabled)
        self.btn_full.setEnabled(enabled)
