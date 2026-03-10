from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from snapforge.capture import capture_primary_screen
from snapforge.editor import EditorWindow
from snapforge.overlay import SelectionOverlay


class AppController:
    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.overlay: SelectionOverlay | None = None
        self.editor: EditorWindow | None = None

    def start_capture(self) -> None:
        screenshot = capture_primary_screen()

        def handle_selected(crop):
            self.editor = EditorWindow(crop)
            self.editor.show()

        self.overlay = SelectionOverlay(screenshot, on_selected=handle_selected)
        self.overlay.showFullScreen()


def main() -> int:
    app = QApplication(sys.argv)
    controller = AppController(app)
    controller.start_capture()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
