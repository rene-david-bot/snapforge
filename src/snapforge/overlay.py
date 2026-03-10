from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class SelectionOverlay(QWidget):
    def __init__(self, screenshot: QPixmap, on_selected: Callable[[QPixmap], None]) -> None:
        super().__init__()
        self.screenshot = screenshot
        self.on_selected = on_selected

        self.origin: QPoint | None = None
        self.current: QPoint | None = None
        self.selection: QRect | None = None

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setCursor(Qt.CrossCursor)

        geom = QGuiApplication.primaryScreen().geometry() if QGuiApplication.primaryScreen() else self.screenshot.rect()
        self.setGeometry(geom)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.screenshot)

        # Darken everything.
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        # Restore selected area.
        if self.selection is not None:
            sel = self.selection.normalized().intersected(self.rect())
            if not sel.isNull():
                painter.drawPixmap(sel, self.screenshot, sel)
                painter.setPen(QPen(QColor("#f59e0b"), 2, Qt.SolidLine))
                painter.drawRect(sel)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() != Qt.LeftButton:
            return
        self.origin = event.position().toPoint()
        self.current = self.origin
        self.selection = QRect(self.origin, self.current)
        self.update()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self.origin is None:
            return
        self.current = event.position().toPoint()
        self.selection = QRect(self.origin, self.current)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() != Qt.LeftButton or self.selection is None:
            return

        sel = self.selection.normalized().intersected(self.rect())
        if sel.width() < 3 or sel.height() < 3:
            self.selection = None
            self.update()
            return

        crop = self.screenshot.copy(sel)
        self.close()
        self.on_selected(crop)
