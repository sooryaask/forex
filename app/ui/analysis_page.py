"""
Aurion Markets — Market Analysis Page
Interactive candlestick charts with technical indicators and AI predictions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QFrame,
    QScrollArea, QSizePolicy, QGridLayout, QPushButton, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
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
        try:
            from core.data_fetcher import fetch_ohlcv, add_indicators, get_current_price
            from core.predictor_engine import compute_signal

            df = fetch_ohlcv(self.symbol, self.timeframe)
            price_info = get_current_price(self.symbol)

            if df.empty:
                self.result_ready.emit({"error": f"No data available for {self.symbol}. Check your internet connection."})
                return

            df_ind = add_indicators(df.copy())
            signal = compute_signal(df_ind) if not df_ind.empty else {
                "signal": "NEUTRAL", "confidence": 0, "movement_score": 0,
                "entry": 0, "stop_loss": 0, "take_profit": 0, "risk_reward": 0,
                "analysis": ["Not enough data for full technical analysis"]
            }

            self.result_ready.emit({
                "df": df,
                "df_ind": df_ind,
                "signal": signal,
                "price_info": price_info,
            })
        except Exception as e:
            self.result_ready.emit({"error": f"Analysis failed: {str(e)}"})


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
        # Ensure correct column names for mplfinance
        col_map = {}
        for col in plot_df.columns:
            if col.lower() == "open":
                col_map[col] = "Open"
            elif col.lower() == "high":
                col_map[col] = "High"
            elif col.lower() == "low":
                col_map[col] = "Low"
            elif col.lower() == "close":
                col_map[col] = "Close"
            elif col.lower() == "volume":
                col_map[col] = "Volume"
        plot_df = plot_df.rename(columns=col_map)

        # Make sure index is DatetimeIndex
        if not isinstance(plot_df.index, pd.DatetimeIndex):
            plot_df.index = pd.to_datetime(plot_df.index)

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

        has_volume = "Volume" in plot_df.columns and plot_df["Volume"].sum() > 0

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
            if not close_data.empty:
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
        # Defer initial analysis until UI is fully ready
        QTimer.singleShot(500, self._run_analysis)

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
        self._symbol_combo.currentIndexChanged.connect(self._on_symbol_changed)
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

        self._loading_label = QLabel("Running analysis...")
        self._loading_label.setAlignment(Qt.AlignCenter)
        self._loading_label.setStyleSheet(f"font-size: {Fonts.SIZE_BASE}px; color: {Colors.TEXT_MUTED}; padding: 40px;")
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
        # Auto-analyse first symbol in new class
        if self._symbol_combo.count() > 0:
            self._current_symbol = self._symbol_combo.currentData()
            self._run_analysis()

    def _on_symbol_changed(self, index: int):
        symbol = self._symbol_combo.currentData()
        if symbol and symbol != self._current_symbol:
            self._current_symbol = symbol
            self._run_analysis()

    def _on_tf_click(self, tf: str):
        self._current_tf = tf
        for btn in self._tf_buttons:
            btn.setStyleSheet(self._tf_style(btn.text() == tf))
        # Auto-analyse on timeframe change
        self._run_analysis()

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
        # Prevent multiple simultaneous analyses
        if self._thread is not None and self._thread.isRunning():
            return

        symbol = self._symbol_combo.currentData() or self._current_symbol
        self._current_symbol = symbol

        # Show loading state
        self._analyse_btn.set_loading(True, "  Analysing...  ")
        self._loading_label.setText(f"Fetching live data for {self._symbol_combo.currentText() or symbol}...")
        self._loading_label.setVisible(True)

        self._thread = DataThread(symbol, self._current_tf)
        self._thread.result_ready.connect(self._on_result)
        self._thread.start()

    def _on_result(self, result: dict):
        # Re-enable button
        self._analyse_btn.set_loading(False)
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

        # Update price from live data
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

        # Clear old analysis points (keep the loading label)
        while self._analysis_container.count():
            child = self._analysis_container.takeAt(0)
            w = child.widget()
            if w and w is not self._loading_label:
                w.deleteLater()

        # Re-add loading label (hidden)
        self._analysis_container.addWidget(self._loading_label)
        self._loading_label.setVisible(False)

        # Add new analysis points
        for point_text in signal.get("analysis", []):
            bullish = None
            lower = point_text.lower()
            if any(w in lower for w in ["bullish", "buy", "oversold", "bounce", "uptrend", "above", "green"]):
                bullish = True
            elif any(w in lower for w in ["bearish", "sell", "overbought", "pullback", "downtrend", "below", "red"]):
                bullish = False
            self._analysis_container.addWidget(AnalysisPoint(point_text, bullish))

        # Save to history
        try:
            from ui.history_page import add_signal_to_history
            signal["name"] = self._symbol_combo.currentText() or "Unknown"
            signal["symbol"] = self._current_symbol
            add_signal_to_history(signal)
        except Exception:
            pass
