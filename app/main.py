"""
Aurion Markets — Trading Intelligence Platform
Professional-grade AI-powered market analysis desktop application.

Usage:
    python main.py
"""

import sys
import os

# Ensure app directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QSplashScreen, QLabel, QVBoxLayout, QWidget, QProgressBar
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QPainter, QLinearGradient, QPixmap, QPen


class SplashScreen(QSplashScreen):
    """Premium animated splash screen."""

    def __init__(self):
        pixmap = QPixmap(600, 380)
        pixmap.fill(QColor("#06080d"))
        super().__init__(pixmap)
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)

        self._progress = 0
        self._status = "Initializing..."

    def set_progress(self, value: int, status: str = ""):
        self._progress = value
        if status:
            self._status = status
        self.repaint()

    def drawContents(self, painter: QPainter):
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background gradient
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor("#06080d"))
        grad.setColorAt(0.5, QColor("#0c1225"))
        grad.setColorAt(1.0, QColor("#0d0818"))
        painter.fillRect(0, 0, w, h, grad)

        # Subtle grid pattern
        painter.setPen(QPen(QColor(255, 255, 255, 8), 1))
        for i in range(0, w, 30):
            painter.drawLine(i, 0, i, h)
        for i in range(0, h, 30):
            painter.drawLine(0, i, w, i)

        # Glow circle behind logo
        glow_grad = QLinearGradient(w / 2 - 60, h / 2 - 100, w / 2 + 60, h / 2 - 20)
        glow_grad.setColorAt(0, QColor(59, 130, 246, 30))
        glow_grad.setColorAt(1, QColor(139, 92, 246, 20))
        painter.setBrush(glow_grad)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(w / 2 - 50), 50, 100, 100)

        # Logo "A"
        logo_grad = QLinearGradient(w / 2 - 20, 70, w / 2 + 20, 130)
        logo_grad.setColorAt(0, QColor("#3b82f6"))
        logo_grad.setColorAt(1, QColor("#8b5cf6"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(logo_grad)
        painter.drawRoundedRect(int(w / 2 - 28), 72, 56, 56, 14, 14)

        painter.setPen(QColor("white"))
        font = QFont("Helvetica Neue", 26)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(int(w / 2 - 28), 72, 56, 56, Qt.AlignCenter, "A")

        # Brand name
        painter.setPen(QColor("#f1f5f9"))
        font = QFont("Helvetica Neue", 28)
        font.setWeight(QFont.Weight.ExtraBold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 6)
        painter.setFont(font)
        painter.drawText(0, 150, w, 45, Qt.AlignCenter, "AURION")

        # Sub brand
        painter.setPen(QColor("#64748b"))
        font = QFont("Helvetica Neue", 11)
        font.setWeight(QFont.Weight.Medium)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 8)
        painter.setFont(font)
        painter.drawText(0, 195, w, 25, Qt.AlignCenter, "MARKETS")

        # Tagline
        painter.setPen(QColor("#475569"))
        font = QFont("Helvetica Neue", 10)
        painter.setFont(font)
        painter.drawText(0, 230, w, 20, Qt.AlignCenter, "Trading Intelligence Platform")

        # Progress bar background
        bar_y = 290
        bar_x = 100
        bar_w = w - 200
        bar_h = 4

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1e293b"))
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 2, 2)

        # Progress bar fill
        fill_w = int(bar_w * self._progress / 100)
        if fill_w > 0:
            bar_grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            bar_grad.setColorAt(0, QColor("#3b82f6"))
            bar_grad.setColorAt(1, QColor("#8b5cf6"))
            painter.setBrush(bar_grad)
            painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 2, 2)

        # Status text
        painter.setPen(QColor("#64748b"))
        font = QFont("Helvetica Neue", 9)
        painter.setFont(font)
        painter.drawText(0, 305, w, 20, Qt.AlignCenter, self._status)

        # Version
        painter.setPen(QColor("#334155"))
        font = QFont("Helvetica Neue", 8)
        painter.setFont(font)
        painter.drawText(0, h - 30, w, 20, Qt.AlignCenter, "v4.2.1  ·  © 2014 – 2026 Aurion Markets Ltd.")

        # Border
        painter.setPen(QPen(QColor("#1e293b"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 12, 12)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Aurion Markets")
    app.setOrganizationName("Aurion Markets Ltd.")

    # Show splash
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # Simulate loading stages
    stages = [
        (10, "Loading core modules..."),
        (25, "Initializing prediction engine..."),
        (40, "Connecting to market data feeds..."),
        (55, "Loading technical indicators..."),
        (70, "Preparing chart renderer..."),
        (85, "Building user interface..."),
        (95, "Almost ready..."),
    ]

    from ui.theme import get_stylesheet

    current_stage = [0]

    def advance_loading():
        if current_stage[0] < len(stages):
            pct, status = stages[current_stage[0]]
            splash.set_progress(pct, status)
            current_stage[0] += 1
            app.processEvents()

    # Load stages with delays
    load_timer = QTimer()
    load_timer.setInterval(200)
    load_timer.timeout.connect(advance_loading)
    load_timer.start()

    # Process all loading steps
    import time
    for _ in range(len(stages) + 3):
        app.processEvents()
        time.sleep(0.18)

    load_timer.stop()
    splash.set_progress(100, "Launching Aurion Markets...")
    app.processEvents()

    # Apply global stylesheet
    app.setStyleSheet(get_stylesheet())

    # Build main window
    from ui.main_window import MainWindow
    from ui.dashboard_page import DashboardPage
    from ui.analysis_page import AnalysisPage
    from ui.scanner_page import ScannerPage
    from ui.signals_page import SignalsPage
    from ui.history_page import HistoryPage

    window = MainWindow()
    window.add_page(DashboardPage())
    window.add_page(AnalysisPage())
    window.add_page(ScannerPage())
    window.add_page(SignalsPage())
    window.add_page(HistoryPage())

    splash.set_progress(100, "Ready")
    app.processEvents()

    window.show()
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
