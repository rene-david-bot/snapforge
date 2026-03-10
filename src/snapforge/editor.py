from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


@dataclass
class StrokeOp:
    points: List[QPoint] = field(default_factory=list)
    color: QColor = field(default_factory=lambda: QColor("#ef4444"))
    width: int = 3


@dataclass
class ShapeOp:
    # kind: rect | line | arrow
    kind: str
    start: QPoint
    end: QPoint
    color: QColor = field(default_factory=lambda: QColor("#22c55e"))
    width: int = 2


@dataclass
class TextOp:
    pos: QPoint
    text: str
    color: QColor = field(default_factory=lambda: QColor("#f8fafc"))
    size: int = 18


@dataclass
class PixelateOp:
    rect: QRect
    block: int = 12


class AnnotationCanvas(QWidget):
    TOOL_PEN = "pen"
    TOOL_RECT = "rect"
    TOOL_LINE = "line"
    TOOL_ARROW = "arrow"
    TOOL_TEXT = "text"
    TOOL_PIXELATE = "pixelate"

    def __init__(self, pixmap: QPixmap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base = pixmap
        self._tool = self.TOOL_PEN

        self._ops: list[object] = []
        self._redo: list[object] = []

        self._active_stroke: StrokeOp | None = None
        self._active_start: QPoint | None = None
        self._active_end: QPoint | None = None

        self.color = QColor("#ef4444")
        self.width = 3
        self.font_size = 18
        self.pixel_block = 12

        self.setFixedSize(self._base.size())
        self.setMouseTracking(True)

    def set_tool(self, tool: str) -> None:
        self._tool = tool

    def set_color(self, color: QColor) -> None:
        self.color = color

    def set_width(self, width: int) -> None:
        self.width = max(1, width)

    def set_font_size(self, size: int) -> None:
        self.font_size = max(8, size)

    def undo(self) -> None:
        if not self._ops:
            return
        self._redo.append(self._ops.pop())
        self.update()

    def redo(self) -> None:
        if not self._redo:
            return
        self._ops.append(self._redo.pop())
        self.update()

    def _clear_redo(self) -> None:
        self._redo.clear()

    @staticmethod
    def _draw_arrow(painter: QPainter, start: QPoint, end: QPoint, color: QColor, width: int) -> None:
        pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start, end)

        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1:
            return

        ux = dx / length
        uy = dy / length
        size = max(10, width * 4)

        # Two wing points for arrow head.
        lx = end.x() - ux * size - uy * (size * 0.5)
        ly = end.y() - uy * size + ux * (size * 0.5)
        rx = end.x() - ux * size + uy * (size * 0.5)
        ry = end.y() - uy * size - ux * (size * 0.5)

        painter.drawLine(end, QPoint(int(lx), int(ly)))
        painter.drawLine(end, QPoint(int(rx), int(ry)))

    @staticmethod
    def _pixelate_area(img: QImage, rect: QRect, block: int) -> QImage:
        r = rect.normalized().intersected(QRect(0, 0, img.width(), img.height()))
        if r.isNull() or r.width() < 2 or r.height() < 2:
            return img

        cut = img.copy(r)
        tiny_w = max(1, cut.width() // max(1, block))
        tiny_h = max(1, cut.height() // max(1, block))
        tiny = cut.scaled(tiny_w, tiny_h, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        pix = tiny.scaled(cut.width(), cut.height(), Qt.IgnoreAspectRatio, Qt.FastTransformation)

        p = QPainter(img)
        p.drawImage(r.topLeft(), pix)
        p.end()
        return img

    def _render_ops(self, painter: QPainter, ops: list[object]) -> None:
        for op in ops:
            if isinstance(op, StrokeOp):
                if len(op.points) < 2:
                    continue
                pen = QPen(op.color, op.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                for i in range(1, len(op.points)):
                    painter.drawLine(op.points[i - 1], op.points[i])

            elif isinstance(op, ShapeOp):
                if op.kind == "rect":
                    painter.setPen(QPen(op.color, op.width))
                    painter.drawRect(QRect(op.start, op.end).normalized())
                elif op.kind == "line":
                    painter.setPen(QPen(op.color, op.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    painter.drawLine(op.start, op.end)
                elif op.kind == "arrow":
                    self._draw_arrow(painter, op.start, op.end, op.color, op.width)

            elif isinstance(op, TextOp):
                painter.setPen(QPen(op.color, 1))
                font = QFont()
                font.setPointSize(op.size)
                painter.setFont(font)
                painter.drawText(op.pos, op.text)

    def _preview_ops(self) -> list[object]:
        out: list[object] = []
        if self._active_stroke is not None:
            out.append(self._active_stroke)

        if self._active_start is not None and self._active_end is not None:
            if self._tool in (self.TOOL_RECT, self.TOOL_LINE, self.TOOL_ARROW):
                out.append(
                    ShapeOp(
                        kind={
                            self.TOOL_RECT: "rect",
                            self.TOOL_LINE: "line",
                            self.TOOL_ARROW: "arrow",
                        }[self._tool],
                        start=self._active_start,
                        end=self._active_end,
                        color=self.color,
                        width=self.width,
                    )
                )
        return out

    def paintEvent(self, event) -> None:  # type: ignore[override]
        pix = self.render_result()
        painter = QPainter(self)
        painter.drawPixmap(0, 0, pix)

        if self._active_stroke is not None:
            self._render_ops(painter, [self._active_stroke])

        # Dashed preview for current drag op.
        if self._active_start is not None and self._active_end is not None and self._tool in (
            self.TOOL_RECT,
            self.TOOL_LINE,
            self.TOOL_ARROW,
            self.TOOL_PIXELATE,
        ):
            if self._tool == self.TOOL_PIXELATE:
                painter.setPen(QPen(QColor("#f59e0b"), 2, Qt.DashLine))
                painter.drawRect(QRect(self._active_start, self._active_end).normalized())
            else:
                pen = QPen(self.color, max(1, self.width), Qt.DashLine)
                painter.setPen(pen)
                shape = self._preview_ops()
                self._render_ops(painter, shape)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() != Qt.LeftButton:
            return

        p = event.position().toPoint()

        if self._tool == self.TOOL_TEXT:
            text, ok = QInputDialog.getText(self, "Insert text", "Text:")
            if ok and text.strip():
                self._ops.append(TextOp(pos=p, text=text, color=self.color, size=self.font_size))
                self._clear_redo()
                self.update()
            return

        if self._tool == self.TOOL_PEN:
            self._active_stroke = StrokeOp(points=[p], color=QColor(self.color), width=self.width)
        else:
            self._active_start = p
            self._active_end = p

        self.update()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        p = event.position().toPoint()

        if self._tool == self.TOOL_PEN and self._active_stroke is not None:
            self._active_stroke.points.append(p)
        elif self._active_start is not None:
            self._active_end = p

        self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() != Qt.LeftButton:
            return

        if self._tool == self.TOOL_PEN and self._active_stroke is not None:
            if len(self._active_stroke.points) > 1:
                self._ops.append(self._active_stroke)
                self._clear_redo()
            self._active_stroke = None

        elif self._active_start is not None and self._active_end is not None:
            if self._tool == self.TOOL_RECT:
                self._ops.append(ShapeOp("rect", self._active_start, self._active_end, QColor(self.color), self.width))
                self._clear_redo()
            elif self._tool == self.TOOL_LINE:
                self._ops.append(ShapeOp("line", self._active_start, self._active_end, QColor(self.color), self.width))
                self._clear_redo()
            elif self._tool == self.TOOL_ARROW:
                self._ops.append(ShapeOp("arrow", self._active_start, self._active_end, QColor(self.color), self.width))
                self._clear_redo()
            elif self._tool == self.TOOL_PIXELATE:
                self._ops.append(PixelateOp(QRect(self._active_start, self._active_end).normalized(), self.pixel_block))
                self._clear_redo()

            self._active_start = None
            self._active_end = None

        self.update()

    def render_result(self) -> QPixmap:
        # Compose all vector-like ops on top of base.
        composed = QPixmap(self._base)
        p = QPainter(composed)
        self._render_ops(p, self._ops)
        p.end()

        # Apply pixelation ops last, in order.
        img = composed.toImage()
        for op in self._ops:
            if isinstance(op, PixelateOp):
                img = self._pixelate_area(img, op.rect, op.block)

        return QPixmap.fromImage(img)


class EditorWindow(QMainWindow):
    def __init__(self, pixmap: QPixmap) -> None:
        super().__init__()
        self.setWindowTitle("SnapForge Editor")

        self.canvas = AnnotationCanvas(pixmap)

        tool_row = QHBoxLayout()
        self._add_tool_buttons(tool_row)
        self._add_style_controls(tool_row)

        hint = QLabel("Shortcuts: Ctrl+Z/Ctrl+Y/Ctrl+C/Ctrl+S | Esc")
        tool_row.addWidget(hint)
        tool_row.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(False)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addLayout(tool_row)
        layout.addWidget(scroll)

        self.setCentralWidget(root)
        self.resize(min(1500, self.canvas.width() + 60), min(950, self.canvas.height() + 120))

        self._bind_shortcuts()

    def _add_tool_buttons(self, row: QHBoxLayout) -> None:
        buttons = [
            ("Pen", AnnotationCanvas.TOOL_PEN),
            ("Rect", AnnotationCanvas.TOOL_RECT),
            ("Line", AnnotationCanvas.TOOL_LINE),
            ("Arrow", AnnotationCanvas.TOOL_ARROW),
            ("Text", AnnotationCanvas.TOOL_TEXT),
            ("Pixelate", AnnotationCanvas.TOOL_PIXELATE),
        ]
        for label, tool in buttons:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _=False, t=tool: self.canvas.set_tool(t))
            row.addWidget(btn)

        btn_undo = QPushButton("Undo")
        btn_redo = QPushButton("Redo")
        btn_copy = QPushButton("Copy")
        btn_save = QPushButton("Save")
        btn_undo.clicked.connect(self.canvas.undo)
        btn_redo.clicked.connect(self.canvas.redo)
        btn_copy.clicked.connect(self.copy_to_clipboard)
        btn_save.clicked.connect(self.save_png)

        for b in [btn_undo, btn_redo, btn_copy, btn_save]:
            row.addWidget(b)

    def _add_style_controls(self, row: QHBoxLayout) -> None:
        btn_color = QPushButton("Color")
        btn_color.clicked.connect(self.pick_color)

        width_spin = QSpinBox()
        width_spin.setRange(1, 24)
        width_spin.setValue(3)
        width_spin.valueChanged.connect(self.canvas.set_width)

        font_spin = QSpinBox()
        font_spin.setRange(8, 96)
        font_spin.setValue(18)
        font_spin.valueChanged.connect(self.canvas.set_font_size)

        pixel_spin = QSpinBox()
        pixel_spin.setRange(2, 64)
        pixel_spin.setValue(12)

        def on_pixel(v: int) -> None:
            self.canvas.pixel_block = v

        pixel_spin.valueChanged.connect(on_pixel)

        row.addWidget(btn_color)
        row.addWidget(QLabel("Width"))
        row.addWidget(width_spin)
        row.addWidget(QLabel("Font"))
        row.addWidget(font_spin)
        row.addWidget(QLabel("Pixel"))
        row.addWidget(pixel_spin)

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.canvas.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self.canvas.redo)
        QShortcut(QKeySequence("Ctrl+C"), self, activated=self.copy_to_clipboard)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_png)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def pick_color(self) -> None:
        color = QColorDialog.getColor(self.canvas.color, self, "Pick color")
        if color.isValid():
            self.canvas.set_color(color)

    def copy_to_clipboard(self) -> None:
        QApplication.clipboard().setPixmap(self.canvas.render_result())

    def save_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", "snapforge.png", "PNG Files (*.png)")
        if not path:
            return
        ok = self.canvas.render_result().save(path, "PNG")
        if not ok:
            QMessageBox.critical(self, "Save failed", f"Could not save file: {path}")
