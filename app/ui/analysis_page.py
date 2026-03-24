"""
Aurion Markets — Market Analysis Page
Interactive candlestick charts with technical indicators and AI predictions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QFrame,
    QScrollArea, QSizePolicy, QGridLayout, QPushButton, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import mplfinance as mpf
import pandas as pd
import numpy as np

from ui.theme import Colors, Fonts, Radius, Spacing
from ui.widgets import (
    Card, SectionHeader, ConfidenceGauge, SignalBadge, StatPill,
    AnalysisPoint, GlowButton, LoadingLabel, Divider
)


class DataThread(QThread):
    """Background thread for fetching + analysing market data."""
    result_ready = Signal(dict)

    def __init__(self, symbol: str, timeframe: str):
        super().__init__()
        self.symbol = symbol
        self.timeframe = timeframe

    def run(self):
        from core.data_fetcher import fetch_ohlcv, add_indicators, get_current_price
        from core.predictor_engine import compute_signal

        df = fetch_ohlcv(self.symbol, self.timeframe)
        price_info = get_current_price(self.symbol)

        if df.empty:
            self.result_ready.emit({"error": "No data available"})
            return

        df_ind = add_indicators(df.copy())
        signal = compute_signal(df_ind) if not df_ind.empty else {"signal": "NEUTRAL", "confidence": 0, "analysis": []}

        self.result_ready.emit({
            "df": df,
            "df_ind": df_ind,
            "signal": signal,
            "price_info": price_info,
        })


class ChartCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas for candlestick charts."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.fig.patch.set_facecolor(Colors.BG_CARD)
        super().__init__(self.fig)
        self.setStyleSheet(f"background: {Colors.BG_CARD}; border-radius: {Radius.LG}px;")

    def plot_chart(self, df: pd.DataFrame, title: str = ""):
        self.fig.clear()

        if df.empty or len(df) < 2:
            ax = self.fig.add_subplot(111)
            ax.set_facecolor(Colors.BG_CARD)
            ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                    color=Colors.TEXT_MUTED, fontsize=14, transform=ax.transAxes)
            self.draw()
            return

        # Prepare data for mplfinance
        plot_df = df.copy()
        plot_df.columns = [c.capitalize() if c in ("open", "high", "low", "close", "volume") else c for c in plot_df.columns]
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col not in plot_df.columns:
                if col.lower() in plot_df.columns:
                    plot_df[col] = plot_df[col.lower()]

        # Custom style
        mc = mpf.make_marketcolors(
            up=Colors.CANDLE_UP, down=Colors.CANDLE_DOWN,
            edge={"up": Colors.CANDLE_UP, "down": Colors.CANDLE_DOWN},
            wick={"up": Colors.CANDLE_UP, "down": Colors.CANDLE_DOWN},
            volume={"up": "#10b98140", "down": "#ef444440"},
        )
        style = mpf.make_mpf_style(
            marketcolors=mc,
            facecolor=Colors.BG_CARD,
            edgecolor=Colors.BORDER,
            gridcolor=Colors.GRID,
            gridstyle="--",
            gridaxis="both",
            y_on_right=True,
            rc={
                "axes.labelcolor": Colors.TEXT_MUTED,
                "xtick.color": Colors.TEXT_MUTED,
                "ytick.color": Colors.TEXT_MUTED,
                "font.size": 9,
            },
        )

        # Additional plots (EMA overlays if available)
        add_plots = []
        if "ema_9" in df.columns:
            add_plots.append(mpf.make_addplot(df["ema_9"], color=Colors.ACCENT, width=1, ax=None))
        if "ema_21" in df.columns:
            add_plots.append(mpf.make_addplot(df["ema_21"], color=Colors.PURPLE, width=1, ax=None))

        has_volume = "Volume" in plot_df.columns or "volume" in plot_df.columns
        if has_volume:
            vol_data = plot_df.get("Volume", plot_df.get("volume", pd.Series()))
            has_volume = vol_data.sum() > 0

        try:
            mpf.plot(
                plot_df, type="candle", style=style,
                volume=has_volume,
                figsize=(10, 6),
                title=f"\n{title}" if title else "",
                fig=self.fig,
                warn_too_much_data=9999,
            )
        except Exception:
            # Fallback to simple line chart
            ax = self.fig.add_subplot(111)
            ax.set_facecolor(Colors.BG_CARD)
            close_data = plot_df.get("Close", plot_df.get("close", pd.Series()))
            ax.plot(close_data.values, color=Colors.ACCENT, linewidth=1.5)
            ax.fill_between(range(len(close_data)), close_data.values,
                          alpha=0.1, color=Colors.ACCENT)
            ax.tick_params(colors=Colors.TEXT_MUTED)
            for spine in ax.spines.values():
                spine.set_color(Colors.BORDER)
            ax.set_title(title, color=Colors.TEXT, fontsize=12, pad=10)

        self.fig.tight_layout(pad=1.5)
        self.draw()


class AnalysisPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_symbol = "EURUSD=X"
        self._current_tf = "1M"
        self._thread = None
        self._build_ui()
        self._run_analysis()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

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

        # ── Controls Bar ─────────────────────────────────────────────────
        controls = QHBoxLayout()
        controls.setSpacing(12)

        # Asset class selector
        self._class_combo = QComboBox()
        from core.data_fetcher import ASSET_CATALOG
        for cls in ASSET_CATALOG:
            self._class_combo.addItem(cls)
        self._class_combo.currentTextChanged.connect(self._on_class_changed)
        controls.addWidget(self._class_combo)

        # Symbol selector
        self._symbol_combo = QComboBox()
        self._populate_symbols("Forex")
        self._symbol_combo.currentTextChanged.connect(self._on_symbol_changed)
        controls.addWidget(self._symbol_combo)

        controls.addSpacing(12)

        # Timeframe buttons
        self._tf_buttons: list[QPushButton] = []
        from core.data_fetcher import TIMEFRAMES
        for tf in TIMEFRAMES:
            btn = QPushButton(tf)
            btn.setFixedSize(48, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._tf_style(tf == self._current_tf))
            btn.clicked.connect(lambda _, t=tf: self._on_tf_click(t))
            controls.addWidget(btn)
            self._tf_buttons.append(btn)

        controls.addStretch()

        self._analyse_btn = GlowButton("  Analyse  ")
        self._analyse_btn.clicked.connect(self._run_analysis)
        controls.addWidget(self._analyse_btn)

        layout.addLayout(controls)

        # ── Main Content: Chart + Signal Panel ───────────────────────────
        content = QHBoxLayout()
        content.setSpacing(20)

        # Chart
        chart_card = Card()
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(16, 16, 16, 16)
        self._chart = ChartCanvas()
        self._chart.setMinimumHeight(450)
        chart_layout.addWidget(self._chart)
        content.addWidget(chart_card, 7)

        # Signal Panel
        signal_card = Card(glow=True)
        signal_card.setFixedWidth(300)
        signal_layout = QVBoxLayout(signal_card)
        signal_layout.setContentsMargins(24, 24, 24, 24)
        signal_layout.setSpacing(16)

        signal_header = QLabel("AI PREDICTION")
        signal_header.setStyleSheet(f"""
            font-size: {Fonts.SIZE_XS}px; color: {Colors.TEXT_MUTED};
            font-weight: 700; letter-spacing: 2px;
        """)
        signal_layout.addWidget(signal_header, 0, Qt.AlignCenter)

        self._signal_badge = SignalBadge()
        signal_layout.addWidget(self._signal_badge, 0, Qt.AlignCenter)

        self._gauge = ConfidenceGauge()
        signal_layout.addWidget(self._gauge, 0, Qt.AlignCenter)

        signal_layout.addWidget(Divider())

        # Stats
        stats_grid = QGridLayout()
        stats_grid.setSpacing(8)

        self._entry_pill = StatPill("ENTRY", "—")
        self._sl_pill = StatPill("STOP", "—")
        self._tp_pill = StatPill("TARGET", "—")
        self._rr_pill = StatPill("R:R", "—")

        stats_grid.addWidget(self._entry_pill, 0, 0)
        stats_grid.addWidget(self._sl_pill, 0, 1)
        stats_grid.addWidget(self._tp_pill, 1, 0)
        stats_grid.addWidget(self._rr_pill, 1, 1)

        signal_layout.addLayout(stats_grid)

        signal_layout.addWidget(Divider())

        # Price info
        self._price_label = QLabel("—")
        self._price_label.setStyleSheet(f"""
            font-size: {Fonts.SIZE_3XL}px; font-weight: 800;
            color: {Colors.TEXT}; font-family: {Fonts.MONO};
        """)
        self._price_label.setAlignment(Qt.AlignCenter)
        signal_layout.addWidget(self._price_label)

        self._change_label = QLabel("")
        self._change_label.setAlignment(Qt.AlignCenter)
        signal_layout.addWidget(self._change_label)

        signal_layout.addStretch()

        content.addWidget(signal_card, 0)
        layout.addLayout(content)

        # ── Analysis Points ──────────────────────────────────────────────
        layout.addWidget(SectionHeader("Technical Analysis Breakdown"))

        self._analysis_container = QVBoxLayout()
        self._analysis_container.setSpacing(6)

        self._loading_label = LoadingLabel("Running analysis")
        self._analysis_container.addWidget(self._loading_label)

        layout.addLayout(self._analysis_container)
        layout.addStretch()

    def _populate_symbols(self, asset_class: str):
        from core.data_fetcher import ASSET_CATALOG
        self._symbol_combo.blockSignals(True)
        self._symbol_combo.clear()
        symbols = ASSET_CATALOG.get(asset_class, {})
        for name, ticker in symbols.items():
            self._symbol_combo.addItem(name, ticker)
        self._symbol_combo.blockSignals(False)

    def _on_class_changed(self, asset_class: str):
        self._populate_symbols(asset_class)

    def _on_symbol_changed(self, name: str):
        symbol = self._symbol_combo.currentData()
        if symbol:
            self._current_symbol = symbol

    def _on_tf_click(self, tf: str):
        self._current_tf = tf
        for btn in self._tf_buttons:
            btn.setStyleSheet(self._tf_style(btn.text() == tf))

    def _tf_style(self, active: bool) -> str:
        if active:
            return f"""
                background: {Colors.ACCENT};
                color: white;
                border: none;
                border-radius: {Radius.SM}px;
                font-size: {Fonts.SIZE_SM}px;
                font-weight: 700;
            """
        return f"""
            background: {Colors.BG_INPUT};
            color: {Colors.TEXT_MUTED};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.SM}px;
            font-size: {Fonts.SIZE_SM}px;
            font-weight: 500;
        """

    def _run_analysis(self):
        symbol = self._symbol_combo.currentData() or self._current_symbol
        self._current_symbol = symbol
        self._loading_label.setVisible(True)
        self._loading_label.setText(f"Analysing {self._symbol_combo.currentText()}...")

        self._thread = DataThread(symbol, self._current_tf)
        self._thread.result_ready.connect(self._on_result)
        self._thread.start()

    def _on_result(self, result: dict):
        self._loading_label.setVisible(False)

        if "error" in result:
            self._loading_label.setText(result["error"])
            self._loading_label.setVisible(True)
            return

        df = result["df"]
        signal = result["signal"]
        price_info = result.get("price_info", {})

        # Update chart
        name = self._symbol_combo.currentText() or "Market"
        self._chart.plot_chart(df, f"{name}  ·  {self._current_tf}")

        # Update signal panel
        self._signal_badge.set_signal(signal["signal"])
        self._gauge.set_value(signal["confidence"], signal["signal"])

        fmt = lambda v: f"{v:,.5f}" if abs(v) < 100 else f"{v:,.2f}"

        if signal["entry"]:
            self._entry_pill.set_value(fmt(signal["entry"]))
            self._sl_pill.set_value(fmt(signal["stop_loss"]))
            self._tp_pill.set_value(fmt(signal["take_profit"]))
            self._rr_pill.set_value(f"{signal['risk_reward']}:1")
        else:
            for pill in [self._entry_pill, self._sl_pill, self._tp_pill, self._rr_pill]:
                pill.set_value("—")

        # Update price
        if price_info:
            price = price_info["price"]
            self._price_label.setText(fmt(price))
            pct = price_info.get("change_pct", 0)
            color = Colors.BUY if pct >= 0 else Colors.SELL
            arrow = "▲" if pct >= 0 else "▼"
            self._change_label.setText(f"{arrow} {pct:+.2f}%")
            self._change_label.setStyleSheet(f"font-size: {Fonts.SIZE_BASE}px; font-weight: 700; color: {color};")
        else:
            self._price_label.setText("—")
            self._change_label.setText("")

        # Update analysis points
        # Clear old points
        while self._analysis_container.count():
            child = self._analysis_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for point_text in signal.get("analysis", []):
            bullish = None
            lower = point_text.lower()
            if any(w in lower for w in ["bullish", "buy", "oversold", "bounce", "uptrend", "above", "green"]):
                bullish = True
            elif any(w in lower for w in ["bearish", "sell", "overbought", "pullback", "downtrend", "below", "red"]):
                bullish = False
            self._analysis_container.addWidget(AnalysisPoint(point_text, bullish))
