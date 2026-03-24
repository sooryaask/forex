"""
Aurion Markets — Reusable UI Components
Premium widget library for the trading platform.
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy, QPushButton, QProgressBar
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QLinearGradient, QBrush, QPainterPath
import math

from ui.theme import Colors, Fonts, Radius, Spacing


# ── Card Container ───────────────────────────────────────────────────────────

class Card(QFrame):
    """A styled card container with optional glow effect."""

    def __init__(self, parent=None, glow: bool = False):
        super().__init__(parent)
        self.setStyleSheet(f"""
            Card {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)
        if glow:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(30)
            shadow.setColor(QColor(59, 130, 246, 30))
            shadow.setOffset(0, 4)
            self.setGraphicsEffect(shadow)


# ── Metric Card ──────────────────────────────────────────────────────────────

class MetricCard(Card):
    """Displays a single KPI metric with label, value, and optional delta."""

    def __init__(self, label: str, value: str = "—", delta: str = "",
                 delta_positive: bool = True, parent=None):
        super().__init__(parent, glow=False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)

        self._label = QLabel(label)
        self._label.setStyleSheet(f"""
            font-size: {Fonts.SIZE_SM}px;
            color: {Colors.TEXT_MUTED};
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        """)

        self._value = QLabel(value)
        self._value.setStyleSheet(f"""
            font-size: {Fonts.SIZE_2XL}px;
            color: {Colors.TEXT};
            font-weight: 700;
            font-family: {Fonts.MONO};
        """)

        self._delta = QLabel(delta)
        self._update_delta_style(delta_positive)

        layout.addWidget(self._label)
        layout.addWidget(self._value)
        layout.addWidget(self._delta)

    def set_value(self, value: str, delta: str = "", delta_positive: bool = True):
        self._value.setText(value)
        self._delta.setText(delta)
        self._update_delta_style(delta_positive)

    def _update_delta_style(self, positive: bool):
        color = Colors.BUY if positive else Colors.SELL
        bg = Colors.BUY_BG if positive else Colors.SELL_BG
        self._delta.setStyleSheet(f"""
            font-size: {Fonts.SIZE_SM}px;
            color: {color};
            font-weight: 600;
            background: {bg};
            border-radius: 4px;
            padding: 2px 8px;
        """)


# ── Signal Badge ─────────────────────────────────────────────────────────────

class SignalBadge(QLabel):
    """Colored badge showing BUY / SELL / NEUTRAL."""

    def __init__(self, signal: str = "NEUTRAL", parent=None):
        super().__init__(parent)
        self.set_signal(signal)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(32)
        self.setMinimumWidth(80)

    def set_signal(self, signal: str):
        signal = signal.upper()
        if signal == "BUY":
            bg, color = Colors.BUY_BG, Colors.BUY
            text = "▲  BUY"
        elif signal == "SELL":
            bg, color = Colors.SELL_BG, Colors.SELL
            text = "▼  SELL"
        else:
            bg, color = Colors.NEUTRAL_BG, Colors.NEUTRAL
            text = "●  NEUTRAL"

        self.setText(text)
        self.setStyleSheet(f"""
            background: {bg};
            color: {color};
            font-size: {Fonts.SIZE_SM}px;
            font-weight: 700;
            border-radius: {Radius.PILL}px;
            padding: 4px 16px;
            letter-spacing: 1px;
        """)


# ── Confidence Gauge ─────────────────────────────────────────────────────────

