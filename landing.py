import logging
from typing import Callable
from PySide6 import QtWidgets, QtGui, QtCore


class Landing(QtWidgets.QWidget):
    layout: Callable[..., QtWidgets.QLayout] | QtWidgets.QLayout
    placeholder = None
    confirm_sig = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(Landing, self).__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)

        self._dir_select_layout = QtWidgets.QHBoxLayout()
        self._dir_line_edit = QtWidgets.QLineEdit(
            QtCore.QStandardPaths.standardLocations(
                QtCore.QStandardPaths.StandardLocation.HomeLocation
            )[0]
        )
        self._dir_line_edit.setFixedWidth(300)

        self._dir_select_button = QtWidgets.QPushButton("Select folder")
        self._dir_select_button.clicked.connect(self._dir_select_dialog)
        self._dir_select_layout.addWidget(self._dir_line_edit)
        self._dir_select_layout.addWidget(self._dir_select_button)

        self._show_comp_button = QtWidgets.QCheckBox("Prune compressed images")
        self._show_comp_button.setChecked(True)
        self._show_raw_button = QtWidgets.QCheckBox("Prune raw images")

        self._confirm_button = QtWidgets.QPushButton("Prune")
        self._confirm_button.clicked.connect(self._on_confirm)

        self.layout.addLayout(self._dir_select_layout)
        self.layout.addWidget(self._show_comp_button)
        self.layout.addWidget(self._show_raw_button)
        self.layout.addWidget(
            self._confirm_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )

    def _on_confirm(self):
        self.confirm_sig.emit(self._dir_line_edit.text())

    def _dir_select_dialog(self):
        dialog = QtWidgets.QFileDialog(self)
        folder = dialog.getExistingDirectory()
        self._dir_line_edit.setText(folder)
