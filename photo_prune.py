import sys
import logging
import os
from typing import Callable
from PySide6 import QtCore, QtWidgets, QtGui

from image_viewer import ImageViewer
from landing import Landing
from stylesheet import stylesheet


class PhotoPrune(QtWidgets.QWidget):
    layout: Callable[..., QtWidgets.QLayout] | QtWidgets.QLayout
    image_viewer: ImageViewer | None = None
    landing: Landing

    def __init__(self, parent=None):
        super(PhotoPrune, self).__init__(parent)

        self.setStyleSheet(stylesheet)
        self.setWindowTitle("Photo Prune")

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.landing = Landing()
        self.layout.addWidget(self.landing)

        self.fix_size_to_min()

        # Fullscreen bindings
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_F11), self, self._fullscreen
        )
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Escape), self, self._esc)

        self.landing.confirm_sig.connect(self._switch_to_viewer)

        self._set_up_image_viewer()

    def _set_up_image_viewer(self):
        """Because we might tear it down"""
        self.image_viewer = ImageViewer()
        self.layout.addWidget(self.image_viewer)
        self.image_viewer.hide()
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

    def fix_size_to_min(self):
        self.setFixedSize(self.minimumSizeHint())

    @QtCore.Slot(str, bool, bool)
    def _switch_to_viewer(
        self, folder: str, include_std_img: bool, include_raw_img: bool
    ):
        def _err(m: str):
            _msg_box = QtWidgets.QMessageBox()
            _msg_box.setWindowTitle("Error")
            _msg_box.setText(m)
            _msg_box.addButton(QtWidgets.QMessageBox.StandardButton.Ok)
            _msg_box.exec()

        if not os.path.isdir(folder):
            logging.error("Not a valid folder")
            _err("Folder doesn't exist.")
            return

        self._set_up_image_viewer()
        if self.image_viewer is None:
            raise Exception

        if not include_std_img and not include_raw_img:
            _err("You must check one of the image format boxes.")
            return

        self.image_viewer.include_standard_images(include_std_img)
        self.image_viewer.include_raw_images(include_raw_img)

        try:
            self.image_viewer.load_folder(folder)
        except Exception as e:
            _err(str(e))
            return

        self.unfix_size()
        self.resize(1280, 720)
        self.image_viewer.gfxview_fill_space()
        self.landing.hide()
        self.image_viewer.show()

    @QtCore.Slot()
    def _switch_to_landing(self):
        # TODO: Img cleanup/viewer destruction
        self.fix_size_to_min()
        if self.image_viewer:
            self.image_viewer.hide()
        self.landing.show()


def set_up_logging():
    log_level_name = os.getenv("LOG_LEVEL")
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    log_level = logging.WARNING
    if log_level_name is not None and log_level_name in levels.keys():
        log_level = levels[log_level_name]

    logging.basicConfig(level=log_level)
    logging.info(f"Log level set to {logging.getLevelName(log_level)}")


if __name__ == "__main__":
    set_up_logging()
    app = QtWidgets.QApplication([])

    photo_prune = PhotoPrune()
    photo_prune.show()
    
    exit_code = app.exec()
    sys.exit(exit_code)
