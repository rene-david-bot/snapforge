from __future__ import annotations

from PySide6.QtGui import QGuiApplication, QPixmap


def capture_primary_screen() -> QPixmap:
    """Capture the full primary screen as a QPixmap."""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        raise RuntimeError("No primary screen available")
    return screen.grabWindow(0)
