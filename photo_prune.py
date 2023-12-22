import sys
import logging
from typing import Callable
from PySide6 import QtCore, QtWidgets, QtGui

class ImageViewer(QtWidgets.QWidget):
    layout: Callable[..., QtWidgets.QLayout] | QtWidgets.QLayout

    _image: QtGui.QImage | None = None
    _img_scale: float = 1.0
    _gfxview: QtWidgets.QGraphicsView | None = None
    _pixmap_in_scene: QtWidgets.QGraphicsPixmapItem | None = None
    _last_window_state: QtCore.Qt.WindowState | None = None

    def __init__(self, parent = None):
        super(ImageViewer, self).__init__(parent)

        self.layout = QtWidgets.QVBoxLayout(self)

        self._img_scale = 1.0
        self._gfxview = QtWidgets.QGraphicsView()
        self._gfxview.setBackgroundRole(QtGui.QPalette.ColorRole.Base)
        self._gfxview.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,
                                       QtWidgets.QSizePolicy.Policy.Ignored)
        self._gfxview.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self._gfxview.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.NoAnchor)

        self._gfxview.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)

        self._gfxview.wheelEvent = self._on_scroll
        self.resizeEvent = self._on_resize
        self.contextMenuEvent = self._on_context

        self.layout.addWidget(self._gfxview)

        # Fullscreen bindings
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_F11), self, self._fullscreen)
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Escape), self, self._esc)

        # Zoom bindings
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Equal), self, lambda: self._fit_to_viewport())
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Plus), self, lambda: self._scale(1.1))
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Minus), self, lambda: self._scale(0.9))

        # We get Shift+Arrow translate for free

        # Override Arrow translate and put in next and prev
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Right), self, lambda: print("Next image"))
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Left), self, lambda: print("Prev image"))
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Up), self, None)
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Down), self, None)
        # TODO: Implement next and prev image funcs

        # Discard photo
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_D), self, lambda: print("Discard"))
        # TODO: Implement discard func

    def _on_context(self, event: QtGui.QContextMenuEvent):
        menu = QtWidgets.QMenu(self)

        menu.addAction("Discard this image")
        menu.addSeparator()

        menu.addAction("Prune another folder")
        menu.addAction("Open discarded in file viewer")

        if self.windowState() == QtCore.Qt.WindowState.WindowFullScreen:
            menu.addAction("Exit fullscreen", self._fullscreen)
        else:
            menu.addAction("Fullscreen", self._fullscreen)

        menu.addAction("Help")

        menu.exec(event.globalPos())

    def _on_resize(self, event: QtGui.QResizeEvent):
        if self._gfxview is None or self._gfxview.scene() is None:
            return

        if (
            self._gfxview.scene().width() < self._gfxview.viewport().width()
            or self._gfxview.scene().height() < self._gfxview.viewport().height()
        ):
            self._fit_to_size(self._gfxview.width(), self._gfxview.height())

    def _on_scroll(self, event: QtGui.QWheelEvent):
        _d = event.angleDelta().y()
        _scale_multiplier = 0.2
        self._scale(1 + ((_d / 120) * _scale_multiplier))

    def load_file(self, fileName):
        reader = QtGui.QImageReader(fileName)
        reader.setAutoTransform(True)
        new_image = reader.read()
        native_filename = QtCore.QDir.toNativeSeparators(fileName)
        if new_image.isNull():
            error = reader.errorString()
            QtWidgets.QMessageBox.information(self, QtGui.QGuiApplication.applicationDisplayName(),
                                    f"Cannot load {native_filename}: {error}")
            return False
        self._set_image(new_image)
        self.setWindowFilePath(fileName)

        if self._image is None:
            raise Exception

        w = self._image.width()
        h = self._image.height()
        d = self._image.depth()
        color_space = self._image.colorSpace()
        description = color_space.description() if color_space.isValid() else 'unknown'
        message = f'Opened "{native_filename}", {w}x{h}, Depth: {d} ({description})'
        logging.info(message)
        return True

    def _set_image(self, new_image):
        if self._gfxview is None:
            raise Exception

        self._image = new_image
        if self._image.colorSpace().isValid():
            self._image.convertToColorSpace(QtGui.QColorSpace.NamedColorSpace.SRgb)

        sf_width = self._gfxview.viewport().width() / self._image.width()
        sf_height = self._gfxview.viewport().height() / self._image.height()
        self._img_scale = min(sf_width, sf_height)

        gfxscene = QtWidgets.QGraphicsScene()
        self._pixmap_in_scene = gfxscene.addPixmap(QtGui.QPixmap.fromImage(self._image).scaled(
            self._image.width() * self._img_scale - 10,
            self._image.height() * self._img_scale - 10,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        ))
        self._gfxview.setScene(gfxscene)

    def _translate(self, x, y):
        if self._gfxview is None:
            raise Exception

        self._gfxview.translate(x, y)

    def _fit_to_viewport(self):
        if self._gfxview is None:
            raise Exception

        self._fit_to_size(self._gfxview.width(), self._gfxview.height())

    def _fit_to_size(self, w, h):
        if self._image is None or self._gfxview is None or self._pixmap_in_scene is None:
            raise Exception

        sf_width = w / self._image.width()
        sf_height = h / self._image.height()
        self._img_scale = min(sf_width, sf_height)
        scene = self._gfxview.scene()

        self._log_view_sizes()

        new_width = (self._image.width() * self._img_scale)
        new_height = self._image.height() * self._img_scale

        self._pixmap_in_scene.setPixmap(QtGui.QPixmap.fromImage(self._image).scaled(
            new_width - 10,
            new_height - 10,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        ))
        self._gfxview.centerOn(self._pixmap_in_scene)
        scene.setSceneRect(scene.itemsBoundingRect())

    def _scale(self, scale_factor):
        if self._image is None or self._gfxview is None or self._pixmap_in_scene is None:
            return

        new_img_scale = self._img_scale * scale_factor
        if new_img_scale > 2:
            logging.debug("Scale too high", new_img_scale)
            return

        viewport = self._gfxview.viewport()
        vw_width = viewport.width()
        vw_height = viewport.height()
        if (
            self._image.width() * new_img_scale < vw_width
            or self._image.height() * new_img_scale < vw_height
        ) and scale_factor < 1:
            logging.debug("New dimensions would be smaller than viewport, fitting to viewport instead")
            self._fit_to_viewport()
            return

        self._img_scale = new_img_scale

        scene = self._gfxview.scene()

        old_scene_dx = self._gfxview.viewportTransform().dx() - viewport.width() / 2
        old_scene_dy = self._gfxview.viewportTransform().dy() - viewport.height() / 2
        new_scene_dx = old_scene_dx * scale_factor
        new_scene_dy = old_scene_dy * scale_factor

        self._pixmap_in_scene.setPixmap(QtGui.QPixmap.fromImage(self._image).scaled(
            self._image.width() * self._img_scale,
            self._image.height() * self._img_scale,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        ))

        scene.setSceneRect(scene.itemsBoundingRect())
        self._gfxview.centerOn(-new_scene_dx, -new_scene_dy)

        self._log_view_sizes()

    def _log_view_sizes(self):
        logging.debug("GFXVIEW size", self._gfxview.size()) if self._gfxview else None
        logging.debug("SCENE size", self._gfxview.scene().sceneRect()) if self._gfxview else None
        logging.debug("PIXMAP size", self._pixmap_in_scene.pixmap().size()) if self._pixmap_in_scene else None

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


stylesheet = """
ImageViewer {
    background-color: #ffffff;
}

ImageViewer QGraphicsView {
    background-color: #ffffff;
}

ImageViewer QScrollBar {
    background-color: #ffffff;
}

ImageViewer QAbstractScrollArea::corner {
    border: none;
}

ImageViewer QScrollBar::handle {
    background: #ffffff;
    border: 1px solid gray;
}

ImageViewer QScrollBar::add-line {
    border: none;
    background: none;
}

ImageViewer QScrollBar::sub-line {
    border: none;
    background: none;
}

ImageViewer QMenu {
    background-color: black;
    border: 1px solid #222;
}

ImageViewer QMenu::item {
    background-color: black;
    padding: 5px 10px;
}

ImageViewer QMenu::item::selected {
    background-color: #222;
}

ImageViewer QMenu::separator {
    height: 15px;
}
"""

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = ImageViewer()
    widget.resize(1280, 720)
    widget.setStyleSheet(stylesheet)
    widget.show()
    widget.load_file("test-pic.jpg")

    sys.exit(app.exec())
