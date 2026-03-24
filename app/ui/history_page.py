"""
Aurion Markets — History Page
Track record of past signals with performance metrics.
"""

import json
import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QSizePolicy, QHeaderView,
    QTableWidget, QTableWidgetItem, QAbstractItemView
)
from PySide6.QtCore import Qt

from ui.theme import Colors, Fonts, Radius, Spacing
from ui.widgets import Card, MetricCard, SectionHeader, Divider, GlowButton, SignalBadge

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "signal_history.json")


def load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history: list):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def add_signal_to_history(signal: dict):
    history = load_history()
    record = {
        "timestamp": datetime.now().isoformat(),
        "name": signal.get("name", "Unknown"),
        "symbol": signal.get("symbol", ""),
        "signal": signal.get("signal", "NEUTRAL"),
        "confidence": signal.get("confidence", 0),
        "entry": signal.get("entry", 0),
        "stop_loss": signal.get("stop_loss", 0),
        "take_profit": signal.get("take_profit", 0),
        "risk_reward": signal.get("risk_reward", 0),
        "outcome": "pending",  # pending, win, loss
    }
    history.insert(0, record)
    # Keep last 500
    history = history[:500]
    save_history(history)


class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)
        scroll.setWidget(container)

        # Header
        header_row = QHBoxLayout()
        header_row.addWidget(SectionHeader(
            "Signal History",
            "Complete track record of AI-generated trading signals"
        ))
        header_row.addStretch()

        refresh_btn = GlowButton("  Refresh  ")
        refresh_btn.clicked.connect(self._refresh)
        header_row.addWidget(refresh_btn)

        layout.addLayout(header_row)

        # Stats Row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        self._total_card = MetricCard("Total Signals", "0")
        self._win_card = MetricCard("Wins", "0", "0%", True)
        self._loss_card = MetricCard("Losses", "0", "0%", False)
        self._pending_card = MetricCard("Pending", "0")

        for card in [self._total_card, self._win_card, self._loss_card, self._pending_card]:
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            stats_row.addWidget(card)

        layout.addLayout(stats_row)

        # Table
        table_card = Card()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "Time", "Asset", "Signal", "Confidence", "Entry", "Stop Loss", "Target", "R:R"
        ])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)

        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: {Colors.BG_CARD};
                border: none;
                gridline-color: {Colors.BORDER};
                font-size: {Fonts.SIZE_SM}px;
            }}
            QTableWidget::item {{
                padding: 10px 14px;
                border-bottom: 1px solid {Colors.BORDER};
            }}
            QTableWidget::item:selected {{
                background: {Colors.BG_ELEVATED};
            }}
            QTableWidget::item:alternate {{
                background: {Colors.BG_SECONDARY};
            }}
            QHeaderView::section {{
                background: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_XS}px;
                font-weight: 700;
                letter-spacing: 1px;
                text-transform: uppercase;
                padding: 12px 14px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """)

        table_layout.addWidget(self._table)
        layout.addWidget(table_card, 1)

        # Empty state
        self._empty = QLabel("No signals in history yet.\nUse Market Analysis or Signals to generate predictions — they'll appear here automatically.")
        self._empty.setAlignment(Qt.AlignCenter)
        self._empty.setStyleSheet(f"""
            font-size: {Fonts.SIZE_BASE}px;
            color: {Colors.TEXT_MUTED};
            padding: 60px;
        """)
        layout.addWidget(self._empty)

        layout.addStretch()

    def _refresh(self):
        history = load_history()

        # Update stats
        total = len(history)
        wins = sum(1 for h in history if h.get("outcome") == "win")
        losses = sum(1 for h in history if h.get("outcome") == "loss")
        pending = sum(1 for h in history if h.get("outcome") == "pending")

        self._total_card.set_value(str(total))
        self._win_card.set_value(str(wins), f"{wins/total*100:.0f}%" if total else "0%", True)
        self._loss_card.set_value(str(losses), f"{losses/total*100:.0f}%" if total else "0%", False)
        self._pending_card.set_value(str(pending))

        if not history:
            self._table.setVisible(False)
            self._empty.setVisible(True)
            return

        self._table.setVisible(True)
        self._empty.setVisible(False)

        self._table.setRowCount(len(history))
        for row, record in enumerate(history):
            fmt = lambda v: f"{v:,.5f}" if isinstance(v, (int, float)) and abs(v) < 100 else f"{v:,.2f}" if isinstance(v, (int, float)) else str(v)

            # Time
            try:
                dt = datetime.fromisoformat(record["timestamp"])
                time_str = dt.strftime("%b %d, %H:%M")
            except Exception:
                time_str = record.get("timestamp", "—")

            items = [
                time_str,
                record.get("name", "—"),
                record.get("signal", "—"),
                f"{record.get('confidence', 0):.0%}",
                fmt(record.get("entry", 0)),
                fmt(record.get("stop_loss", 0)),
                fmt(record.get("take_profit", 0)),
                f"{record.get('risk_reward', 0)}:1",
            ]

            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)

                # Color the signal column
                if col == 2:
                    if text == "BUY":
                        item.setForeground(Qt.GlobalColor(Qt.green))
                    elif text == "SELL":
                        item.setForeground(Qt.GlobalColor(Qt.red))
                # Color confidence
                elif col == 3:
                    conf = record.get("confidence", 0)
                    if conf > 0.6:
                        item.setForeground(Qt.GlobalColor(Qt.green))
                    elif conf > 0.3:
                        item.setForeground(Qt.GlobalColor(Qt.yellow))

                self._table.setItem(row, col, item)
