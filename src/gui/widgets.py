# src/gui/widgets.py
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QDialog,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class DropArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.label = QLabel(
            "Presuňte CSV súbor sem alebo kliknite sem pre výber súboru"
        )
        self.label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(".csv"):
                self.parent().load_csv_file(file_path)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # The parent of DropArea is the central widget, its parent is the MainWindow
            self.parent().parent().select_csv_file()
        super().mousePressEvent(event)


class TopchladenieCsvDropArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.label = QLabel(
            "Presuňte Topchladenie.sk CSV súbor sem alebo kliknite sem pre výber súboru"
        )
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("QLabel { color: #666; font-size: 12px; }")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMaximumHeight(60)
        self.topchladenie_df = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(".csv"):
                self.parent().load_topchladenie_csv_file(file_path)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent().parent().parent().select_topchladenie_csv_file()
        super().mousePressEvent(event)

    def clear_file(self):
        self.topchladenie_df = None
        self.label.setText(
            "Presuňte Topchladenie.sk CSV súbor sem alebo kliknite sem pre výber súboru"
        )
        self.label.setStyleSheet("QLabel { color: #666; font-size: 12px; }")


class CategoryMappingDialog(QDialog):
    """Dialog for interactive category mapping when no mapping is found."""

    def __init__(
        self, original_category, suggestions=None, product_name=None, parent=None
    ):
        super().__init__(parent)
        self.original_category = original_category
        self.suggestions = suggestions or []
        self.product_name = product_name
        self.new_category = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Mapovanie kategórie")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        # Display product name if available
        if self.product_name:
            product_label_header = QLabel("Produkt:")
            product_label_header.setStyleSheet("font-weight: bold; margin-bottom: 3px;")
            layout.addWidget(product_label_header)

            product_label = QLabel(self.product_name)
            product_label.setStyleSheet(
                "padding: 8px; background-color: #e3f2fd; border-left: 4px solid #2196F3; margin-bottom: 15px;"
            )
            product_label.setWordWrap(True)
            layout.addWidget(product_label)

        # Label showing original category
        info_label = QLabel("Nebolo nájdené mapovanie pre kategóriu:")
        info_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(info_label)

        original_label = QLabel(self.original_category)
        original_label.setStyleSheet(
            "padding: 10px; background-color: #f0f0f0; border-radius: 5px; margin-bottom: 15px;"
        )
        original_label.setWordWrap(True)
        layout.addWidget(original_label)

        # Suggestions list (if available)
        if self.suggestions:
            suggestions_label = QLabel(
                "Návrhy podobných kategórií (kliknite pre výber):"
            )
            suggestions_label.setStyleSheet(
                "font-weight: bold; margin-top: 10px; margin-bottom: 5px;"
            )
            layout.addWidget(suggestions_label)

            self.suggestions_list = QListWidget()
            self.suggestions_list.setMaximumHeight(200)
            self.suggestions_list.setStyleSheet(
                """
                QListWidget {
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    background-color: #fafafa;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #eee;
                }
                QListWidget::item:hover {
                    background-color: #e3f2fd;
                    cursor: pointer;
                }
                QListWidget::item:selected {
                    background-color: #2196F3;
                    color: white;
                }
            """
            )

            for category, score in self.suggestions:
                item = QListWidgetItem(f"{category}  ({score:.0f}%)")
                item.setData(Qt.UserRole, category)  # Store the category name

                # Bold font for high confidence matches
                if score >= 80:
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)

                self.suggestions_list.addItem(item)

            # Connect click to populate input
            self.suggestions_list.itemClicked.connect(self.on_suggestion_clicked)
            layout.addWidget(self.suggestions_list)

        # Input for new category name
        input_label = QLabel("Alebo zadajte vlastnú kategóriu:")
        input_label.setStyleSheet("margin-top: 10px;")
        layout.addWidget(input_label)

        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("Napr.: Nerezový nábytok/Pracovné stoly")
        self.category_input.returnPressed.connect(self.accept)
        layout.addWidget(self.category_input)

        # OK button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_button = QPushButton("OK")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        ok_button.setMinimumWidth(100)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Set focus to input
        self.category_input.setFocus()

    def on_suggestion_clicked(self, item):
        """Populate input field when a suggestion is clicked."""
        category = item.data(Qt.UserRole)
        if category:
            self.category_input.setText(category)
            self.category_input.setFocus()

    def accept(self):
        self.new_category = self.category_input.text().strip()
        if self.new_category:
            super().accept()

    def get_new_category(self):
        return self.new_category
