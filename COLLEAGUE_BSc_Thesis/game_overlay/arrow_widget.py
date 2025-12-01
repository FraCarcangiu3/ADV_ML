#!/usr/bin/env python3

import sys
import logging
import signal
import setproctitle
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QPainter, QPolygon
from PySide6.QtWidgets import QApplication, QWidget

# Arrow names for the 8 positions
ARROW_NAMES = [
    "top_left", "top", "top_right",
    "right", "bottom_right", "bottom",
    "bottom_left", "left"
]

setproctitle.setproctitle("ArrowsWidget")

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger("arrows_overlay")

class ArrowWidget(QWidget):
    """Small widget drawing a white triangular arrow pointing inward."""
    def __init__(self, direction: str, size: int = 28, color: QColor = QColor("white"), parent=None):
        super().__init__(parent)
        self.direction = direction
        self.size = size
        self.color = color

        # The widget is a small transparent square containing the arrow
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.hide()

    def paintEvent(self, event):
        """Draws the arrow as a triangle using QPainter."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self.color)
        s = self.size

        # Define triangle coordinates depending on the direction
        dirs = {
            "top_left":      [QPoint(0, s), QPoint(int(s*0.7), s), QPoint(0, int(s*0.3))],
            "top":           [QPoint(0, s), QPoint(s, s), QPoint(int(s/2), int(s*0.1))],
            "top_right":     [QPoint(0, s), QPoint(s, int(s*0.3)), QPoint(s, s)],
            "right":         [QPoint(0, 0), QPoint(0, s), QPoint(int(s*0.9), int(s/2))],
            "bottom_right":  [QPoint(0, 0), QPoint(s, int(s*0.7)), QPoint(s, 0)],
            "bottom":        [QPoint(0, 0), QPoint(int(s/2), int(s*0.9)), QPoint(s, 0)],
            "bottom_left":   [QPoint(0, 0), QPoint(0, int(s*0.7)), QPoint(int(s*0.7), 0)],
            "left":          [QPoint(int(s*0.1), int(s/2)), QPoint(s, 0), QPoint(s, s)],
        }
        p.drawPolygon(QPolygon(dirs[self.direction]))


class BackgroundWindow(QWidget):
    """Fullscreen black window always kept below all others, showing 8 arrows."""
    def __init__(self):
        super().__init__()

        # --- Window setup ---
        self.setWindowTitle("Background Black Window")
        log.info("Creating background window (always below other windows)…")

        # Window flags: borderless regular window (shows in Dock/App Switcher), always below
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Window  # regular app window so it appears in the Dock / app switcher
            | Qt.WindowStaysOnBottomHint
        )

        # Attributes: allow normal activation and interaction (do not hide on focus change)
        # (No WA_ShowWithoutActivating, no TransparentForMouseEvents)

        # Black background
        self.setStyleSheet("background-color: black;")

        # Make it fullscreen
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # --- Arrows setup ---
        self.arrow_size = 40
        self.margin = 15
        self.arrows = {
            name: ArrowWidget(name, self.arrow_size, QColor("white"), self)
            for name in ARROW_NAMES
        }

        # Position arrows and show the window
        self.position_arrows()
        self.show()
        log.info("Background window shown.")

    def position_arrows(self):
        """Position all 8 arrows on screen (corners and sides)."""
        g = self.geometry()
        W, H = g.width(), g.height()
        s, m = self.arrow_size, self.margin

        positions = {
            "top_left":      QPoint(m, m),
            "top":           QPoint((W - s)//2, m),
            "top_right":     QPoint(W - s - m, m),
            "right":         QPoint(W - s - m, (H - s)//2),
            "bottom_right":  QPoint(W - s - m, H - s - m),
            "bottom":        QPoint((W - s)//2, H - s - m),
            "bottom_left":   QPoint(m, H - s - m),
            "left":          QPoint(m, (H - s)//2),
        }

        for name, widget in self.arrows.items():
            widget.move(positions[name])
        log.debug("Arrows positioned.")

    def show_arrow(self, name: str, visible: bool = True):
        """Show or hide a specific arrow by name."""
        log.info(f"Set arrow '{name}' visible={visible}")
        if name in self.arrows:
            (self.arrows[name].show if visible else self.arrows[name].hide)()

    def show_all(self):
        """Show all arrows."""
        log.info("Showing all arrows…")
        for w in self.arrows.values():
            w.show()

    def hide_all(self):
        """Hide all arrows."""
        log.info("Hiding all arrows…")
        for w in self.arrows.values():
            w.hide()

    def closeEvent(self, event):
        log.info("Close event received — shutting down.")
        return super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    log.info("Starting arrows overlay… Press Ctrl+C in the terminal to quit.")
    QApplication.setQuitOnLastWindowClosed(True)
    # Optional: avoid native menu bar on macOS if the attribute exists (Qt version-safe)
    if hasattr(Qt, "AA_DontUseNativeMenuBar"):
        app.setAttribute(Qt.AA_DontUseNativeMenuBar, True)

    def _handle_signal(signum, frame):
        names = {getattr(signal, n): n for n in dir(signal) if n.startswith('SIG')}
        sig_name = names.get(signum, str(signum))
        log.info(f"Signal {sig_name} received — exiting…")
        # Use the Qt-safe way to quit from signal handler
        app.quit()

    try:
        signal.signal(signal.SIGINT, _handle_signal)
    except Exception:
        pass
    try:
        signal.signal(signal.SIGTERM, _handle_signal)
    except Exception:
        pass

    window = BackgroundWindow()
    window.show_all()  # Show all arrows immediately

    rc = 0
    try:
        rc = app.exec()
    except KeyboardInterrupt:
        log.info("KeyboardInterrupt — exiting…")
    finally:
        log.info(f"Event loop exited (code={rc}). Bye.")
        sys.exit(rc)


if __name__ == "__main__":
    main()
