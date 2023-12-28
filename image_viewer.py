import functools
import asyncio
import os
import logging
import platform
import subprocess
from typing import Callable, Coroutine
from PySide6 import QtWidgets, QtGui, QtCore


# Viewport margins left, top, right, bottom
PHOTO_MARGINS = [20, 20, 20, 20]

ACCEPTED_FILE_EXTENSIONS = {
    "standard": [".jpg", ".png", ".jpeg"],
    "raw": [".nef", ".raf", ".cr2", ".tiff"],  # For now
}

IMAGE_PRELOAD_MAX = 16
IMAGE_LOAD_DISPLAY_TIMEOUT_S = 0.35


class NoMoreImages(QtWidgets.QWidget):
    _text: QtWidgets.QLabel | None = None
    _landing_button: QtWidgets.QPushButton | None = None

    landing_button_sig = QtCore.Signal()

    def __init__(self, parent=None):
        super(NoMoreImages, self).__init__(parent)

        self._text = QtWidgets.QLabel()
        self._text.setText("No images to display.")

        self._landing_button = QtWidgets.QPushButton()
        self._landing_button.setText("Return")
        self._landing_button.clicked.connect(self.landing_button_sig.emit)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._text)
        layout.addWidget(self._landing_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)


class Overlay(QtWidgets.QWidget):
    _filename_label: QtWidgets.QLabel | None = None
    _position_label: QtWidgets.QLabel | None = None

    def __init__(self, parent=None):
        super(Overlay, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignBottom)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(0)

        self._filename_label = QtWidgets.QLabel()
        self._position_label = QtWidgets.QLabel()

        layout.addWidget(self._filename_label)
        layout.addWidget(self._position_label, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_filename(self, filename: str | None):
        if self._filename_label is None:
            raise Exception

        self._filename_label.setText(filename or "")

    def set_position(self, pos: int = 1, total: int = 1):
        if self._position_label is None:
            raise Exception

        self._position_label.setText(f"{pos}/{total}")


class ReplaceableWaiter:
    _waiting_thread: QtCore.QThread | None = None
    _running_thread: QtCore.QThread | None = None

    def submit_thread(self, t: QtCore.QThread):
        t.finished.connect(self._thread_finished)

        # If there's a thread running, insert a waiting thread
        if self._running_thread:
            logging.debug("Replacing waiting QThread")
            self._waiting_thread = t

        # Otherwise if there's no thread running, insert a running thread
        else:
            logging.debug("Inserting running QThread")
            self._running_thread = t
            self._running_thread.start()

    def _thread_finished(self):
        if self._running_thread is None:
            return

        self._running_thread.deleteLater()
        logging.debug("Deleting finished QThread")
        self._running_thread = None

        # If there's a thread waiting, swap it out now we've run
        if self._waiting_thread:
            logging.debug("Replacing finished QThread")
            self._running_thread = self._waiting_thread
            self._waiting_thread = None
            self._running_thread.start()


class LoadFileThread(QtCore.QThread):
    result_ready = QtCore.Signal(QtGui.QImage)
    _read_fn: Callable | None = None

    def __init__(self, read_fn, parent=None):
        super().__init__(parent)
        self._read_fn = read_fn

    def run(self, *args):
        if not self._read_fn:
            return
        res = self._read_fn()
        self.result_ready.emit(res)


class PreloadFilesThread(QtCore.QThread):
    _preload_coros: list[Coroutine] = []

    def __init__(self, preload_coros: list = [], parent=None):
        super().__init__(parent)
        self._preload_coros = preload_coros

    def run(self, *args):
        for c in self._preload_coros:
            asyncio.run(c)


class GraphicsView(QtWidgets.QGraphicsView):
    _image: QtGui.QImage | None = None
    _img_scale: float = 1.0
    _pixmap_in_scene: QtWidgets.QGraphicsPixmapItem | None = None

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setBackgroundRole(QtGui.QPalette.ColorRole.Base)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Ignored
        )
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.NoAnchor)

        self.setViewportMargins(*PHOTO_MARGINS)

        self.wheelEvent = self._on_scroll
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def _on_scroll(self, event: QtGui.QWheelEvent):
        _d = event.angleDelta().y()
        _scale_multiplier = 0.2
        self.scale(1 + ((_d / 120) * _scale_multiplier))

    def fit_to_viewport(self):
        self._fit_to_size(
            self.viewport().width(),
            self.viewport().height(),
        )

    def scale(self, scale_factor):
        if self._image is None or self._pixmap_in_scene is None:
            return

        new_img_scale = self._img_scale * scale_factor
        if new_img_scale > 2:
            logging.debug("Scale too high", new_img_scale)
            return

        viewport = self.viewport()
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

        scene = self.scene()

        old_scene_dx = self.viewportTransform().dx() - viewport.width() / 2
        old_scene_dy = self.viewportTransform().dy() - viewport.height() / 2
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
        self.centerOn(-new_scene_dx, -new_scene_dy)

        self._log_view_sizes()

    def _log_view_sizes(self):
        logging.debug(f"GFXVIEW size {str(self.size())}")
        logging.debug(f"SCENE size {str(self.scene().sceneRect())}")
        logging.debug(
            f"PIXMAP size {str(self._pixmap_in_scene.pixmap().size())}"
        ) if self._pixmap_in_scene else None

    def _fill_parent(self):
        self.resize(self.parentWidget().size())
        self.viewport().resize(self.maximumViewportSize())

    def _fit_to_size(self, w, h):
        if self._image is None or self._pixmap_in_scene is None:
            raise Exception

        sf_width = w / self._image.width()
        sf_height = h / self._image.height()
        self._img_scale = min(sf_width, sf_height)
        scene = self.scene()

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
        self.centerOn(self._pixmap_in_scene)
        scene.setSceneRect(scene.itemsBoundingRect())

    @functools.lru_cache(maxsize=IMAGE_PRELOAD_MAX)
    def qimage_from_file(self, fpath: str):
        logging.debug(f"Reading image from {fpath}...")
        reader = QtGui.QImageReader(fpath)
        reader.setAutoTransform(True)
        new_image = reader.read()
        native_filename = QtCore.QDir.toNativeSeparators(fpath)
        if new_image.isNull():
            error = reader.errorString()
            QtWidgets.QMessageBox.information(
                self,
                QtGui.QGuiApplication.applicationDisplayName(),
                f"Cannot load {native_filename}: {error}",
            )
            raise Exception

        return new_image

    def set_image(self, new_image: QtGui.QImage):
        self._image = new_image
        if self._image.colorSpace().isValid():
            self._image.convertToColorSpace(QtGui.QColorSpace.NamedColorSpace.SRgb)

        sf_width = self.viewport().width() / self._image.width()
        sf_height = self.viewport().height() / self._image.height()
        self._img_scale = min(sf_width, sf_height)

        gfxscene = QtWidgets.QGraphicsScene()
        self._pixmap_in_scene = gfxscene.addPixmap(QtGui.QPixmap.fromImage(self._image))
        self.setScene(gfxscene)
        self.fit_to_viewport()

    def set_image_hidden(self, hidden: bool):
        if self._pixmap_in_scene:
            self._pixmap_in_scene.setVisible(not hidden)


