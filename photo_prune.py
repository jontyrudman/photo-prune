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

        self.landing = Landing()
        self.image_viewer = ImageViewer()
        self.layout.addWidget(self.landing)
        self.layout.addWidget(self.image_viewer)
        self.image_viewer.hide()

        # Fullscreen bindings
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_F11), self, self._fullscreen
        )
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Escape), self, self._esc)

        self.landing.confirm_button.clicked.connect(self._switch_to_viewer)
        self.image_viewer.back_to_landing_sig.connect(self._switch_to_landing)
        self.image_viewer.fullscreen_sig.connect(self._fullscreen)

    def _fullscreen(self):
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

    def unfix_size(self):
        self.setMinimumSize(QtCore.QSize(0, 0))
        self.setMaximumSize(QtCore.QSize(16777215, 16777215))

    @QtCore.Slot()
    def _switch_to_viewer(self):
        self.image_viewer.load_file("test-pic.jpg")
        self.unfix_size()
        self.resize(1280, 720)
        self.image_viewer.gfxview_fill_space()
        self.landing.hide()
        self.image_viewer.show()
        # TODO: Send a folder of photos

    @QtCore.Slot()
    def _switch_to_landing(self):
        # TODO: Img cleanup/viewer destruction
        self.image_viewer.hide()
        self.landing.show()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    photo_prune = PhotoPrune()
    photo_prune.show()

    sys.exit(app.exec())
