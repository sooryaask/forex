"""
Aurion Markets — Design System
Premium dark fintech theme with glassmorphism accents.
"""


class Colors:
    # ── Backgrounds ────────────────────────────────────────────────────────
    BG_PRIMARY = "#06080d"
    BG_SECONDARY = "#0c1018"
    BG_CARD = "#111827"
    BG_CARD_HOVER = "#1a2235"
    BG_SIDEBAR = "#080b12"
    BG_INPUT = "#0f1420"
    BG_ELEVATED = "#182035"

    # ── Borders ────────────────────────────────────────────────────────────
    BORDER = "#1e293b"
    BORDER_LIGHT = "#334155"
    BORDER_FOCUS = "#3b82f6"

    # ── Brand ──────────────────────────────────────────────────────────────
    ACCENT = "#3b82f6"
    ACCENT_HOVER = "#2563eb"
    ACCENT_GLOW = "rgba(59, 130, 246, 0.15)"
    CYAN = "#06b6d4"
    PURPLE = "#8b5cf6"
    GRADIENT_START = "#3b82f6"
    GRADIENT_END = "#8b5cf6"

    # ── Signals ────────────────────────────────────────────────────────────
    BUY = "#10b981"
    BUY_BG = "rgba(16, 185, 129, 0.12)"
    SELL = "#ef4444"
    SELL_BG = "rgba(239, 68, 68, 0.12)"
    NEUTRAL = "#f59e0b"
    NEUTRAL_BG = "rgba(245, 158, 11, 0.12)"

    # ── Text ───────────────────────────────────────────────────────────────
    TEXT = "#f1f5f9"
    TEXT_SECONDARY = "#94a3b8"
    TEXT_MUTED = "#64748b"
    TEXT_DARK = "#1e293b"

    # ── Chart ──────────────────────────────────────────────────────────────
    CANDLE_UP = "#10b981"
    CANDLE_DOWN = "#ef4444"
    GRID = "#1e293b"
    CROSSHAIR = "#475569"


class Fonts:
    FAMILY = "SF Pro Display, Helvetica Neue, -apple-system, Segoe UI, Arial"
    MONO = "SF Mono, Menlo, JetBrains Mono, Consolas, monospace"
    SIZE_XS = 10
    SIZE_SM = 11
    SIZE_BASE = 13
    SIZE_LG = 15
    SIZE_XL = 18
    SIZE_2XL = 24
    SIZE_3XL = 32
    SIZE_HERO = 42


class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


class Radius:
    SM = 6
    MD = 10
    LG = 14
    XL = 20
    PILL = 100


def get_stylesheet() -> str:
    """Master stylesheet for the entire application."""
    return f"""
    /* ── Global ─────────────────────────────────────────────────────── */
    * {{
        font-family: {Fonts.FAMILY};
        color: {Colors.TEXT};
    }}

    QMainWindow, QWidget {{
        background-color: {Colors.BG_PRIMARY};
    }}

    /* ── Scrollbars ─────────────────────────────────────────────────── */
    QScrollBar:vertical {{
        background: {Colors.BG_SECONDARY};
        width: 8px;
        margin: 0;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {Colors.BORDER_LIGHT};
        min-height: 30px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {Colors.TEXT_MUTED};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: {Colors.BG_SECONDARY};
        height: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {Colors.BORDER_LIGHT};
        min-width: 30px;
        border-radius: 4px;
    }}

    /* ── Labels ──────────────────────────────────────────────────────── */
    QLabel {{
        background: transparent;
        border: none;
    }}

    /* ── Buttons ─────────────────────────────────────────────────────── */
    QPushButton {{
        background-color: {Colors.BG_CARD};
        color: {Colors.TEXT};
        border: 1px solid {Colors.BORDER};
        border-radius: {Radius.SM}px;
        padding: 8px 18px;
        font-size: {Fonts.SIZE_BASE}px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {Colors.BG_CARD_HOVER};
        border-color: {Colors.BORDER_LIGHT};
    }}
    QPushButton:pressed {{
        background-color: {Colors.BG_ELEVATED};
    }}

    /* ── Primary Buttons ─────────────────────────────────────────────── */
    QPushButton[class="primary"] {{
        background-color: {Colors.ACCENT};
        color: white;
        border: none;
        font-weight: 600;
    }}
    QPushButton[class="primary"]:hover {{
        background-color: {Colors.ACCENT_HOVER};
    }}

    /* ── Inputs ──────────────────────────────────────────────────────── */
    QLineEdit {{
        background-color: {Colors.BG_INPUT};
        border: 1px solid {Colors.BORDER};
        border-radius: {Radius.SM}px;
        padding: 8px 14px;
        font-size: {Fonts.SIZE_BASE}px;
        color: {Colors.TEXT};
        selection-background-color: {Colors.ACCENT};
    }}
    QLineEdit:focus {{
        border-color: {Colors.ACCENT};
    }}
    QLineEdit::placeholder {{
        color: {Colors.TEXT_MUTED};
    }}

    /* ── ComboBox ────────────────────────────────────────────────────── */
    QComboBox {{
        background-color: {Colors.BG_INPUT};
        border: 1px solid {Colors.BORDER};
        border-radius: {Radius.SM}px;
        padding: 8px 14px;
        font-size: {Fonts.SIZE_BASE}px;
        color: {Colors.TEXT};
        min-width: 140px;
    }}
    QComboBox:hover {{
        border-color: {Colors.BORDER_LIGHT};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {Colors.TEXT_MUTED};
        margin-right: 10px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {Colors.BG_CARD};
        border: 1px solid {Colors.BORDER};
        border-radius: {Radius.SM}px;
        selection-background-color: {Colors.BG_ELEVATED};
        padding: 4px;
    }}

    /* ── Tab Widget ──────────────────────────────────────────────────── */
    QTabWidget::pane {{
        border: none;
        background: transparent;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {Colors.TEXT_MUTED};
        padding: 10px 20px;
        border-bottom: 2px solid transparent;
        font-size: {Fonts.SIZE_BASE}px;
        font-weight: 500;
    }}
    QTabBar::tab:hover {{
        color: {Colors.TEXT_SECONDARY};
    }}
    QTabBar::tab:selected {{
        color: {Colors.ACCENT};
        border-bottom: 2px solid {Colors.ACCENT};
    }}

    /* ── Progress Bar ───────────────────────────────────────────────── */
    QProgressBar {{
        background-color: {Colors.BG_INPUT};
        border: none;
        border-radius: 4px;
        text-align: center;
        font-size: {Fonts.SIZE_XS}px;
        color: {Colors.TEXT_MUTED};
        height: 8px;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {Colors.GRADIENT_START}, stop:1 {Colors.GRADIENT_END});
        border-radius: 4px;
    }}

    /* ── Tooltips ────────────────────────────────────────────────────── */
    QToolTip {{
        background-color: {Colors.BG_ELEVATED};
        color: {Colors.TEXT};
        border: 1px solid {Colors.BORDER};
        border-radius: {Radius.SM}px;
        padding: 6px 10px;
        font-size: {Fonts.SIZE_SM}px;
    }}
    """
