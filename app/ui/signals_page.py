"""
Aurion Markets — Signals Page
Generate and display AI trading signals across multiple assets.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QSizePolicy, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal
from datetime import datetime

from ui.theme import Colors, Fonts, Radius, Spacing
from ui.widgets import (
    Card, SectionHeader, SignalBadge, GlowButton, LoadingLabel,
    Divider, StatPill, ConfidenceGauge
)


class ScanThread(QThread):
    """Scan multiple assets for signals."""
    result_ready = Signal(list)

    def __init__(self, asset_class: str):
        super().__init__()
        self.asset_class = asset_class

    def run(self):
        from core.data_fetcher import ASSET_CATALOG, fetch_ohlcv, add_indicators
        from core.predictor_engine import compute_signal

        symbols = ASSET_CATALOG.get(self.asset_class, {})
        results = []

        for name, ticker in symbols.items():
            try:
                df = fetch_ohlcv(ticker, "1M")
                if df.empty:
                    continue
                df_ind = add_indicators(df)
                if df_ind.empty:
                    continue
                signal = compute_signal(df_ind)
                signal["name"] = name
                signal["symbol"] = ticker
                signal["price"] = df["close"].iloc[-1]
                signal["time"] = datetime.now().strftime("%H:%M")
                results.append(signal)
            except Exception:
                continue

        # Sort by confidence descending
        results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        self.result_ready.emit(results)


class SignalCard(Card):
    """Individual signal card for an asset."""

    def __init__(self, data: dict, parent=None):
        super().__init__(parent, glow=(data.get("confidence", 0) > 0.5))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        # Header row: name + signal badge
        header = QHBoxLayout()
        name_col = QVBoxLayout()
        name_col.setSpacing(2)

        name = QLabel(data.get("name", "Unknown"))
        name.setStyleSheet(f"font-size: {Fonts.SIZE_BASE}px; font-weight: 700; color: {Colors.TEXT};")

        price = data.get("price", 0)
        price_fmt = f"{price:,.5f}" if price < 100 else f"{price:,.2f}"
        price_lbl = QLabel(price_fmt)
        price_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_SM}px; font-family: {Fonts.MONO}; color: {Colors.TEXT_SECONDARY};")

        name_col.addWidget(name)
        name_col.addWidget(price_lbl)

        badge = SignalBadge(data.get("signal", "NEUTRAL"))

        header.addLayout(name_col)
        header.addStretch()
        header.addWidget(badge)

        layout.addLayout(header)

        # Confidence bar
        conf = data.get("confidence", 0)
        conf_bar = QFrame()
        conf_bar.setFixedHeight(4)
        conf_bar.setStyleSheet(f"""
            background: {Colors.BG_INPUT};
            border-radius: 2px;
        """)
        layout.addWidget(conf_bar)

        # Filled portion
        signal = data.get("signal", "NEUTRAL")
        if signal == "BUY":
            bar_color = Colors.BUY
        elif signal == "SELL":
            bar_color = Colors.SELL
        else:
            bar_color = Colors.NEUTRAL

        conf_fill = QFrame(conf_bar)
        conf_fill.setFixedHeight(4)
        conf_fill.setFixedWidth(max(int(conf_bar.width() * conf), int(250 * conf)))
        conf_fill.setStyleSheet(f"background: {bar_color}; border-radius: 2px;")

        # Stats row
        stats = QHBoxLayout()
        stats.setSpacing(16)

        conf_lbl = QLabel(f"Confidence: {conf:.0%}")
        conf_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_XS}px; color: {Colors.TEXT_MUTED};")

        rr = data.get("risk_reward", 0)
        rr_lbl = QLabel(f"R:R  {rr}:1")
        rr_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_XS}px; color: {Colors.TEXT_MUTED};")

        score_val = data.get("movement_score", 0)
        score_color = Colors.BUY if score_val > 0 else Colors.SELL if score_val < 0 else Colors.TEXT_MUTED
        score_lbl = QLabel(f"Score: {score_val:+d}")
        score_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_XS}px; color: {score_color}; font-weight: 700;")

        time_lbl = QLabel(data.get("time", ""))
        time_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_XS}px; color: {Colors.TEXT_MUTED};")

        stats.addWidget(conf_lbl)
        stats.addWidget(rr_lbl)
        stats.addWidget(score_lbl)
        stats.addStretch()
        stats.addWidget(time_lbl)

        layout.addLayout(stats)

        # Key analysis point
        analysis = data.get("analysis", [])
        if analysis:
            key_point = QLabel(analysis[0])
            key_point.setWordWrap(True)
            key_point.setStyleSheet(f"""
                font-size: {Fonts.SIZE_SM}px; color: {Colors.TEXT_SECONDARY};
                background: {Colors.BG_INPUT}; border-radius: {Radius.SM}px;
                padding: 8px 12px;
            """)
            layout.addWidget(key_point)


class SignalsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(32, 24, 32, 24)
        self._layout.setSpacing(20)
        scroll.setWidget(container)

        # Controls
        controls = QHBoxLayout()
        controls.setSpacing(12)

        self._layout.addWidget(SectionHeader(
            "AI Trading Signals",
            "Multi-factor analysis engine scanning for high-probability setups"
        ))

        self._class_combo = QComboBox()
        from core.data_fetcher import ASSET_CATALOG
        for cls in ASSET_CATALOG:
            self._class_combo.addItem(cls)
        controls.addWidget(self._class_combo)

        self._scan_btn = GlowButton("  Scan for Signals  ")
        self._scan_btn.clicked.connect(self._run_scan)
        controls.addWidget(self._scan_btn)

        controls.addStretch()

        # Summary pills
        self._total_pill = StatPill("TOTAL", "—")
        self._buy_pill = StatPill("BUY", "—")
        self._sell_pill = StatPill("SELL", "—")
        controls.addWidget(self._total_pill)
        controls.addWidget(self._buy_pill)
        controls.addWidget(self._sell_pill)

        self._layout.addLayout(controls)

        # Results grid
        self._grid_widget = QWidget()
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(16)
        self._layout.addWidget(self._grid_widget)

        self._loading = LoadingLabel("Click 'Scan for Signals' to begin")
        self._layout.addWidget(self._loading)

        self._layout.addStretch()

    def _run_scan(self):
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("  Scanning...  ")
        self._loading.setText(f"Scanning {self._class_combo.currentText()} markets...")
        self._loading.setVisible(True)

        # Clear grid
        while self._grid.count():
            child = self._grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._thread = ScanThread(self._class_combo.currentText())
        self._thread.result_ready.connect(self._on_results)
        self._thread.start()

    def _on_results(self, results: list):
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("  Scan for Signals  ")
        self._loading.setVisible(False)

        if not results:
            self._loading.setText("No signals found. Try a different asset class.")
            self._loading.setVisible(True)
            return

        # Update summary
        buys = sum(1 for r in results if r["signal"] == "BUY")
        sells = sum(1 for r in results if r["signal"] == "SELL")
        self._total_pill.set_value(str(len(results)))
        self._buy_pill.set_value(str(buys))
        self._sell_pill.set_value(str(sells))

        # Populate grid
        for i, data in enumerate(results):
            card = SignalCard(data)
            self._grid.addWidget(card, i // 2, i % 2)
