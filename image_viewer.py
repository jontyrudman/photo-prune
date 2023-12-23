import logging
from typing import Callable
from PySide6 import QtWidgets, QtGui, QtCore


class ImageViewer(QtWidgets.QWidget):
    layout: Callable[..., QtWidgets.QLayout] | QtWidgets.QLayout

    _image: QtGui.QImage | None = None
    _img_scale: float = 1.0
    _gfxview: QtWidgets.QGraphicsView | None = None
    _pixmap_in_scene: QtWidgets.QGraphicsPixmapItem | None = None
    _last_window_state: QtCore.Qt.WindowState | None = None

    back_to_landing_sig = QtCore.Signal()
    fullscreen_sig = QtCore.Signal()

    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self._img_scale = 1.0

        self._set_up_gfxview()
        if self._gfxview is None:
            raise Exception

        self.layout.addWidget(self._gfxview)

        # Event callbacks
        self.resizeEvent = self._on_resize
        self.contextMenuEvent = self._on_context

        self._set_up_shortcuts()

    def _set_up_gfxview(self):
        self._gfxview = QtWidgets.QGraphicsView()
        self._gfxview.setBackgroundRole(QtGui.QPalette.ColorRole.Base)
        self._gfxview.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Ignored
        )
        self._gfxview.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self._gfxview.setTransformationAnchor(
            QtWidgets.QGraphicsView.ViewportAnchor.NoAnchor
        )

        self._gfxview.setViewportMargins(20, 20, 20, 20)

        self._gfxview.wheelEvent = self._on_scroll
        self._gfxview.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._gfxview.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

    def _set_up_shortcuts(self):
        # Zoom bindings
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_Equal),
            self,
            lambda: self.fit_to_viewport(),
        )
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_Plus), self, lambda: self._scale(1.1)
        )
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_Minus), self, lambda: self._scale(0.9)
        )

        # We get Shift+Arrow translate for free

        # Override Arrow translate and put in next and prev
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_Right),
            self,
            lambda: print("Next image"),
        )
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_Left), self, lambda: print("Prev image")
        )
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Up), self, None)
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Down), self, None)
        # TODO: Implement next and prev image funcs

        # Discard photo
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_D), self, lambda: print("Discard")
        )
        # TODO: Implement discard func

    def _on_context(self, event: QtGui.QContextMenuEvent):
        self.menu = QtWidgets.QMenu(self)

        self.menu.addAction("Discard this image")
        self.menu.addSeparator()

        self.menu.addAction("Prune another folder", self.back_to_landing_sig.emit)
        self.menu.addAction("Open discarded in file viewer")
        self.menu.addAction("Toggle fullscreen", self.fullscreen_sig.emit)
        self.menu.addAction("Help")

        self.menu.exec(event.globalPos())

    def _on_resize(self, event: QtGui.QResizeEvent):
        if self._gfxview is None or self._gfxview.scene() is None:
            return

        if (
            self._gfxview.scene().width() < self._gfxview.viewport().width()
            or self._gfxview.scene().height() < self._gfxview.viewport().height()
        ):
            self.fit_to_viewport()

    def _on_scroll(self, event: QtGui.QWheelEvent):
        _d = event.angleDelta().y()
        _scale_multiplier = 0.2
        self._scale(1 + ((_d / 120) * _scale_multiplier))

    def gfxview_fill_space(self):
        if self._gfxview is None:
            raise Exception
        self._gfxview.resize(self.parentWidget().size())
        self._gfxview.viewport().resize(self._gfxview.maximumViewportSize())

    def load_file(self, fileName):
        reader = QtGui.QImageReader(fileName)
        reader.setAutoTransform(True)
        new_image = reader.read()
        native_filename = QtCore.QDir.toNativeSeparators(fileName)
        if new_image.isNull():
            error = reader.errorString()
            QtWidgets.QMessageBox.information(
                self,
                QtGui.QGuiApplication.applicationDisplayName(),
                f"Cannot load {native_filename}: {error}",
            )
            return False
        self._set_image(new_image)
        self.setWindowFilePath(fileName)

        if self._image is None:
            raise Exception

        w = self._image.width()
        h = self._image.height()
        d = self._image.depth()
        color_space = self._image.colorSpace()
        description = color_space.description() if color_space.isValid() else "unknown"
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
        self._pixmap_in_scene = gfxscene.addPixmap(QtGui.QPixmap.fromImage(self._image))
        self._gfxview.setScene(gfxscene)
        self.fit_to_viewport()

    def _translate(self, x, y):
        if self._gfxview is None:
            raise Exception

        self._gfxview.translate(x, y)

    def fit_to_viewport(self):
        if self._gfxview is None:
            logging.debug("No gfxview to fit a viewport to")
            return

        self._fit_to_size(
            self._gfxview.viewport().width(),
            self._gfxview.viewport().height(),
        )

    def _fit_to_size(self, w, h):
        if (
            self._image is None
            or self._gfxview is None
            or self._pixmap_in_scene is None
        ):
            raise Exception

        sf_width = w / self._image.width()
        sf_height = h / self._image.height()
        self._img_scale = min(sf_width, sf_height)
        scene = self._gfxview.scene()

        self._log_view_sizes()

        new_width = self._image.width() * self._img_scale
        new_height = self._image.height() * self._img_scale

        self._pixmap_in_scene.setPixmap(
            QtGui.QPixmap.fromImage(self._image).scaled(
                new_width,
                new_height,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        )
        self._gfxview.centerOn(self._pixmap_in_scene)
        scene.setSceneRect(scene.itemsBoundingRect())

    def _scale(self, scale_factor):
        if (
            self._image is None
            or self._gfxview is None
            or self._pixmap_in_scene is None
        ):
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
            and self._image.height() * new_img_scale < vw_height
        ) and scale_factor < 1:
            logging.debug(
                "New dimensions would be smaller than viewport, fitting to viewport instead"
            )
            self.fit_to_viewport()
            return

        self._img_scale = new_img_scale

        scene = self._gfxview.scene()

        old_scene_dx = self._gfxview.viewportTransform().dx() - viewport.width() / 2
        old_scene_dy = self._gfxview.viewportTransform().dy() - viewport.height() / 2
        new_scene_dx = old_scene_dx * scale_factor
        new_scene_dy = old_scene_dy * scale_factor

        self._pixmap_in_scene.setPixmap(
            QtGui.QPixmap.fromImage(self._image).scaled(
                self._image.width() * self._img_scale,
                self._image.height() * self._img_scale,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        )

        scene.setSceneRect(scene.itemsBoundingRect())
        self._gfxview.centerOn(-new_scene_dx, -new_scene_dy)

        self._log_view_sizes()

    def _log_view_sizes(self):
        logging.debug("GFXVIEW size", self._gfxview.size()) if self._gfxview else None
        logging.debug(
            "SCENE size", self._gfxview.scene().sceneRect()
        ) if self._gfxview else None
        logging.debug(
            "PIXMAP size", self._pixmap_in_scene.pixmap().size()
        ) if self._pixmap_in_scene else None
