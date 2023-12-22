import logging
from typing import Callable
from PySide6 import QtWidgets, QtGui, QtCore


class Landing(QtWidgets.QWidget):
    layout: Callable[..., QtWidgets.QLayout] | QtWidgets.QLayout
    placeholder = None

    def __init__(self, parent=None):
        super(Landing, self).__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.placeholder = QtWidgets.QLabel(self)
        self.placeholder.setText("Placeholder for landing widget")
        self.layout.addWidget(self.placeholder)
