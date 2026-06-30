"""
Keyword Experiments Tab - Track and learn from keyword performance.
US-001 Implementation.
"""
from uuid import uuid4
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QLabel, QGroupBox,
    QTextEdit, QSpinBox, QDoubleSpinBox, QRadioButton,
    QMessageBox, QDialog, QComboBox, QLineEdit, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from database.db import get_connection
from models import compute_actual_score, classify_outcome, compute_accuracy
from agents.learn_agent import analyze_keyword_experiments, suggest_scoring_adjustments
from agents.evaluate_agent import evaluate_keyword
from utils.logger import get_logger

log = get_logger("ui.keyword_exp")

class KeywordExperimentsTab(QWidget):
    """Main tab for keyword experiment tracking."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.check_pending_reminders()
        self.load_experiments()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Keyword Experiments - Track Real Performance")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8; padding: 8px 0;")
        layout.addWidget(header)
        
        # Reminder Banner
        self.reminder_banner = QLabel()
        self.reminder_banner.setStyleSheet("""
            background-color: #fbbf24; color: #78350f; padding: 12px;
            border-radius: 6px; font-weight: bold;
        """)
        self.reminder_banner.hide()
        layout.addWidget(self.reminder_banner)
        
        # Action Buttons
        actions = QHBoxLayout()
        actions.setSpacing(8)
        
        self.btn_start = QPushButton("Start New Experiment")
        self.btn_start.clicked.connect(self.start_experiment_dialog)
        self.btn_start.setStyleSheet("background: #10b981; color: white; padding: 8px 16px; border-radius: 4px;")
        actions.addWidget(self.btn_start)
        
        self.btn_report = QPushButton("Report Results")
        self.btn_report.clicked.connect(self.report_results_dialog)
        self.btn_report.setStyleSheet("background: #3b82f6; color: white; padding: 8px 16px; border-radius: 4px;")
        actions.addWidget(self.btn_report)
        
        self.btn_insights = QPushButton("View Learning Insights")
        self.btn_insights.clicked.connect(self.show_insights)
        self.btn_insights.setStyleSheet("background: #8b5cf6; color: white; padding: 8px 16px; border-radius: 4px;")
        actions.addWidget(self.btn_insights)
        
        actions.addStretch()
        layout.addLayout(actions)
        
        # Stats Summary
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.stats_label)
        
        # Experiments Table
        table_frame = QFrame()
        table_frame.setStyleSheet("background: #0f172a; border-radius: 6px;")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(8, 8, 8, 8)
        
        table_label = QLabel("Experiments")
        table_label.setStyleSheet("color: #cbd5e1; font-weight: bold;")
        table_layout.addWidget(table_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Keyword", "Channel", "Predicted", "Actual", "Status", "Accuracy", "Rating", "Days"
        ])
        self.table.setStyleSheet("QTableWidget { background: #0f172a; color: #f1f5f9; gridline-color: #1e293b; }")
        table_layout.addWidget(self.table)
        layout.addWidget(table_frame)
        
        self.setLayout(layout)
    
    def check_pending_reminders(self):
        conn = get_connection()
        pending = conn.execute("""
            SELECT COUNT(*) as count FROM keyword_experiments
            WHERE test_status = 'in_progress'
            AND julianday('now') - julianday(created_at) >= 7
        """).fetchone()
        conn.close()
        
        if pending and pending['count'] > 0:
            self.reminder_banner.setText(f"{pending['count']} experiment(s) ready to report (7+ days old)")
            self.reminder_banner.show()
        else:
            self.reminder_banner.hide()
    
    def load_experiments(self):
        conn = get_connection()
        rows = conn.execute("""
            SELECT e.*, c.name as channel_name
            FROM keyword_experiments e
            LEFT JOIN channels c ON e.channel_id = c.id
            ORDER BY e.created_at DESC
            LIMIT 100
        """).fetchall()
        conn.close()
        
        self.table.setRowCount(len(rows))
        
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(row['keyword']))
            channel_name = row['channel_name'] or row.get('account_label') or '-'
            self.table.setItem(i, 1, QTableWidgetItem(channel_name))
            self.table.setItem(i, 2, QTableWidgetItem(str(row['predicted_score'])))
            self.table.setItem(i, 3, QTableWidgetItem(str(row['actual_score'] or '-')))
            
            status = row['test_status']
            status_item = QTableWidgetItem(status)
            if status == 'success': status_item.setForeground(Qt.GlobalColor.green)
            elif status == 'failed': status_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(i, 4, status_item)
            
            acc = row['accuracy']
            self.table.setItem(i, 5, QTableWidgetItem(f"{acc*100:.0f}%" if acc else '-'))
            
            rating = row['user_rating']
            self.table.setItem(i, 6, QTableWidgetItem('⭐' * rating if rating else '-'))
            
            if row['created_at']:
                from datetime import datetime
                created = datetime.fromisoformat(row['created_at'].split('+')[0])
                days_old = (datetime.now() - created).days
                self.table.setItem(i, 7, QTableWidgetItem(str(days_old)))
            else:
                self.table.setItem(i, 7, QTableWidgetItem('-'))
        
        completed = [r for r in rows if r['test_status'] in ('success', 'failed', 'partial')]
        if completed:
            avg_acc = sum(r['accuracy'] for r in completed if r['accuracy']) / len(completed)
            success_rate = len([r for r in completed if r['test_status'] == 'success']) / len(completed)
            self.stats_label.setText(f"Total: {len(rows)} | Completed: {len(completed)} | "
                                    f"Success: {success_rate*100:.0f}% | Acc: {avg_acc*100:.0f}%")
    
    def start_experiment_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Start Keyword Experiment")
        dialog.resize(500, 350)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Keyword:"))
        keyword_input = QLineEdit()
        layout.addWidget(keyword_input)
        
        layout.addWidget(QLabel("Channel:"))
        channel_combo = QComboBox()
        conn = get_connection()
        channels = conn.execute("SELECT id, name, subscribers, avg_views FROM channels").fetchall()
        for ch in channels:
            channel_combo.addItem(f"{ch['name']} ({ch['subscribers']} subs)", ch['id'])
        conn.close()
        layout.addWidget(channel_combo)
        
        layout.addWidget(QLabel("Account Label (optional):"))
        account_label_input = QLineEdit()
        layout.addWidget(account_label_input)
        
        source_group = QGroupBox("Source")
        source_layout = QHBoxLayout()
        source_agent = QRadioButton("Agent Suggested")
        source_manual = QRadioButton("Manual Entry")
        source_manual.setChecked(True)
        source_layout.addWidget(source_agent)
        source_layout.addWidget(source_manual)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        agent_score_layout = QHBoxLayout()
        agent_score_layout.addWidget(QLabel("Agent Score:"))
        agent_score_input = QSpinBox()
        agent_score_input.setRange(0, 100)
        agent_score_input.setValue(50)
        agent_score_input.setEnabled(False)
        agent_score_layout.addWidget(agent_score_input)
        agent_score_layout.addStretch()
        layout.addLayout(agent_score_layout)
        
        source_agent.toggled.connect(lambda checked: agent_score_input.setEnabled(checked))
        
        btn_layout = QHBoxLayout()
        btn_start = QPushButton("Start")
        btn_cancel = QPushButton("Cancel")
        btn_start.setStyleSheet("background: #10b981; color: white; padding: 8px 16px; border-radius: 4px;")
        btn_cancel.setStyleSheet("background: #64748b; color: white; padding: 8px 16px; border-radius: 4px;")
        btn_layout.addWidget(btn_start)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        
        def on_start():
            keyword = keyword_input.text().strip()
            if not keyword:
                QMessageBox.warning(dialog, "Error", "Please enter a keyword")
                return
            
            channel_id = channel_combo.currentData()
            account_label = account_label_input.text().strip() or None
            suggestion_source = 'agent_suggested' if source_agent.isChecked() else 'user_manual'
            agent_score = agent_score_input.value() if source_agent.isChecked() else None
            
            conn = get_connection()
            channel = next((ch for ch in channels if ch['id'] == channel_id), None)
            if not channel:
                conn.close()
                QMessageBox.warning(dialog, "Error", "Selected channel not found")
                return
            
            prediction = evaluate_keyword(keyword, channel_id)
            exp_id = str(uuid4())
            conn.execute("""
                INSERT INTO keyword_experiments 
                (id, keyword, channel_id, channel_subscribers, creator_avg_views,
                 account_label, suggestion_source, agent_suggested_score,
                 predicted_score, prediction_reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exp_id, keyword, channel_id,
                channel['subscribers'], channel['avg_views'],
                account_label, suggestion_source, agent_score,
                prediction['score'], prediction['reasoning']
            ))
            conn.commit()
            conn.close()
            
            dialog.accept()
            self.load_experiments()
            QMessageBox.information(self, "Success", "Experiment started!")
        
        btn_start.clicked.connect(on_start)
        btn_cancel.clicked.connect(dialog.reject)
        dialog.exec()
    
    def report_results_dialog(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Error", "Select an experiment first")
            return
        
        exp_id = self.table.item(selected, 0).data(Qt.ItemDataRole.UserRole)
        conn = get_connection()
        exp = conn.execute("SELECT * FROM keyword_experiments WHERE id = ?", (exp_id,)).fetchone()
        conn.close()
        
        if not exp or exp['test_status'] != 'in_progress':
            QMessageBox.warning(self, "Error", "Experiment not found or already completed")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Report: {exp['keyword']}")
        dialog.resize(500, 450)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Status:"))
        status_group = QHBoxLayout()
        status_success = QRadioButton("Success")
        status_partial = QRadioButton("Partial")
        status_failed = QRadioButton("Failed")
        status_success.setChecked(True)
        status_group.addWidget(status_success)
        status_group.addWidget(status_partial)
        status_group.addWidget(status_failed)
        layout.addLayout(status_group)
        
        layout.addWidget(QLabel("Views:"))
        views_input = QSpinBox()
        views_input.setRange(0, 10000000)
        views_input.setValue(exp.get('actual_views', 0) or 0)
        layout.addWidget(views_input)
        
        layout.addWidget(QLabel("Engagement %:"))
        engagement_input = QDoubleSpinBox()
        engagement_input.setRange(0, 100)
        engagement_input.setValue(exp.get('actual_engagement', 0) or 0)
        layout.addWidget(engagement_input)
        
        layout.addWidget(QLabel("Rating:"))
        rating_input = QSpinBox()
        rating_input.setRange(1, 5)
        rating_input.setValue(3)
        layout.addWidget(rating_input)
        
        btn_layout = QHBoxLayout()
        btn_submit = QPushButton("Submit")
        btn_cancel = QPushButton("Cancel")
        btn_submit.setStyleSheet("background: #10b981; color: white; padding: 8px 16px; border-radius: 4px;")
        btn_cancel.setStyleSheet("background: #64748b; color: white; padding: 8px 16px; border-radius: 4px;")
        btn_layout.addWidget(btn_submit)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        
        def on_submit():
            test_status = 'success' if status_success.isChecked() else 'partial' if status_partial.isChecked() else 'failed'
            actual_views = views_input.value()
            actual_engagement = engagement_input.value()
            user_rating = rating_input.value()
            
            creator_avg_views = exp['creator_avg_views'] or 2000
            actual_score = compute_actual_score(actual_views, creator_avg_views, actual_engagement)
            accuracy = compute_accuracy(exp['predicted_score'], actual_score)
            outcome_type = classify_outcome(exp['predicted_score'], test_status)
            
            conn = get_connection()
            conn.execute("""
                UPDATE keyword_experiments
                SET actual_views = ?, actual_engagement = ?, actual_score = ?,
                    views_vs_baseline = ?, test_status = ?, user_rating = ?,
                    accuracy = ?, outcome_type = ?, reported_at = datetime('now')
                WHERE id = ?
            """, (actual_views, actual_engagement, actual_score,
                  actual_views / creator_avg_views, test_status, user_rating,
                  accuracy, outcome_type, exp_id))
            conn.commit()
            conn.close()
            
            dialog.accept()
            self.load_experiments()
            QMessageBox.information(self, "Success", f"Reported! Accuracy: {accuracy*100:.1f}%, Outcome: {outcome_type}")
        
        btn_submit.clicked.connect(on_submit)
        btn_cancel.clicked.connect(dialog.reject)
        dialog.exec()
    
    def show_insights(self):
        analysis = analyze_keyword_experiments()
        
        if analysis['status'] == 'insufficient_data':
            QMessageBox.information(self, "Insufficient Data",
                f"Need 5+ experiments. Current: {analysis['stats']['total']}")
            return
        
        suggestions = suggest_scoring_adjustments(analysis['patterns'])
        dialog = LearningInsightsDialog(analysis, suggestions, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            from agents.learn_agent import apply_approved_adjustments
            apply_approved_adjustments(suggestions['weight_adjustments'])
            QMessageBox.information(self, "Applied", "Scoring weights updated!")


class LearningInsightsDialog(QDialog):
    def __init__(self, analysis: dict, suggestions: dict, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.suggestions = suggestions
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        stats = self.analysis['stats']
        stats_html = f"""
<h2>Overall Performance</h2>
<ul>
<li>Total: {stats['total']}</li>
<li>True Positives: {stats['true_positives']}</li>
<li>False Positives: {stats['false_positives']}</li>
<li>False Negatives: {stats['false_negatives']}</li>
<li>Avg Accuracy: {stats['avg_accuracy']*100:.1f}%</li>
</ul>
"""
        stats_label = QLabel(stats_html)
        stats_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(stats_label)
        
        patterns_html = "<h2>Patterns Discovered</h2><ul>"
        for p in self.analysis['patterns']:
            patterns_html += f"<li><strong>{p['trait']}</strong> ({p['outcome_type']}): {p['count']} occ, conf: {p['confidence']*100:.0f}%</li>"
        patterns_html += "</ul>"
        patterns_label = QLabel(patterns_html)
        patterns_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(patterns_label)
        
        if self.suggestions['weight_adjustments']:
            sug_html = "<h2>Suggested Adjustments (Requires Approval)</h2><ul>"
            for r in self.suggestions['reasoning']:
                sug_html += f"<li>{r}</li>"
            sug_html += "</ul><h4>Weight Changes:</h4><ul>"
            for k, v in self.suggestions['weight_adjustments'].items():
                sug_html += f"<li>{k}: {v:.2f}</li>"
            sug_html += "</ul>"
            
            sug_label = QLabel(sug_html)
            sug_label.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(sug_label)
            
            btn_layout = QHBoxLayout()
            btn_approve = QPushButton("Approve & Apply")
            btn_reject = QPushButton("Reject")
            btn_approve.setStyleSheet("background: #10b981; color: white; padding: 8px 16px; border-radius: 4px;")
            btn_reject.setStyleSheet("background: #64748b; color: white; padding: 8px 16px; border-radius: 4px;")
            btn_approve.clicked.connect(self.accept)
            btn_reject.clicked.connect(self.reject)
            btn_layout.addWidget(btn_approve)
            btn_layout.addWidget(btn_reject)
            layout.addLayout(btn_layout)
        else:
            no_sug = QLabel("No adjustments needed.")
            no_sug.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(no_sug)
            
            btn_close = QPushButton("Close")
            btn_close.clicked.connect(self.reject)
            layout.addWidget(btn_close)
        
        self.setLayout(layout)
        self.setWindowTitle("Learning Insights")
        self.resize(600, 500)
