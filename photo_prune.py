import sys
from typing import Callable
from PySide6 import QtCore, QtWidgets, QtGui

from image_viewer import ImageViewer
from landing import Landing
from stylesheet import stylesheet


class PhotoPrune(QtWidgets.QWidget):
    layout: Callable[..., QtWidgets.QLayout] | QtWidgets.QLayout
    image_viewer: ImageViewer
    landing: Landing

    def __init__(self, parent=None):
        super(PhotoPrune, self).__init__(parent)
        self.setStyleSheet(stylesheet)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.landing = Landing(self)
        self.image_viewer = ImageViewer(self)
        self.image_viewer.hide()
        self.layout.addWidget(self.image_viewer)

        self.layout.addWidget(self.landing)

        # Fullscreen bindings
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_F11), self, self.fullscreen)
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Escape), self, self._esc)

    def windowState(self):
        return super().windowState()

    def fullscreen(self):
        if self.windowState() == QtCore.Qt.WindowState.WindowFullScreen:
            if self._last_window_state is not None:
                self.setWindowState(self._last_window_state)
            else:
                self.setWindowState(QtCore.Qt.WindowState.WindowNoState)
        else:
            self._last_window_state = self.windowState()
            self.setWindowState(QtCore.Qt.WindowState.WindowFullScreen)

    def _esc(self):
        if self.windowState() == QtCore.Qt.WindowState.WindowFullScreen:
            if self._last_window_state is not None:
                self.setWindowState(self._last_window_state)
            else:
                self.setWindowState(QtCore.Qt.WindowState.WindowNoState)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    photo_prune = PhotoPrune()
    photo_prune.resize(1280, 720)
    photo_prune.show()
    photo_prune.image_viewer.load_file("test-pic.jpg")

    sys.exit(app.exec())