class ConfidenceGauge(QWidget):
    """Circular gauge showing prediction confidence."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._signal = "NEUTRAL"
        self.setFixedSize(160, 160)

    def set_value(self, value: float, signal: str = "NEUTRAL"):
        self._value = max(0.0, min(1.0, value))
        self._signal = signal.upper()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 12

        # Track
        pen = QPen(QColor(Colors.BORDER), 8)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(
            int(cx - radius), int(cy - radius),
            int(radius * 2), int(radius * 2),
            225 * 16, -270 * 16
        )

        # Value arc
        if self._signal == "BUY":
            arc_color = QColor(Colors.BUY)
        elif self._signal == "SELL":
            arc_color = QColor(Colors.SELL)
        else:
            arc_color = QColor(Colors.NEUTRAL)

        pen = QPen(arc_color, 8)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        span = int(-270 * self._value)
        painter.drawArc(
            int(cx - radius), int(cy - radius),
            int(radius * 2), int(radius * 2),
            225 * 16, span * 16
        )

        # Center text
        painter.setPen(Qt.NoPen)
        pct_text = f"{self._value * 100:.0f}%"
        painter.setPen(QColor(Colors.TEXT))
        font = QFont(Fonts.MONO, Fonts.SIZE_2XL)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, -10, 0, 0), Qt.AlignCenter, pct_text)

        # Sub label
        painter.setPen(QColor(Colors.TEXT_MUTED))
        font = QFont(Fonts.FAMILY, Fonts.SIZE_XS)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, 25, 0, 0), Qt.AlignCenter, "CONFIDENCE")

        painter.end()


# ── Market Ticker Row ────────────────────────────────────────────────────────

class MarketTickerRow(QFrame):
    """Single row in a market watchlist."""

    def __init__(self, name: str, price: str, change: str,
                 change_pct: str, positive: bool, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            MarketTickerRow {{
                background: transparent;
                border-bottom: 1px solid {Colors.BORDER};
                border-radius: 0;
            }}
            MarketTickerRow:hover {{
                background: {Colors.BG_CARD_HOVER};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_BASE}px; font-weight: 600; color: {Colors.TEXT};")

        price_lbl = QLabel(price)
        price_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_BASE}px; font-family: {Fonts.MONO}; color: {Colors.TEXT};")
        price_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        color = Colors.BUY if positive else Colors.SELL
        arrow = "▲" if positive else "▼"
        change_lbl = QLabel(f"{arrow} {change_pct}")
        change_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_SM}px; font-weight: 600; color: {color};")
        change_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        change_lbl.setFixedWidth(90)

        layout.addWidget(name_lbl, 1)
        layout.addWidget(price_lbl, 1)
        layout.addWidget(change_lbl, 0)


# ── Section Header ───────────────────────────────────────────────────────────

class SectionHeader(QWidget):
    """Section header with title and optional subtitle."""

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"""
            font-size: {Fonts.SIZE_XL}px;
            font-weight: 700;
            color: {Colors.TEXT};
        """)
        layout.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet(f"""
                font-size: {Fonts.SIZE_SM}px;
                color: {Colors.TEXT_MUTED};
            """)
            layout.addWidget(sub_lbl)


# ── Stat Pill ────────────────────────────────────────────────────────────────

class StatPill(QFrame):
    """Compact inline stat: label + value."""

    def __init__(self, label: str, value: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            StatPill {{
                background: {Colors.BG_INPUT};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.PILL}px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(8)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: {Fonts.SIZE_XS}px; color: {Colors.TEXT_MUTED}; font-weight: 500;")

        self._val = QLabel(value)
        self._val.setStyleSheet(f"font-size: {Fonts.SIZE_SM}px; color: {Colors.TEXT}; font-weight: 700; font-family: {Fonts.MONO};")

        layout.addWidget(lbl)
        layout.addWidget(self._val)

    def set_value(self, value: str):
        self._val.setText(value)


# ── Analysis Point ───────────────────────────────────────────────────────────

class AnalysisPoint(QFrame):
    """Single analysis bullet point with icon."""

    def __init__(self, text: str, bullish=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            AnalysisPoint {{
                background: {Colors.BG_INPUT};
                border-radius: {Radius.SM}px;
                border: none;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        if bullish is True:
            icon, color = "▲", Colors.BUY
        elif bullish is False:
            icon, color = "▼", Colors.SELL
        else:
            icon, color = "●", Colors.TEXT_MUTED

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_SM}px; color: {color};")
        icon_lbl.setFixedWidth(16)

        text_lbl = QLabel(text)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_SM}px; color: {Colors.TEXT_SECONDARY};")

        layout.addWidget(icon_lbl)
        layout.addWidget(text_lbl, 1)


# ── Divider ──────────────────────────────────────────────────────────────────

class Divider(QFrame):
    """Horizontal divider line."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {Colors.BORDER};")


# ── Glow Button ──────────────────────────────────────────────────────────────

class GlowButton(QPushButton):
    """Primary action button with subtle glow effect."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(42)
        self.setStyleSheet(f"""
            GlowButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.GRADIENT_START}, stop:1 {Colors.GRADIENT_END});
                color: white;
                border: none;
                border-radius: {Radius.SM}px;
                padding: 0 28px;
                font-size: {Fonts.SIZE_BASE}px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            GlowButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.ACCENT_HOVER}, stop:1 #7c3aed);
            }}
            GlowButton:pressed {{
                background: {Colors.ACCENT_HOVER};
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(59, 130, 246, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


# ── Loading Spinner Label ────────────────────────────────────────────────────

class LoadingLabel(QLabel):
    """Animated loading text."""

    def __init__(self, text: str = "Loading", parent=None):
        super().__init__(text + "...", parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"""
            font-size: {Fonts.SIZE_BASE}px;
            color: {Colors.TEXT_MUTED};
            padding: 40px;
        """)
