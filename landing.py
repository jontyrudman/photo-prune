import logging
from typing import Callable
from PySide6 import QtWidgets, QtGui, QtCore


class Landing(QtWidgets.QWidget):
    layout: Callable[..., QtWidgets.QLayout] | QtWidgets.QLayout
    placeholder = None

    def __init__(self, parent=None):
        super(Landing, self).__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)

        self._dir_select_layout = QtWidgets.QHBoxLayout()
        self._dir_line_edit = QtWidgets.QLineEdit()
        self._dir_select_button = QtWidgets.QPushButton("Select folder")
        self._dir_select_layout.addWidget(self._dir_line_edit)
        self._dir_select_layout.addWidget(self._dir_select_button)

        self._show_comp_button = QtWidgets.QCheckBox("Prune compressed images")
        self._show_comp_button.setChecked(True)
        self._show_raw_button = QtWidgets.QCheckBox("Prune raw images")

        self.confirm_button = QtWidgets.QPushButton("Prune")

        self.layout.addLayout(self._dir_select_layout)
        self.layout.addWidget(self._show_comp_button)
        self.layout.addWidget(self._show_raw_button)
        self.layout.addWidget(self.confirm_button)