class ImageViewer(QtWidgets.QWidget):
    _gfxview: GraphicsView | None = None
    _last_window_state: QtCore.Qt.WindowState | None = None

    _cwd: str | None = None
    _cwd_file_count: int = 0
    _ordered_files: list[str] = []
    # Index and path of current file
    _current_file: tuple[int, str] | None = None
    _include_standard_image_ext: bool = True
    _include_raw_image_ext: bool = False
    _time_image_last_loaded_s: float | None = None

    _no_images_layout: NoMoreImages | None = None
    _overlay: Overlay | None = None

    _load_image_thread_replaceable_waiter = ReplaceableWaiter()
    _preload_images_thread_replaceable_waiter = ReplaceableWaiter()

    back_to_landing_sig = QtCore.Signal()
    fullscreen_sig = QtCore.Signal()

    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)

        self._gfxview = GraphicsView()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._gfxview)

        # Event callbacks
        self.resizeEvent = self._on_resize
        self.contextMenuEvent = self._on_context

        self._set_up_shortcuts()
        self._set_up_no_images_layout()

        self._overlay = Overlay(self)

        self.setLayout(layout)

    def _set_up_no_images_layout(self):
        self._no_images_layout = NoMoreImages(self)
        self._no_images_layout.hide()
        self._no_images_layout.resize(self.size())
        self._no_images_layout.landing_button_sig.connect(self.back_to_landing_sig.emit)

    def _set_up_shortcuts(self):
        def scale(_sf: float):
            if not self._gfxview:
                return
            self._gfxview.scale(_sf)

        def fit_to_viewport():
            if not self._gfxview:
                return
            self._gfxview.fit_to_viewport()

        # Zoom bindings
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_Equal),
            self,
            fit_to_viewport,
        )
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_Plus), self, lambda: scale(1.1)
        )
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_Minus), self, lambda: scale(0.9)
        )
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_Underscore),
            self,
            lambda: scale(0.9),
        )

        # We get Shift+Arrow translate for free

        # Override Arrow translate and put in next and prev
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_Right),
            self,
            self._next_photo,
        )
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_Left), self, self._prev_photo
        )
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Up), self, None)
        QtGui.QShortcut(QtGui.QKeySequence(QtGui.Qt.Key.Key_Down), self, None)

        # Discard photo
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.Qt.Key.Key_D), self, self._discard_current_photo
        )

    def _on_context(self, event: QtGui.QContextMenuEvent):
        self.menu = QtWidgets.QMenu(self)

        self.menu.addAction("Discard this image", self._discard_current_photo)
        self.menu.addSeparator()

        self.menu.addAction("Open discard folder in file viewer", self._open_discarded)
        self.menu.addAction("Prune another folder", self.back_to_landing_sig.emit)
        self.menu.addAction("Toggle fullscreen", self.fullscreen_sig.emit)
        self.menu.addAction("Help")  # TODO

        self.menu.exec(event.globalPos())

    def _on_resize(self, event: QtGui.QResizeEvent):
        if self._no_images_layout is not None:
            self._no_images_layout.resize(self.size())

        if self._overlay is not None:
            self._overlay.resize(self.size())

        if self._gfxview is not None and self._gfxview.scene() is not None:
            if (
                self._gfxview.scene().width() < self._gfxview.viewport().width()
                or self._gfxview.scene().height() < self._gfxview.viewport().height()
            ):
                self._gfxview.fit_to_viewport()

    def load_file(self, fpath: str, index: int):
        if not self._gfxview:
            raise Exception

        if self._no_images_layout:
            self._no_images_layout.hide()

        if self._overlay:
            self._overlay.show()
            self._overlay.set_filename(f"{os.path.basename(fpath)} loading...")
            if self._current_file:
                self._overlay.set_position(
                    self._current_file[0] + 1, len(self._ordered_files)
                )

        def callback(_img: QtGui.QImage):
            # If it's a stale thread arriving late it won't match our _current_file index
            if self._current_file and index and index != self._current_file[0]:
                logging.debug("Stale image load detected; not setting image")
                return

            if not self._gfxview:
                raise Exception

            self._gfxview.set_image(_img)
            self._gfxview.set_image_hidden(False)
            self.setWindowFilePath(fpath)

            if self._overlay:
                if self._current_file:
                    self._overlay.set_filename(os.path.basename(self._current_file[1]))
                    self._overlay.set_position(
                        self._current_file[0] + 1, len(self._ordered_files)
                    )

            w = _img.width()
            h = _img.height()
            d = _img.depth()
            color_space = _img.colorSpace()
            description = (
                color_space.description() if color_space.isValid() else "unknown"
            )
            message = f'Read "{fpath}", {w}x{h}, Depth: {d} ({description})'
            logging.info(message)

        def qimage_from_file():
            if not self._gfxview:
                raise Exception
            return self._gfxview.qimage_from_file(fpath)

        t = LoadFileThread(
            qimage_from_file,
            parent=self,
        )

        t.result_ready.connect(callback)
        self._load_image_thread_replaceable_waiter.submit_thread(t)

    def _scan_cwd(self):
        """
        Build the `self._ordered_files` list of accepted file paths in `self._cwd`.
        Skips if file count hasn't changed.
        """
        if self._cwd is None:
            raise Exception

        # Check cached file count and if it's not changed, return early
        count = len(
            [
                name
                for name in os.listdir(self._cwd)
                if os.path.isfile(os.path.join(self._cwd, name))
            ]
        )
        if count == self._cwd_file_count:
            logging.debug(f"File count hasn't changed ({count}); skipping scan")
            return

        self._cwd_file_count = count

        accepted_exts = (
            ACCEPTED_FILE_EXTENSIONS["standard"]
            if self._include_standard_image_ext
            else []
        ) + (ACCEPTED_FILE_EXTENSIONS["raw"] if self._include_raw_image_ext else [])
        logging.debug(f"Accepted file extensions: {accepted_exts}")

        # Build paths for self._ordered_files
        paths = []
        with os.scandir(self._cwd) as scanner:
            for f in scanner:
                if f.is_file() and os.path.splitext(f)[1].lower() in accepted_exts:
                    paths.append(f.path)

        self._ordered_files = sorted(paths, key=str.lower)

    async def _read_image_async(self, fpath: str):
        if not self._gfxview:
            raise Exception

        return self._gfxview.qimage_from_file(fpath)

    def preload(self):
        """
        Pre-read images asynchronously to fill up LRU cache for _read_image.
        Up to `IMAGE_PRELOAD_MAX`.
        """

        t = PreloadFilesThread(
            self.get_preload_coros(),
            parent=self,
        )

        self._preload_images_thread_replaceable_waiter.submit_thread(t)
        return

    def get_preload_coros(self):
        """
        Pre-read images asynchronously to fill up LRU cache for _read_image.
        Up to `IMAGE_PRELOAD_MAX`.
        """
        if not self._current_file or not self._ordered_files:
            logging.debug("Nothing to preread")
            return []

        preload_coros = []
        window_size = 0
        window_start = window_end = self._current_file[0]
        while window_size < IMAGE_PRELOAD_MAX - 1:
            # Check after current file (prefer)
            if window_end + 1 < len(self._ordered_files):
                window_end += 1
                preload_coros.append(
                    self._read_image_async(self._ordered_files[window_end]),
                )
                window_size += 1

            # Check before current file
            if window_size < IMAGE_PRELOAD_MAX and window_start - 1 >= 0:
                window_start -= 1
                preload_coros.append(
                    self._read_image_async(self._ordered_files[window_start]),
                )
                window_size += 1

            # Break if we've reached both ends of self._ordered_files
            if window_start == 0 and window_end == len(self._ordered_files) - 1:
                break

        logging.debug(f"Preload window: {window_start}, {window_end}")

        return preload_coros

    def load_folder(self, folder: str):
        """
        Load the first photo by asc alphabetical filename in `folder`.
        """
        logging.info(f"Loading {folder}...")
        self._cwd = folder
        self._scan_cwd()

        if not self._ordered_files:
            logging.error("No photos in folder")
            raise Exception("No photos in folder.")

        self._current_file = 0, self._ordered_files[0]
        self.load_file(self._ordered_files[0], 0)
        self.preload()

    def _next_photo(self):
        """
        Move to whichever photo is evaluated by asc alphabetical filename as being next.
        """
        if self._current_file is None:
            raise Exception

        self._scan_cwd()

        next_idx = self._current_file[0] + 1
        if next_idx > len(self._ordered_files) - 1:
            logging.info("No more photos to show")
            return

        self._current_file = next_idx, self._ordered_files[next_idx]
        self.load_file(self._ordered_files[next_idx], next_idx)
        self.preload()

    def _prev_photo(self):
        """
        Move to whichever photo is evaluated by asc alphabetical filename as being previous.
        """
        if self._current_file is None:
            raise Exception

        self._scan_cwd()

        prev_idx = self._current_file[0] - 1
        if prev_idx < 0:
            logging.info("No more photos to show")
            return

        self._current_file = prev_idx, self._ordered_files[prev_idx]
        self.load_file(self._ordered_files[prev_idx], prev_idx)
        self.preload()

    def _discard_current_photo(self):
        """
        Skip to next photo and discard skipped photo into "pruned" folder.
        """
        if self._current_file is None:
            raise Exception

        def _discard(_path: str):
            """Move file to nested `pruned` folder"""
            if self._cwd is None:
                raise Exception

            _pruned_folder_path = self._get_pruned_folder_path()
            _dst = os.path.join(_pruned_folder_path, os.path.basename(_path))
            os.makedirs(_pruned_folder_path, exist_ok=True)
            os.rename(_path, _dst)
            logging.info(f"Moved {_path} to {_dst}")

        discarded_file = self._current_file

        # Remove from self._ordered_files
        self._ordered_files.pop(self._current_file[0])
        self._cwd_file_count -= 1

        if self._current_file[0] < len(self._ordered_files):
            # If there's something next
            next_idx = self._current_file[0]
        elif self._current_file[0] - 1 >= 0:
            # Otherwise if there's something before
            next_idx = self._current_file[0] - 1
        else:
            logging.info("No images left to prune")
            _discard(discarded_file[1])
            self._no_more_images()
            return

        self._current_file = next_idx, self._ordered_files[next_idx]
        self.load_file(self._ordered_files[next_idx], next_idx)

        _discard(discarded_file[1])
        self._scan_cwd()

    def _no_more_images(self):
        if self._overlay is not None:
            self._overlay.hide()

        if self._gfxview is not None:
            self._gfxview.set_image_hidden(True)

        if self._no_images_layout is not None:
            self._no_images_layout.show()

    def _get_pruned_folder_path(self):
        if self._cwd is None:
            raise Exception

        return os.path.join(self._cwd, "pruned")

    def _open_discarded(self):
        """Open 'pruned' folder in file viewer."""
        pruned_path = self._get_pruned_folder_path()
        os.makedirs(pruned_path, exist_ok=True)
        if platform.system() == "Windows":
            os.startfile(pruned_path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", pruned_path])
        else:
            subprocess.Popen(["xdg-open", pruned_path])

    def include_raw_images(self, include: bool):
        self._include_raw_image_ext = include
        logging.info(f"{'In' if include else 'Ex'}cluding raw images")

    def include_standard_images(self, include: bool):
        self._include_standard_image_ext = include
        logging.info(f"{'In' if include else 'Ex'}cluding standard images")
