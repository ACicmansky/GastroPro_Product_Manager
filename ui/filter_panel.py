"""
Filter panel component for product selection
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QPushButton, QCheckBox, QLineEdit, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal

class FilterPanel(QWidget):
    """
    Filter panel widget for selecting product categories 
    and managing SEO preservation settings
    """
    # Signals
    categorySelectionChanged = pyqtSignal()
    seoPreservationChanged = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glass")
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components"""
        filter_layout = QVBoxLayout(self)
        filter_layout.setContentsMargins(10, 10, 10, 10)
        
        # Category Filter
        filter_label = QLabel("Vyberte kategórie na export:")
        filter_label.setStyleSheet("font-weight: bold;")
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Hľadať kategórie...")
        self.search_bar.textChanged.connect(self.filter_categories)
        
        # Category buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setAlignment(Qt.AlignLeft)
        
        self.select_all_button = QPushButton("Prepnúť všetky")
        self.select_all_button.clicked.connect(self.select_all_categories)
        self.select_all_button.setToolTip("Prepnúť všetky kategórie")
        self.select_all_button.setMaximumWidth(130)
        
        self.toggle_filtered_button = QPushButton("Prepnúť filtrované")
        self.toggle_filtered_button.clicked.connect(self.toggle_filtered_categories)
        self.toggle_filtered_button.setToolTip("Označiť/odznačiť všetky filtrované kategórie")
        self.toggle_filtered_button.setMaximumWidth(130)
        
        buttons_layout.addWidget(self.select_all_button)
        buttons_layout.addWidget(self.toggle_filtered_button)
        buttons_layout.addStretch(1)
        
        # Category list
        self.category_list = QListWidget()
        self.category_list.setMaximumHeight(300)
        self.category_list.itemChanged.connect(self._on_item_changed)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.search_bar)
        filter_layout.addLayout(buttons_layout)
        filter_layout.addWidget(self.category_list)
        
        # SEO preservation controls
        seo_header = QLabel("SEO Nastavenia:")
        seo_header.setStyleSheet("font-weight: bold; margin-top: 10px;")
        filter_layout.addWidget(seo_header)
        
        self.seo_preservation_layout = QHBoxLayout()
        self.preserve_seo_checkbox = QCheckBox("Zachovať produkty s SEO dátami")
        self.preserve_seo_checkbox.stateChanged.connect(self._on_seo_preservation_changed)
        self.seo_count_label = QLabel("(0)")
        self.seo_preservation_layout.addWidget(self.preserve_seo_checkbox)
        self.seo_preservation_layout.addWidget(self.seo_count_label)
        self.seo_preservation_layout.addStretch(1)
        filter_layout.addLayout(self.seo_preservation_layout)
        
        # SEO preserved products list
        self.seo_details_button = QPushButton("Zobraziť zachované SEO produkty")
        self.seo_details_button.clicked.connect(self.toggle_seo_details)
        self.seo_details_button.setVisible(False)
        filter_layout.addWidget(self.seo_details_button)
        
        self.seo_details_list = QListWidget()
        self.seo_details_list.setVisible(False)
        self.seo_details_list.setMaximumHeight(150)
        filter_layout.addWidget(self.seo_details_list)
        
        filter_layout.addStretch(1)
    
    def filter_categories(self, text):
        """Filter the category list based on search text"""
        try:
            from rapidfuzz import fuzz
            
            # If search text is empty, show all items
            if not text:
                for i in range(self.category_list.count()):
                    item = self.category_list.item(i)
                    item.setHidden(False)
                return
                
            # Set the similarity threshold (0-100)
            # Lower values will match more items but with less precision
            threshold = 70
            
            for i in range(self.category_list.count()):
                item = self.category_list.item(i)
                item_text = item.text()
                
                # Calculate similarity scores using different methods
                # 1. Check if search is a substring (original method)
                substring_match = text.lower() in item_text.lower()
                
                # 2. Check for partial ratio (fuzzy substring matching)
                partial_score = fuzz.partial_ratio(text.lower(), item_text.lower())
                
                # 3. Check for token sort ratio (for word order independence)
                token_score = fuzz.token_sort_ratio(text.lower(), item_text.lower())
                
                # Hide item if it doesn't meet any of the match criteria
                item.setHidden(not (substring_match or partial_score >= threshold or token_score >= threshold))
        except ImportError:
            # Fallback if rapidfuzz is not available
            for i in range(self.category_list.count()):
                item = self.category_list.item(i)
                item.setHidden(text.lower() not in item.text().lower())
    
    def select_all_categories(self):
        """Toggle between selecting all and deselecting all categories"""
        all_checked = True
        
        # Check if all items are already checked
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() != Qt.Checked:
                all_checked = False
                break
        
        # Set all items to the opposite state
        new_state = Qt.Unchecked if all_checked else Qt.Checked
        
        # Temporarily disconnect the signal to avoid multiple updates
        self.category_list.itemChanged.disconnect(self._on_item_changed)
        
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setCheckState(new_state)
            
        # Reconnect the signal
        self.category_list.itemChanged.connect(self._on_item_changed)
        
        # Emit signal once for all changes
        self.categorySelectionChanged.emit()
    
    def toggle_filtered_categories(self):
        """Toggle the check state of filtered (visible) categories only"""
        # Determine the state to apply based on the first visible item
        new_state = Qt.Unchecked
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if not item.isHidden():
                # If first visible item is unchecked, we'll check all visible items
                # Otherwise, we'll uncheck all visible items
                if item.checkState() == Qt.Unchecked:
                    new_state = Qt.Checked
                break
                
        # Temporarily disconnect the signal to avoid multiple updates
        self.category_list.itemChanged.disconnect(self._on_item_changed)
        
        # Apply the determined state to all visible items
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if not item.isHidden():
                item.setCheckState(new_state)
        
        # Reconnect the signal
        self.category_list.itemChanged.connect(self._on_item_changed)
        
        # Emit signal once for all changes
        self.categorySelectionChanged.emit()
    
    def populate_categories(self, categories):
        """Populate the category list with the given categories"""
        # Disconnect signals temporarily
        if self.category_list.receivers(self.category_list.itemChanged) > 0:
            self.category_list.itemChanged.disconnect(self._on_item_changed)
            
        # Clear the list
        self.category_list.clear()
        
        # Add categories with checkboxes
        for category in sorted(categories):
            item = QListWidgetItem(category)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, category)
            self.category_list.addItem(item)
            
        # Reconnect signals
        self.category_list.itemChanged.connect(self._on_item_changed)
    
    def get_selected_categories(self):
        """Return a list of selected category names"""
        selected_categories = []
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_categories.append(item.text())
        return selected_categories
    
    def _on_item_changed(self, item):
        """Handle item change event"""
        self.categorySelectionChanged.emit()
    
    def _on_seo_preservation_changed(self, state):
        """Handle SEO preservation checkbox state change"""
        is_checked = state == Qt.Checked
        self.seoPreservationChanged.emit(is_checked)
        # Update visibility of SEO details button based on count and checkbox state
        self.seo_details_button.setVisible(
            is_checked and self._get_seo_count() > 0
        )
        
    def toggle_seo_details(self):
        """Toggle visibility of SEO preserved products list"""
        if not self.seo_details_list.isVisible():
            self.seo_details_list.setVisible(True)
            self.seo_details_button.setText("Skryť zachované SEO produkty")
        else:
            self.seo_details_list.setVisible(False)
            self.seo_details_button.setText("Zobraziť zachované SEO produkty")
    
    def _get_seo_count(self):
        """Helper to extract the count from the label text"""
        text = self.seo_count_label.text()
        try:
            return int(text.strip('()'))
        except ValueError:
            return 0
            
    def update_seo_count(self, count):
        """Update the SEO count label"""
        self.seo_count_label.setText(f"({count})")
        # Update visibility of SEO details button based on count and checkbox state
        self.seo_details_button.setVisible(
            count > 0 and self.preserve_seo_checkbox.isChecked()
        )
        
    def populate_seo_details(self, preserved_products):
        """Populate the list of preserved SEO products"""
        self.seo_details_list.clear()
        
        # Limit to first 100 products to avoid performance issues
        max_items = min(100, len(preserved_products))
        display_products = preserved_products.head(max_items)
        
        # Add products to the list with their categories
        for _, row in display_products.iterrows():
            try:
                product_name = row.get('Nazov', 'Unknown')
                category = row.get('Hlavna kategória', 'Unknown')
                
                # Create readable item text
                item_text = f"{product_name} (Kategória: {category})"
                
                # Add item to list
                self.seo_details_list.addItem(item_text)
            except Exception as e:
                print(f"Error adding item to SEO details list: {e}")
        
        # Add note if there are more products than shown
        if len(preserved_products) > max_items:
            remaining = len(preserved_products) - max_items
            self.seo_details_list.addItem(f"... a ďalších {remaining} produktov")
    
    def is_seo_preservation_enabled(self):
        """Return whether SEO preservation is enabled"""
        return self.preserve_seo_checkbox.isChecked()
