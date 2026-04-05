# src/gui/widgets.py
import re
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
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QGroupBox,
    QSizePolicy,
    QDialogButtonBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from rapidfuzz import fuzz


from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtGui import QFont, QPixmap


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
        self.setMinimumWidth(700)

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


class PriceMappingDialog(QDialog):
    """Dialog for interactive price mapping when no price is found."""

    def __init__(self, product_data, prices_df, parent=None):
        super().__init__(parent)
        self.product_data = product_data
        self.product_code = product_data.get("code", "")
        self.prices_df = prices_df
        self.selected_price = None
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.on_image_downloaded)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Priradenie ceny produktu")
        self.setModal(True)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(800)

        layout = QVBoxLayout()

        # Header with remaining count
        remaining = self.product_data.get("remaining_count", "?")
        header_label = QLabel(f"Ostáva priradiť: {remaining} produktov")
        header_label.setStyleSheet(
            "font-weight: bold; color: #666; margin-bottom: 10px;"
        )
        header_label.setAlignment(Qt.AlignRight)
        layout.addWidget(header_label)

        # Product Info Area (Horizontal Layout for Image + Details)
        info_layout = QHBoxLayout()

        # Image Label
        self.image_label = QLabel()
        self.image_label.setFixedSize(150, 150)
        self.image_label.setStyleSheet(
            "border: 1px solid #ccc; background-color: #f0f0f0;"
        )
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText("Načítavam obrázok...")
        info_layout.addWidget(self.image_label)

        # Details Layout
        details_layout = QVBoxLayout()

        info_label = QLabel("Nebola nájdená cena pre produkt:")
        info_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        details_layout.addWidget(info_label)

        code_label = QLabel(self.product_code)
        code_label.setStyleSheet(
            "padding: 15px; background-color: #e3f2fd; border-left: 5px solid #2196F3; font-size: 14pt; font-weight: bold; margin-bottom: 5px;"
        )
        code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_layout.addWidget(code_label)

        # Dimensions Display
        dims = []
        if self.product_data.get("width"):
            dims.append(f"Š: {self.product_data['width']}")
        if self.product_data.get("depth"):
            dims.append(f"H: {self.product_data['depth']}")
        if self.product_data.get("height"):
            dims.append(f"V: {self.product_data['height']}")

        if dims:
            dims_label = QLabel(" | ".join(dims))
            dims_label.setStyleSheet(
                "color: #666; font-size: 10pt; margin-bottom: 15px;"
            )
            details_layout.addWidget(dims_label)

        details_layout.addStretch()
        info_layout.addLayout(details_layout)
        layout.addLayout(info_layout)

        # Trigger image download
        image_url = self.product_data.get("image_url")
        if image_url:
            from PyQt5.QtCore import QUrl

            request = QNetworkRequest(QUrl(image_url))
            self.network_manager.get(request)
        else:
            self.image_label.setText("Bez obrázku")

        # Suggestions
        suggestions = self.get_price_suggestions()
        if suggestions:
            suggestions_group = QGroupBox("Podobné produkty")
            suggestions_layout = QVBoxLayout(suggestions_group)

            self.suggestions_list = QListWidget()
            self.suggestions_list.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding
            )
            self.suggestions_list.setMinimumHeight(100)
            self.suggestions_list.itemClicked.connect(self.on_suggestion_selected)

            for code, price, score, dim_str in suggestions:
                dim_info = f" [{dim_str}]" if dim_str and dim_str != "nan" else ""
                item_text = f"{code} - {price} ({score:.0f}%){dim_info}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, price)
                self.suggestions_list.addItem(item)

            suggestions_layout.addWidget(self.suggestions_list)
            layout.addWidget(suggestions_group)

        # Search
        search_group = QFrame()
        search_layout = QVBoxLayout(search_group)
        search_layout.setContentsMargins(0, 0, 0, 0)

        search_label = QLabel("Vyhľadať v cenníku:")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Hľadať kód alebo cenu...")
        self.search_input.textChanged.connect(self.filter_prices)
        search_layout.addWidget(self.search_input)

        layout.addWidget(search_group)

        # Prices Table
        self.prices_table = QTableWidget()
        self.prices_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.prices_table.setMinimumHeight(200)  # Increased height to show ~5 rows
        self.prices_table.setColumnCount(3)
        self.prices_table.setHorizontalHeaderLabels(["Kód produktu", "Cena", "Rozmer"])
        self.prices_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.prices_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.prices_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self.prices_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.prices_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.prices_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.prices_table.itemClicked.connect(self.on_price_selected)

        layout.addWidget(self.prices_table)

        # Populate table
        self.populate_table(self.prices_df)

        # Manual Input
        input_group = QFrame()
        input_group.setStyleSheet("border-top: 1px solid #ccc;")
        input_layout = QVBoxLayout(input_group)
        input_layout.setContentsMargins(
            0, 15, 0, 0
        )  # Top margin for spacing from border

        input_label = QLabel("Alebo zadajte cenu manuálne:")
        input_label.setStyleSheet("font-weight: bold;")
        input_layout.addWidget(input_label)

        self.manual_price_input = QLineEdit()
        self.manual_price_input.setPlaceholderText("Napr.: 123.45")
        self.manual_price_input.setMinimumHeight(30)  # Ensure good click target
        input_layout.addWidget(self.manual_price_input)

        input_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        layout.addSpacing(10)
        layout.addWidget(input_group)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_price)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

        # Initial filter if product code has parts
        initial_search = self.product_code.split()[0] if self.product_code else ""
        if len(initial_search) > 2:
            self.search_input.setText(initial_search)

    def on_image_downloaded(self, reply):
        if reply.error():
            self.image_label.setText("Chyba načítania")
        else:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                self.image_label.setPixmap(
                    pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                self.image_label.setText("Chybný obrázok")
        reply.deleteLater()

    def populate_table(self, df):
        self.prices_table.setRowCount(0)
        if df is None or df.empty:
            return

        self.prices_table.setRowCount(len(df))
        for i, (index, row) in enumerate(df.iterrows()):
            code_item = QTableWidgetItem(str(row.get("code", "")))
            price_item = QTableWidgetItem(str(row.get("price", "")))
            dim_item = QTableWidgetItem(str(row.get("dimension", "")))

            self.prices_table.setItem(i, 0, code_item)
            self.prices_table.setItem(i, 1, price_item)
            self.prices_table.setItem(i, 2, dim_item)

    def filter_prices(self, text):
        if self.prices_df is None:
            return

        text = text.lower()
        filtered_df = self.prices_df[
            self.prices_df["code"]
            .astype(str)
            .str.lower()
            .str.contains(text, regex=False)
            | self.prices_df["price"]
            .astype(str)
            .str.lower()
            .str.contains(text, regex=False)
            | self.prices_df["dimension"]
            .astype(str)
            .str.lower()
            .str.contains(text, regex=False)
        ]
        self.populate_table(filtered_df)

    def on_price_selected(self, item):
        row = item.row()
        price = self.prices_table.item(row, 1).text()
        self.manual_price_input.setText(str(price))

    def on_suggestion_selected(self, item):
        price = item.data(Qt.UserRole)
        self.manual_price_input.setText(str(price))

    def _extract_numbers(self, text):
        """Extract all number sequences from text."""
        if not text:
            return set()
        return set(re.findall(r"\d+", str(text)))

    def _extract_finish(self, text):
        """Extract finish type (POL/SAT) from text."""
        if not text:
            return None
        text = str(text).upper()
        if "(POL)" in text or " POL " in text or text.endswith(" POL"):
            return "POL"
        if "(SAT)" in text or " SAT " in text or text.endswith(" SAT"):
            return "SAT"
        return None

    def get_price_suggestions(self, top_n=5):
        if self.prices_df is None or self.prices_df.empty or not self.product_code:
            return []

        suggestions = []
        target_code = str(self.product_code).lower()
        target_nums = self._extract_numbers(target_code)
        target_finish = self._extract_finish(self.product_code)

        # Parse target dimensions
        target_w = self._parse_dim(self.product_data.get("width"))
        target_d = self._parse_dim(self.product_data.get("depth"))
        target_h = self._parse_dim(self.product_data.get("height"))
        has_target_dims = (
            target_w is not None and target_d is not None and target_h is not None
        )

        for _, row in self.prices_df.iterrows():
            code = str(row.get("code", ""))
            price = row.get("price", "")
            dim_str = str(row.get("dimension", ""))

            if not code:
                continue

            # 1. Code Similarity
            score_ratio = fuzz.ratio(target_code, code.lower())
            score_token = fuzz.token_sort_ratio(target_code, code.lower())
            code_score = (score_ratio * 0.6) + (score_token * 0.4)

            # 2. Number Similarity
            num_score = 0
            row_nums = self._extract_numbers(code)
            if target_nums and row_nums:
                matches = len(target_nums.intersection(row_nums))
                if matches > 0:
                    # Calculate percentage of target numbers matched
                    num_score = (matches / len(target_nums)) * 100

            # 3. Finish Similarity
            finish_score = 0
            row_finish = self._extract_finish(code)
            if target_finish:
                if row_finish == target_finish:
                    finish_score = 100
                elif row_finish is not None:  # Different finish found
                    finish_score = 0
                else:  # No finish found in row
                    finish_score = 50

            # 4. Dimension Similarity
            dim_score = 0
            if has_target_dims and dim_str:
                # Parse row dimensions (format: WxDxH)
                try:
                    parts = dim_str.lower().replace("ø", "").split("x")
                    if len(parts) >= 3:
                        row_w = self._parse_dim(parts[0])
                        row_d = self._parse_dim(parts[1])
                        row_h = self._parse_dim(parts[2])

                        if (
                            row_w is not None
                            and row_d is not None
                            and row_h is not None
                        ):
                            # Calculate differences
                            diff_w = abs(target_w - row_w)
                            diff_d = abs(target_d - row_d)
                            diff_h = abs(target_h - row_h)

                            # Allow small tolerance (e.g. 10mm)
                            if diff_w <= 10 and diff_d <= 10 and diff_h <= 10:
                                dim_score = 100
                            elif diff_w <= 20 and diff_d <= 20 and diff_h <= 20:
                                dim_score = 80
                            elif diff_w <= 50 and diff_d <= 50 and diff_h <= 50:
                                dim_score = 50
                except:
                    pass

            # Combined Score
            if target_finish:
                # Weights: Code (10%), Numbers (40%), Finish (30%), Dimensions (20%)
                final_score = (
                    (code_score * 0.1)
                    + (num_score * 0.4)
                    + (finish_score * 0.3)
                    + (dim_score * 0.2)
                )
            elif not target_nums:
                # Weights: Code (60%), Dimensions (40%)
                final_score = (code_score * 0.6) + (dim_score * 0.4)
            else:
                # Weights: Code (30%), Numbers (40%), Dimensions (30%)
                final_score = (code_score * 0.3) + (num_score * 0.4) + (dim_score * 0.3)

            if final_score > 40:
                suggestions.append((code, price, final_score, dim_str))

        # Sort by score descending
        suggestions.sort(key=lambda x: x[2], reverse=True)

        # Format output
        return [(s[0], s[1], s[2], s[3]) for s in suggestions[:top_n]]

    def _parse_dim(self, value):
        """Parse dimension string to float."""
        if not value:
            return None
        try:
            # Remove non-numeric chars except dot/comma
            clean = "".join(c for c in str(value) if c.isdigit() or c in ".,")
            return float(clean.replace(",", "."))
        except:
            return None

    def accept_price(self):
        price = self.manual_price_input.text().strip()
        if price:
            self.selected_price = price
            self.accept()

    def get_selected_price(self):
        return self.selected_price
