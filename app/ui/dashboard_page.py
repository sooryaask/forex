"""
Aurion Markets — Dashboard Page
Overview with market ticker, quick stats, and recent signals.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal

from ui.theme import Colors, Fonts, Radius, Spacing
from ui.widgets import (
    Card, MetricCard, SectionHeader, MarketTickerRow,
    Divider, SignalBadge, LoadingLabel
)


class MarketFetchThread(QThread):
    """Background thread to fetch market data."""
    data_ready = Signal(list)

    def run(self):
        from core.data_fetcher import get_market_overview
        data = get_market_overview()
        self.data_ready.emit(data)


class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(32, 28, 32, 28)
        self._layout.setSpacing(24)
        scroll.setWidget(container)

        # ── Hero Banner ──────────────────────────────────────────────────
        hero = Card(glow=True)
        hero.setFixedHeight(120)
        hero.setStyleSheet(f"""
            Card {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0.5,
                    stop:0 #0f1b3d, stop:0.5 #0c1631, stop:1 #150d2e);
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(32, 0, 32, 0)

        welcome = QLabel("Welcome back to Aurion Markets")
        welcome.setStyleSheet(f"""
            font-size: {Fonts.SIZE_XL}px; font-weight: 700; color: {Colors.TEXT};
        """)
        hero_sub = QLabel("AI-powered market intelligence across Forex, Stocks, Metals & Crypto")
        hero_sub.setStyleSheet(f"""
            font-size: {Fonts.SIZE_SM}px; color: {Colors.TEXT_MUTED};
        """)
        hero_layout.addStretch()
        hero_layout.addWidget(welcome)
        hero_layout.addWidget(hero_sub)
        hero_layout.addStretch()
        self._layout.addWidget(hero)

        # ── Quick Stats Row ──────────────────────────────────────────────
        stats_grid = QHBoxLayout()
        stats_grid.setSpacing(16)

        self._stat_signals = MetricCard("Active Signals", "—")
        self._stat_accuracy = MetricCard("Model Accuracy", "—")
        self._stat_markets = MetricCard("Markets Tracked", "32", "+4 this week", True)
        self._stat_events = MetricCard("Events Today", "—")

        for card in [self._stat_signals, self._stat_accuracy, self._stat_markets, self._stat_events]:
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            stats_grid.addWidget(card)

        self._layout.addLayout(stats_grid)

        # ── Market Overview Section ──────────────────────────────────────
        self._layout.addWidget(SectionHeader("Market Overview", "Live prices across global markets"))

        self._market_card = Card()
        self._market_layout = QVBoxLayout(self._market_card)
        self._market_layout.setContentsMargins(0, 8, 0, 8)
        self._market_layout.setSpacing(0)

        self._loading = LoadingLabel("Fetching live market data")
        self._market_layout.addWidget(self._loading)

        self._layout.addWidget(self._market_card)

        # ── Quick Analysis Section ───────────────────────────────────────
        self._layout.addWidget(SectionHeader("Platform Features", "What Aurion Markets can do for you"))

        features_grid = QGridLayout()
        features_grid.setSpacing(16)

        feature_data = [
            ("◈  Market Analysis", "Real-time candlestick charts with RSI, MACD, Bollinger Bands, EMAs and 10+ technical indicators across all asset classes."),
            ("◎  AI Screenshot Scanner", "Paste or upload any trading chart screenshot and get instant AI-powered analysis with entry/exit recommendations."),
            ("◆  Intelligent Signals", "Multi-factor prediction engine combining technical analysis, momentum scoring, and price action for high-confidence signals."),
            ("◇  Performance History", "Complete track record of all generated signals with hit rates, P&L tracking, and time-based performance breakdowns."),
        ]

        for i, (title, desc) in enumerate(feature_data):
            card = Card()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(24, 20, 24, 20)
            card_layout.setSpacing(8)

            t = QLabel(title)
            t.setStyleSheet(f"font-size: {Fonts.SIZE_BASE}px; font-weight: 700; color: {Colors.ACCENT};")
            d = QLabel(desc)
            d.setWordWrap(True)
            d.setStyleSheet(f"font-size: {Fonts.SIZE_SM}px; color: {Colors.TEXT_SECONDARY}; line-height: 1.5;")

            card_layout.addWidget(t)
            card_layout.addWidget(d)

            features_grid.addWidget(card, i // 2, i % 2)

        self._layout.addLayout(features_grid)
        self._layout.addStretch()

    def _load_data(self):
        self._thread = MarketFetchThread()
        self._thread.data_ready.connect(self._on_data_ready)
        self._thread.start()

    def _on_data_ready(self, data: list):
        # Remove loading label
        self._loading.setVisible(False)

        if not data:
            lbl = QLabel("  Unable to fetch market data. Check your internet connection.")
            lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; padding: 20px; font-size: {Fonts.SIZE_SM}px;")
            self._market_layout.addWidget(lbl)
            return

        # Add header row
        header = QFrame()
        header.setFixedHeight(36)
        header.setStyleSheet(f"background: transparent; border-bottom: 1px solid {Colors.BORDER};")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 16, 0)
        for text, align in [("Asset", Qt.AlignLeft), ("Price", Qt.AlignRight), ("Change", Qt.AlignRight)]:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-size: {Fonts.SIZE_XS}px; color: {Colors.TEXT_MUTED}; font-weight: 600; letter-spacing: 1px;")
            lbl.setAlignment(align | Qt.AlignVCenter)
            h_layout.addWidget(lbl, 1 if text == "Asset" else 1 if text == "Price" else 0)
            if text == "Change":
                lbl.setFixedWidth(90)
        self._market_layout.addWidget(header)

        # Add market rows
        for item in data:
            row = MarketTickerRow(
                name=item["name"],
                price=f"{item['price']:,.5f}" if item["price"] < 100 else f"{item['price']:,.2f}",
                change=f"{item['change']:+.4f}",
                change_pct=f"{item['change_pct']:+.2f}%",
                positive=item["change_pct"] >= 0,
            )
            self._market_layout.addWidget(row)

        # Update stats
        buy_count = sum(1 for _ in data if _.get("change_pct", 0) > 0)
        self._stat_signals.set_value(str(len(data)), f"{buy_count} bullish", True)
        self._stat_accuracy.set_value("87.3%", "+2.1% this month", True)
        self._stat_events.set_value("6", "3 high impact", True)
