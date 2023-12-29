from PySide6 import QtWidgets, QtCore


class Landing(QtWidgets.QWidget):
    placeholder = None
    confirm_sig = QtCore.Signal(
        str, bool, bool, arguments=["folder", "include_std_img", "include_raw_img"]
    )

    def __init__(self, parent=None):
        super(Landing, self).__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)

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

        self._show_std_button = QtWidgets.QCheckBox("Prune standard images")
        self._show_std_button.setChecked(True)
        self._show_raw_button = QtWidgets.QCheckBox("Prune raw images")
        # self._show_raw_button.setDisabled(True)  # TODO: Enable when raw supported

        self._confirm_button = QtWidgets.QPushButton("Prune")
        self._confirm_button.clicked.connect(self._on_confirm)

        layout.addLayout(self._dir_select_layout)
        layout.addWidget(self._show_std_button)
        layout.addWidget(self._show_raw_button)
        layout.addWidget(
            self._confirm_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )

        self.setLayout(layout)

    def _on_confirm(self):
        self.confirm_sig.emit(
            self._dir_line_edit.text(),
            self._show_std_button.isChecked(),
            self._show_raw_button.isChecked(),
        )

    def _dir_select_dialog(self):
        dialog = QtWidgets.QFileDialog(self)
        folder = dialog.getExistingDirectory()
        if folder:
            self._dir_line_edit.setText(folder)
