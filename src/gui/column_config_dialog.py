from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QDialogButtonBox,
    QGroupBox,
)
from PyQt5.QtCore import Qt


class ColumnConfigDialog(QDialog):
    """Dialog for configuring output columns based on input file."""

    def __init__(self, columns_to_add, columns_to_remove, parent=None):
        super().__init__(parent)
        self.columns_to_add = columns_to_add
        self.columns_to_remove = columns_to_remove
        self.selected_to_add = []
        self.selected_to_remove = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Konfigurácia stĺpcov")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()

        # Info label
        info_label = QLabel(
            "Boli zistené rozdiely medzi stĺpcami vo vstupnom súbore a konfiguráciou.\n"
            "Vyberte, ktoré zmeny chcete aplikovať do config.json."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Columns to Add Group
        if self.columns_to_add:
            add_group = QGroupBox("Nové stĺpce na pridanie (zistené v súbore)")
            add_layout = QVBoxLayout(add_group)

            self.add_list = QListWidget()
            for col in self.columns_to_add:
                item = QListWidgetItem(col)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)  # Default to checked
                self.add_list.addItem(item)

            add_layout.addWidget(self.add_list)
            layout.addWidget(add_group)

        # Columns to Remove Group
        if self.columns_to_remove:
            remove_group = QGroupBox(
                "Chýbajúce stĺpce na odstránenie (nie sú v súbore)"
            )
            remove_layout = QVBoxLayout(remove_group)

            self.remove_list = QListWidget()
            for col in self.columns_to_remove:
                item = QListWidgetItem(col)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)  # Default to unchecked (safety)
                self.remove_list.addItem(item)

            remove_layout.addWidget(self.remove_list)
            layout.addWidget(remove_group)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def accept(self):
        # Collect selected items
        if hasattr(self, "add_list"):
            for i in range(self.add_list.count()):
                item = self.add_list.item(i)
                if item.checkState() == Qt.Checked:
                    self.selected_to_add.append(item.text())

        if hasattr(self, "remove_list"):
            for i in range(self.remove_list.count()):
                item = self.remove_list.item(i)
                if item.checkState() == Qt.Checked:
                    self.selected_to_remove.append(item.text())

        super().accept()

    def get_changes(self):
        """Return tuple of (columns_to_add, columns_to_remove)."""
        return self.selected_to_add, self.selected_to_remove
