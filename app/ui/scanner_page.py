"""
Aurion Markets — AI Screenshot Scanner Page
Drag-and-drop or paste chart screenshots for instant AI analysis.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QFileDialog, QSizePolicy, QGridLayout, QTextEdit
)
from PySide6.QtCore import Qt, QMimeData, Signal, QThread
from PySide6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent, QPainter, QColor

from ui.theme import Colors, Fonts, Radius, Spacing
from ui.widgets import (
    Card, SectionHeader, ConfidenceGauge, SignalBadge, StatPill,
    AnalysisPoint, GlowButton, Divider, LoadingLabel
)


class AnalysisThread(QThread):
    """Run screenshot analysis in background."""
    result_ready = Signal(dict)

    def __init__(self, price_text: str):
        super().__init__()
        self.price_text = price_text

    def run(self):
        from core.predictor_engine import analyse_screenshot_data
        import re
        # Extract numbers from pasted text
        numbers = re.findall(r"[\d]+\.[\d]+", self.price_text)
        if not numbers:
            numbers = re.findall(r"[\d]+", self.price_text)

        if len(numbers) < 3:
            self.result_ready.emit({"error": "Could not extract enough price data. Please paste at least 3 price values."})
            return

        prices = [float(n) for n in numbers[:50]]  # cap at 50 points
        result = analyse_screenshot_data(prices)
        self.result_ready.emit(result)


class DropZone(QFrame):
    """Drag-and-drop zone for images."""

    file_dropped = Signal(str)
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(280)
        self._pixmap = None
        self._update_style(False)

    def _update_style(self, hover: bool):
        border_color = Colors.ACCENT if hover else Colors.BORDER_LIGHT
        bg = Colors.BG_ELEVATED if hover else Colors.BG_CARD
        self.setStyleSheet(f"""
            DropZone {{
                background: {bg};
                border: 2px dashed {border_color};
                border-radius: {Radius.LG}px;
            }}
        """)

    def set_image(self, pixmap: QPixmap):
        self._pixmap = pixmap.scaled(
            self.width() - 40, self.height() - 40,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._pixmap:
            x = (self.width() - self._pixmap.width()) // 2
            y = (self.height() - self._pixmap.height()) // 2
            painter.drawPixmap(x, y, self._pixmap)
        else:
            # Draw placeholder
            painter.setPen(QColor(Colors.TEXT_MUTED))
            from PySide6.QtGui import QFont
            font = QFont(Fonts.FAMILY, Fonts.SIZE_3XL)
            painter.setFont(font)
            painter.drawText(self.rect().adjusted(0, -30, 0, 0), Qt.AlignCenter, "◎")

            font = QFont(Fonts.FAMILY, Fonts.SIZE_BASE)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(Colors.TEXT_SECONDARY))
            painter.drawText(self.rect().adjusted(0, 20, 0, 0), Qt.AlignCenter, "Drop chart screenshot here")

            font = QFont(Fonts.FAMILY, Fonts.SIZE_SM)
            painter.setFont(font)
            painter.setPen(QColor(Colors.TEXT_MUTED))
            painter.drawText(self.rect().adjusted(0, 50, 0, 0), Qt.AlignCenter, "or click to browse  ·  PNG, JPG, WEBP")

        painter.end()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasImage() or event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._update_style(True)

    def dragLeaveEvent(self, event):
        self._update_style(False)

    def dropEvent(self, event: QDropEvent):
        self._update_style(False)
        mime = event.mimeData()
        if mime.hasUrls():
            url = mime.urls()[0]
            path = url.toLocalFile()
            if path:
                self.file_dropped.emit(path)
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    self.set_image(pixmap)
        elif mime.hasImage():
            img = mime.imageData()
            if isinstance(img, QImage):
                pixmap = QPixmap.fromImage(img)
                self.set_image(pixmap)

    def mousePressEvent(self, event):
        self.clicked.emit()


class ScannerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)
        scroll.setWidget(container)

        # ── Header ───────────────────────────────────────────────────────
        layout.addWidget(SectionHeader(
            "AI Screenshot Scanner",
            "Upload a chart screenshot or paste price data for instant AI-powered analysis"
        ))

        # ── Main content: drop zone + price input ────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        # Drop zone
        drop_card = Card()
        drop_layout = QVBoxLayout(drop_card)
        drop_layout.setContentsMargins(16, 16, 16, 16)

        self._drop_zone = DropZone()
        self._drop_zone.file_dropped.connect(self._on_file_dropped)
        self._drop_zone.clicked.connect(self._browse_file)
        drop_layout.addWidget(self._drop_zone)

        top_row.addWidget(drop_card, 3)

        # Price data input panel
        input_card = Card()
        input_card.setFixedWidth(380)
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(24, 24, 24, 24)
        input_layout.setSpacing(16)

        input_title = QLabel("PASTE PRICE DATA")
        input_title.setStyleSheet(f"""
            font-size: {Fonts.SIZE_XS}px; color: {Colors.TEXT_MUTED};
            font-weight: 700; letter-spacing: 2px;
        """)
        input_layout.addWidget(input_title)

        desc = QLabel("Paste price values from your chart, one per line or comma-separated. The AI will analyse the trend and generate a prediction.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"font-size: {Fonts.SIZE_SM}px; color: {Colors.TEXT_SECONDARY};")
        input_layout.addWidget(desc)

        self._price_input = QTextEdit()
        self._price_input.setPlaceholderText("e.g.\n1.0845\n1.0852\n1.0838\n1.0861\n1.0875\n1.0869\n...")
        self._price_input.setStyleSheet(f"""
            QTextEdit {{
                background: {Colors.BG_INPUT};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.SM}px;
                padding: 12px;
                font-family: {Fonts.MONO};
                font-size: {Fonts.SIZE_SM}px;
                color: {Colors.TEXT};
            }}
            QTextEdit:focus {{
                border-color: {Colors.ACCENT};
            }}
        """)
        self._price_input.setMinimumHeight(160)
        input_layout.addWidget(self._price_input, 1)

        self._analyse_btn = GlowButton("  Analyse Price Data  ")
        self._analyse_btn.clicked.connect(self._run_price_analysis)
        input_layout.addWidget(self._analyse_btn)

        top_row.addWidget(input_card, 0)
        layout.addLayout(top_row)

        # ── Results Section ──────────────────────────────────────────────
        self._results_frame = QFrame()
        self._results_frame.setVisible(False)
        results_layout = QVBoxLayout(self._results_frame)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(20)

        results_layout.addWidget(SectionHeader("Analysis Results"))

        # Signal + Gauge row
        result_top = QHBoxLayout()
        result_top.setSpacing(20)

        # Signal card
        signal_card = Card(glow=True)
        signal_inner = QVBoxLayout(signal_card)
        signal_inner.setContentsMargins(32, 28, 32, 28)
        signal_inner.setSpacing(16)

        sig_header = QLabel("AI SIGNAL")
        sig_header.setStyleSheet(f"font-size: {Fonts.SIZE_XS}px; color: {Colors.TEXT_MUTED}; font-weight: 700; letter-spacing: 2px;")
        signal_inner.addWidget(sig_header, 0, Qt.AlignCenter)

        self._result_badge = SignalBadge()
        signal_inner.addWidget(self._result_badge, 0, Qt.AlignCenter)

        self._result_gauge = ConfidenceGauge()
        signal_inner.addWidget(self._result_gauge, 0, Qt.AlignCenter)

        signal_inner.addWidget(Divider())

        stats_grid = QGridLayout()
        stats_grid.setSpacing(8)
        self._r_entry = StatPill("ENTRY", "—")
        self._r_sl = StatPill("STOP", "—")
        self._r_tp = StatPill("TARGET", "—")
        self._r_rr = StatPill("R:R", "—")
        stats_grid.addWidget(self._r_entry, 0, 0)
        stats_grid.addWidget(self._r_sl, 0, 1)
        stats_grid.addWidget(self._r_tp, 1, 0)
        stats_grid.addWidget(self._r_rr, 1, 1)
        signal_inner.addLayout(stats_grid)

        result_top.addWidget(signal_card, 0)

        # Analysis points
        analysis_card = Card()
        analysis_inner = QVBoxLayout(analysis_card)
        analysis_inner.setContentsMargins(24, 24, 24, 24)
        analysis_inner.setSpacing(8)

        ana_header = QLabel("ANALYSIS BREAKDOWN")
        ana_header.setStyleSheet(f"font-size: {Fonts.SIZE_XS}px; color: {Colors.TEXT_MUTED}; font-weight: 700; letter-spacing: 2px;")
        analysis_inner.addWidget(ana_header)

        self._analysis_list = QVBoxLayout()
        self._analysis_list.setSpacing(6)
        analysis_inner.addLayout(self._analysis_list)
        analysis_inner.addStretch()

        result_top.addWidget(analysis_card, 1)
        results_layout.addLayout(result_top)

        layout.addWidget(self._results_frame)
        layout.addStretch()

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Chart Screenshot", "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if path:
            self._on_file_dropped(path)

    def _on_file_dropped(self, path: str):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self._drop_zone.set_image(pixmap)
            # For now, show a message about image analysis
            self._show_image_analysis_placeholder()

    def _show_image_analysis_placeholder(self):
        self._results_frame.setVisible(True)
        self._result_badge.set_signal("NEUTRAL")
        self._result_gauge.set_value(0.0, "NEUTRAL")

        # Clear old analysis
        while self._analysis_list.count():
            child = self._analysis_list.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._analysis_list.addWidget(AnalysisPoint(
            "Image uploaded successfully. For full image analysis, paste the visible price levels in the price data panel.",
            None
        ))
        self._analysis_list.addWidget(AnalysisPoint(
            "Tip: Copy the last 10-20 price values you can see on the chart's Y-axis or candlestick close prices.",
            None
        ))

    def _run_price_analysis(self):
        text = self._price_input.toPlainText().strip()
        if not text:
            return

        self._analyse_btn.setEnabled(False)
        self._analyse_btn.setText("  Analysing...  ")

        self._thread = AnalysisThread(text)
        self._thread.result_ready.connect(self._on_analysis_result)
        self._thread.start()

    def _on_analysis_result(self, result: dict):
        self._analyse_btn.setEnabled(True)
        self._analyse_btn.setText("  Analyse Price Data  ")
        self._results_frame.setVisible(True)

        if "error" in result:
            self._result_badge.set_signal("NEUTRAL")
            self._result_gauge.set_value(0.0)
            while self._analysis_list.count():
                child = self._analysis_list.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self._analysis_list.addWidget(AnalysisPoint(result["error"], None))
            return

        self._result_badge.set_signal(result["signal"])
        self._result_gauge.set_value(result["confidence"], result["signal"])

        fmt = lambda v: f"{v:,.5f}" if abs(v) < 100 else f"{v:,.2f}"
        if result["entry"]:
            self._r_entry.set_value(fmt(result["entry"]))
            self._r_sl.set_value(fmt(result["stop_loss"]))
            self._r_tp.set_value(fmt(result["take_profit"]))
            self._r_rr.set_value(f"{result['risk_reward']}:1")

        # Clear and populate analysis
        while self._analysis_list.count():
            child = self._analysis_list.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for text in result.get("analysis", []):
            bullish = None
            lower = text.lower()
            if any(w in lower for w in ["bullish", "buy", "oversold", "bounce", "uptrend"]):
                bullish = True
            elif any(w in lower for w in ["bearish", "sell", "overbought", "pullback", "downtrend"]):
                bullish = False
            self._analysis_list.addWidget(AnalysisPoint(text, bullish))
