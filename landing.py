import platform
from PySide6 import QtWidgets, QtCore


class Landing(QtWidgets.QWidget):
    placeholder = None
    confirm_sig = QtCore.Signal(
        str,
        bool,
        bool,
        bool,
        arguments=["folder", "include_std_img", "include_raw_img", "prune_similar"],
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

        self._show_std_checkbox = QtWidgets.QCheckBox("Prune standard images")
        self._show_std_checkbox.setChecked(True)
        self._show_raw_checkbox = QtWidgets.QCheckBox("Prune raw images")
        self._prune_similar_checkbox = QtWidgets.QCheckBox(
            "When an image is pruned, also prune all files with the same name"
        )

        self._confirm_button = QtWidgets.QPushButton("Prune")
        self._confirm_button.clicked.connect(self._on_confirm)

        layout.addLayout(self._dir_select_layout)
        layout.addWidget(self._show_std_checkbox)
        layout.addWidget(self._show_raw_checkbox)
        layout.addWidget(self._prune_similar_checkbox)
        layout.addWidget(
            self._confirm_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )

        self.setLayout(layout)

    def _on_confirm(self):
        self.confirm_sig.emit(
            self._dir_line_edit.text(),
            self._show_std_checkbox.isChecked(),
            self._show_raw_checkbox.isChecked(),
            self._prune_similar_checkbox.isChecked(),
        )

    def _dir_select_dialog(self):
        dialog = QtWidgets.QFileDialog(self)

        if platform.system() == "Windows":
            folder = dialog.getExistingDirectory(
                options=QtWidgets.QFileDialog.Option.DontUseNativeDialog
            )
        else:
            folder = dialog.getExistingDirectory()
        if folder:
            self._dir_line_edit.setText(folder)
