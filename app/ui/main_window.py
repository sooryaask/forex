"""
Aurion Markets — Main Window
Sidebar navigation + content area shell.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QStackedWidget, QSizePolicy, QPushButton, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QLinearGradient, QIcon

from ui.theme import Colors, Fonts, Radius, Spacing


# ── Sidebar Navigation Item ──────────────────────────────────────────────────

class NavItem(QPushButton):
    """Single sidebar navigation button."""

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.icon_char = icon
        self.label_text = label
        self._active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(48)
        self.setCheckable(True)
        self._apply_style()

    def _apply_style(self):
        bg = Colors.BG_ELEVATED if self._active else "transparent"
        text_color = Colors.ACCENT if self._active else Colors.TEXT_MUTED
        border_left = f"3px solid {Colors.ACCENT}" if self._active else "3px solid transparent"

        self.setStyleSheet(f"""
            NavItem {{
                background: {bg};
                color: {text_color};
                border: none;
                border-left: {border_left};
                border-radius: 0;
                text-align: left;
                padding-left: 20px;
                font-size: {Fonts.SIZE_BASE}px;
                font-weight: {'600' if self._active else '400'};
            }}
            NavItem:hover {{
                background: {Colors.BG_CARD_HOVER};
                color: {Colors.TEXT};
            }}
        """)
        self.setText(f" {self.icon_char}    {self.label_text}")

    def set_active(self, active: bool):
        self._active = active
        self.setChecked(active)
        self._apply_style()


# ── Sidebar ──────────────────────────────────────────────────────────────────

class Sidebar(QFrame):
    """Left sidebar with branding and navigation."""

    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setStyleSheet(f"""
            Sidebar {{
                background-color: {Colors.BG_SIDEBAR};
                border-right: 1px solid {Colors.BORDER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Brand ────────────────────────────────────────────────────────
        brand = QFrame()
        brand.setFixedHeight(80)
        brand.setStyleSheet(f"background: transparent; border-bottom: 1px solid {Colors.BORDER};")
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(20, 0, 20, 0)

        # Logo circle
        logo = QLabel("A")
        logo.setFixedSize(36, 36)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {Colors.GRADIENT_START}, stop:1 {Colors.GRADIENT_END});
            color: white;
            font-size: {Fonts.SIZE_LG}px;
            font-weight: 800;
            border-radius: 10px;
        """)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)

        name = QLabel("AURION")
        name.setStyleSheet(f"""
            font-size: {Fonts.SIZE_LG}px;
            font-weight: 800;
            color: {Colors.TEXT};
            letter-spacing: 3px;
        """)

        subtitle = QLabel("MARKETS")
        subtitle.setStyleSheet(f"""
            font-size: {Fonts.SIZE_XS}px;
            color: {Colors.TEXT_MUTED};
            letter-spacing: 5px;
            font-weight: 500;
        """)

        brand_text.addWidget(name)
        brand_text.addWidget(subtitle)

        brand_layout.addWidget(logo)
        brand_layout.addSpacing(12)
        brand_layout.addLayout(brand_text)
        brand_layout.addStretch()

        layout.addWidget(brand)

        # ── Navigation ───────────────────────────────────────────────────
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 12, 0, 12)
        nav_layout.setSpacing(2)

        section_lbl = QLabel("  OVERVIEW")
        section_lbl.setStyleSheet(f"""
            font-size: 9px; color: {Colors.TEXT_MUTED}; font-weight: 600;
            letter-spacing: 2px; padding: 10px 20px 6px 23px;
        """)
        nav_layout.addWidget(section_lbl)

        self._nav_items: list[NavItem] = []
        nav_entries = [
            ("◉", "Dashboard"),
            ("◈", "Market Analysis"),
            ("◎", "AI Scanner"),
        ]

        for icon, label in nav_entries:
            item = NavItem(icon, label)
            item.clicked.connect(lambda checked, i=len(self._nav_items): self._on_nav_click(i))
            nav_layout.addWidget(item)
            self._nav_items.append(item)

        section_lbl2 = QLabel("  INTELLIGENCE")
        section_lbl2.setStyleSheet(f"""
            font-size: 9px; color: {Colors.TEXT_MUTED}; font-weight: 600;
            letter-spacing: 2px; padding: 16px 20px 6px 23px;
        """)
        nav_layout.addWidget(section_lbl2)

        nav_entries2 = [
            ("◆", "Signals"),
            ("◇", "History"),
        ]

        for icon, label in nav_entries2:
            item = NavItem(icon, label)
            item.clicked.connect(lambda checked, i=len(self._nav_items): self._on_nav_click(i))
            nav_layout.addWidget(item)
            self._nav_items.append(item)

        nav_layout.addStretch()

        layout.addWidget(nav_container, 1)

        # ── Footer ───────────────────────────────────────────────────────
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet(f"border-top: 1px solid {Colors.BORDER}; background: transparent;")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(20, 8, 20, 8)

        # Connection status
        status_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {Colors.BUY}; font-size: 8px;")
        dot.setFixedWidth(14)
        status_text = QLabel("Connected  ·  v4.2.1")
        status_text.setStyleSheet(f"font-size: {Fonts.SIZE_XS}px; color: {Colors.TEXT_MUTED};")
        status_row.addWidget(dot)
        status_row.addWidget(status_text)
        status_row.addStretch()
        footer_layout.addLayout(status_row)

        layout.addWidget(footer)

        # Set initial active
        if self._nav_items:
            self._nav_items[0].set_active(True)

    def _on_nav_click(self, index: int):
        for i, item in enumerate(self._nav_items):
            item.set_active(i == index)
        self.page_changed.emit(index)


# ── Top Bar ──────────────────────────────────────────────────────────────────

class TopBar(QFrame):
    """Top bar with page title, market status, and time."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            TopBar {{
                background: {Colors.BG_SECONDARY};
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 0, 28, 0)

        self._title = QLabel("Dashboard")
        self._title.setStyleSheet(f"""
            font-size: {Fonts.SIZE_LG}px;
            font-weight: 700;
            color: {Colors.TEXT};
        """)

        # Market status pills
        right = QHBoxLayout()
        right.setSpacing(12)

        for market, status, color in [
            ("NYSE", "OPEN", Colors.BUY),
            ("FOREX", "24H", Colors.ACCENT),
            ("CRYPTO", "24/7", Colors.CYAN),
        ]:
            pill = QLabel(f" ● {market} {status}")
            pill.setStyleSheet(f"""
                font-size: {Fonts.SIZE_XS}px;
                color: {color};
                background: {Colors.BG_INPUT};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.PILL}px;
                padding: 4px 12px;
                font-weight: 600;
            """)
            right.addWidget(pill)

        self._time_label = QLabel()
        self._time_label.setStyleSheet(f"""
            font-size: {Fonts.SIZE_SM}px;
            color: {Colors.TEXT_MUTED};
            font-family: {Fonts.MONO};
        """)
        right.addWidget(self._time_label)

        layout.addWidget(self._title)
        layout.addStretch()
        layout.addLayout(right)

        # Update clock
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time)
        self._timer.start(1000)
        self._update_time()

    def set_title(self, title: str):
        self._title.setText(title)

    def _update_time(self):
        from datetime import datetime
        now = datetime.now()
        self._time_label.setText(now.strftime("%H:%M:%S  UTC%z"))


# ── Main Window ──────────────────────────────────────────────────────────────

PAGE_TITLES = ["Dashboard", "Market Analysis", "AI Scanner", "Signals", "History"]


class MainWindow(QMainWindow):
    """Root application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aurion Markets — Trading Intelligence Platform")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        self._sidebar.page_changed.connect(self._on_page_changed)
        root.addWidget(self._sidebar)

        # Right area (top bar + content)
        right_area = QVBoxLayout()
        right_area.setContentsMargins(0, 0, 0, 0)
        right_area.setSpacing(0)

        self._topbar = TopBar()
        right_area.addWidget(self._topbar)

        # Stacked content pages
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {Colors.BG_PRIMARY};")
        right_area.addWidget(self._stack, 1)

        root.addLayout(right_area, 1)

    def add_page(self, page: QWidget):
        self._stack.addWidget(page)

    def _on_page_changed(self, index: int):
        if index < self._stack.count():
            self._stack.setCurrentIndex(index)
        if index < len(PAGE_TITLES):
            self._topbar.set_title(PAGE_TITLES[index])
