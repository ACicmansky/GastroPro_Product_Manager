# app.py
import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QListWidget,
    QCheckBox, QListWidgetItem, QDesktopWidget, QFrame, QLineEdit, QProgressBar,
    QTableView, QSplitter, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QAbstractTableModel, QModelIndex, QVariant, QStandardPaths, QSortFilterProxyModel

from utils import load_config, fetch_xml_feed, parse_xml_feed, merge_dataframes, load_csv_data


class PandasTableModel(QAbstractTableModel):
    """Model for displaying pandas DataFrame in QTableView with checkboxes and sorting"""
    
    def __init__(self, dataframe=None, editable=False):
        super().__init__()
        self._editable = editable
        self._checkable = True  # Enable checkboxes by default
        self._checked_rows = set()  # Track checked rows
        self._sort_column = -1  # No sorting initially
        self._sort_order = Qt.AscendingOrder
        self._original_df = pd.DataFrame()  # Store original unsorted data
        self._sort_mapping = []  # Maps sorted rows to original rows
        self.setDataFrame(dataframe)
        
    def setDataFrame(self, dataframe):
        """Set the DataFrame to be displayed"""
        self.beginResetModel()
        # Store both original and display data
        self._original_df = dataframe.copy() if dataframe is not None else pd.DataFrame()
        self._data = self._original_df.copy()
        self._display_cache = {}
        self.modified_cells = set()
        # Reset checked rows when data changes
        self._checked_rows = set()
        # Reset sort parameters
        self._sort_column = -1
        self._sort_order = Qt.AscendingOrder
        # Initialize sort mapping (1:1 mapping initially)
        self._sort_mapping = list(range(len(self._data)))
        self.endResetModel()
        
    def sort(self, column, order):
        """Sort the table by the specified column and order"""
        if len(self._data) <= 1:
            return  # Nothing to sort
            
        # Begin layout change
        self.beginResetModel()
        
        # Store sort parameters
        self._sort_column = column
        self._sort_order = order
        
        try:
            # Handle the checkbox column specially
            if self._checkable and column == 0:
                # Create a temporary series for sorting by checkbox state
                checkbox_series = pd.Series([1 if i in self._checked_rows else 0 for i in range(len(self._data))], 
                                           index=range(len(self._data)))
                # Sort by checkbox state
                ascending = (order == Qt.AscendingOrder)
                sorted_indices = checkbox_series.sort_values(ascending=ascending).index
            else:
                # Adjust column index for data access if we have checkboxes
                data_column = column - 1 if self._checkable else column
                
                if data_column >= 0 and data_column < len(self._original_df.columns):
                    # Get column name
                    column_name = self._original_df.columns[data_column]
                    # Sort by the specified column
                    ascending = (order == Qt.AscendingOrder)
                    sorted_indices = self._original_df.sort_values(column_name, ascending=ascending).index
                else:
                    # Invalid column, don't sort
                    self.endResetModel()
                    return
            
            # Update the sort mapping
            self._sort_mapping = list(sorted_indices)
            # Apply the sort to the data - this actually changes the DataFrame order
            self._data = self._original_df.iloc[self._sort_mapping].reset_index(drop=True)
        
        except Exception as e:
            print(f"Error during sorting: {e}")
            # In case of error, don't change anything
            self.endResetModel()
            return
            
        # Finish the layout change
        self.endResetModel()
        
    def isRowChecked(self, row):
        """Return whether the row is checked"""
        return row in self._checked_rows
    
    def setRowChecked(self, row, checked):
        """Set the checked state of the row"""
        if checked:
            self._checked_rows.add(row)
        else:
            self._checked_rows.discard(row)
            
    def getCheckedRows(self):
        """Return the set of checked rows"""
        return self._checked_rows
        
    def getCheckedRowsData(self):
        """Return DataFrame with data from checked rows"""
        if not self._checked_rows or self._data.empty:
            return pd.DataFrame(columns=self._data.columns)
        
        # If sorting is applied, we need to map checked rows to the original DataFrame
        if self._sort_column >= 0:
            # Create a list of original DataFrame indices that correspond to checked rows
            checked_original_indices = [self._sort_mapping[row] for row in self._checked_rows 
                                       if row < len(self._sort_mapping)]
            # Return data from original DataFrame
            return self._original_df.iloc[checked_original_indices].copy()
        else:
            # No sorting applied, just return checked rows from current data
            return self._data.iloc[list(self._checked_rows)].copy()
        
    def rowCount(self, parent=QModelIndex()):
        """Return the number of rows"""
        return len(self._data) if parent == QModelIndex() else 0
        
    def columnCount(self, parent=QModelIndex()):
        """Return the number of columns, including checkbox column"""
        if parent == QModelIndex():
            # Add one extra column for checkboxes
            return len(self._data.columns) + 1 if self._checkable else len(self._data.columns)
        return 0
        
    def data(self, index, role=Qt.DisplayRole):
        """Return data for the given role at the specified index"""
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return QVariant()
        
        row, col = index.row(), index.column()
        
        # Handle checkbox column (first column)
        if self._checkable and col == 0:
            if role == Qt.CheckStateRole:
                return Qt.Checked if row in self._checked_rows else Qt.Unchecked
            # Return empty string for display role to make room for checkbox
            elif role == Qt.DisplayRole:
                return ""
            # Make text center-aligned
            elif role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            return QVariant()
        
        # Adjust column index for data access (subtract 1 for checkbox column)
        data_col = col - 1 if self._checkable else col
        if data_col >= len(self._data.columns):
            return QVariant()
            
        column_name = self._data.columns[data_col]
        value = self._data.iloc[row, data_col]
        
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if pd.isna(value):
                return ""
            
            # Use cached display value if available
            cache_key = (row, data_col)
            if role == Qt.DisplayRole and cache_key in self._display_cache:
                return self._display_cache[cache_key]
                
            # Format value based on its type
            if isinstance(value, float):
                display_val = f"{value:.2f}"
            else:
                display_val = str(value)
                
            # Cache the display value
            if role == Qt.DisplayRole:
                self._display_cache[cache_key] = display_val
                
            return display_val
            
        elif role == Qt.BackgroundRole:
            # Highlight modified cells
            if (row, data_col) in self.modified_cells:
                return QVariant(Qt.yellow)
                
            # Highlight cells with SEO data
            if column_name in ['SEO titulka', 'SEO popis', 'SEO kľúčové slová'] and value and not pd.isna(value):
                return QVariant(Qt.lightGray)
        
        return QVariant()
        
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return header data for the given section, orientation and role"""
        if role != Qt.DisplayRole:
            return QVariant()
            
        if orientation == Qt.Horizontal:
            # Checkbox column header
            if self._checkable and section == 0:
                return "Vybrať"
                
            # Adjust section for data columns
            data_section = section - 1 if self._checkable else section
            if data_section < len(self._data.columns):
                return str(self._data.columns[data_section])
        elif orientation == Qt.Vertical:
            if section < len(self._data.index):
                return str(self._data.index[section])
                
        return QVariant()
        
    def flags(self, index):
        """Return item flags for the given index"""
        if not index.isValid():
            return Qt.ItemIsEnabled
            
        flags = super().flags(index) | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        
        # Make checkbox column checkable and interactive
        if self._checkable and index.column() == 0:
            # These flags ensure the checkbox is fully interactive
            flags |= Qt.ItemIsUserCheckable | Qt.ItemIsEditable
        # Make data columns editable if model is editable
        elif self._editable:
            flags |= Qt.ItemIsEditable
            
        return flags
        
    def setData(self, index, value, role=Qt.EditRole):
        """Set data for the specified index and role"""
        if not index.isValid():
            return False
            
        row, col = index.row(), index.column()
        
        # Handle checkbox column
        if self._checkable and col == 0 and (role == Qt.CheckStateRole or role == Qt.EditRole):
            # For checkbox column, allow toggling with either CheckStateRole or EditRole
            # This allows both standard checkbox clicks and programmatic changes
            if isinstance(value, bool):
                # Direct boolean value
                self._checked_rows.add(row) if value else self._checked_rows.discard(row)
            elif value == Qt.Checked:
                self._checked_rows.add(row)
            else:
                self._checked_rows.discard(row)
            
            # Emit data changed signal
            self.dataChanged.emit(index, index)
            return True
            
        # Handle editable data columns
        if role == Qt.EditRole and self._editable:
            # Adjust column index for data columns
            data_col = col - 1 if self._checkable else col
            if data_col >= len(self._data.columns):
                return False
                
            try:
                # Get the current value for type conversion
                current_value = self._data.iloc[row, data_col]
                
                # Convert the new value to the same type as the current value
                if isinstance(current_value, bool):
                    new_value = bool(value)
                elif isinstance(current_value, int):
                    new_value = int(value)
                elif isinstance(current_value, float):
                    new_value = float(value)
                else:
                    new_value = str(value)
                
                # Update the data
                self._data.iloc[row, data_col] = new_value
                
                # Track this cell as modified
                self.modified_cells.add((row, data_col))
                
                # Clear display cache for this cell
                cache_key = (row, data_col)
                if cache_key in self._display_cache:
                    del self._display_cache[cache_key]
                
                # Emit data changed signal
                self.dataChanged.emit(index, index)
                return True
            except Exception as e:
                print(f"Error setting data: {e}")
                return False
                
        return False
            
    def getDataFrame(self):
        """Return the current DataFrame"""
        return self._data.copy()


class DropArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.label = QLabel("Presuňte CSV súbor sem alebo kliknite na tlačidlo nižšie")
        self.label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith('.csv'):
                self.parent().load_csv_file(file_path)

class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    progress = pyqtSignal(str)
    result = pyqtSignal(object)

    def __init__(self, filtered_df, selected_categories, config, preserve_seo=False):
        super().__init__()
        self.filtered_df = filtered_df  # Already filtered data from the UI
        self.selected_categories = selected_categories
        self.config = config
        self.preserve_seo = preserve_seo

    def run(self):
        try:
            # Using already filtered data from the output table model
            self.progress.emit("Spracovanie filtrovaných dát...")
            
            if self.filtered_df.empty:
                self.error.emit(("Prázdny výsledok", "Žiadne produkty nespĺňajú vybrané kritériá."))
                self.finished.emit()
                return

            # Process XML feeds
            feed_count = len(self.config['xml_feeds'])
            self.progress.emit(f"Načítavanie {feed_count} XML feedov...")
            
            feed_dataframes = []
            for feed_name, feed_info in self.config['xml_feeds'].items():
                self.progress.emit(f"Načítavanie: {feed_name}")
                try:
                    root = fetch_xml_feed(feed_info['url'])
                    if root is None:
                        self.progress.emit(f"Feed {feed_name} nedostupný, pokračujem ďalej...")
                        continue
                    
                    self.progress.emit(f"Parsovanie: {feed_name}")
                    df = parse_xml_feed(root, feed_info['root_element'], feed_info['mapping'], feed_name)
                    
                    if df is not None and not df.empty:
                        feed_dataframes.append(df)
                        self.progress.emit(f"Feed {feed_name} spracovaný: {len(df)} produktov")
                    else:
                        self.progress.emit(f"Feed {feed_name} neobsahuje žiadne dáta")
                        
                except Exception as e:
                    self.error.emit(("Chyba pri spracovaní feedu", f"Chyba pri spracovaní feedu {feed_name}: {e}"))

            self.progress.emit("Spájanie dát...")
            final_df = merge_dataframes(self.filtered_df, feed_dataframes, self.config['final_csv_columns'])
            self.progress.emit(f"Výsledný počet produktov: {len(final_df)}")
            self.result.emit(final_df)
        except Exception as e:
            self.error.emit(("Chyba generovania", f"Pri generovaní došlo k chybe:\n{e}"))
        finally:
            self.finished.emit()

class ProductManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GASTROPRO Product Manager")
        self.setGeometry(100, 100, 600, 400)
        self.main_df = None
        self.categories = []
        self.config = load_config()
        self.dark_mode = False

        if not self.config:
            QMessageBox.critical(self, "Chyba konfigurácie", "Nepodarilo sa načítať konfiguračný súbor. Aplikácia sa ukončí.")
            sys.exit(1)
        
        self.init_ui()
        self.center_window()
        self.load_stylesheet()

    def load_stylesheet(self):
        try:
            with open('styles/main.qss', 'r') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("Stylesheet not found.")

    def center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def init_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setObjectName("central_widget")
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # --- Top controls ---
        top_controls = QHBoxLayout()
        
        # Dark Mode Toggle
        self.dark_mode_button = QPushButton("Dark Mode")
        self.dark_mode_button.clicked.connect(self.toggle_dark_mode)
        self.dark_mode_button.setMaximumWidth(100)
        top_controls.addWidget(self.dark_mode_button)
        
        # CSV Upload
        upload_button = QPushButton("Nahrať CSV")
        upload_button.clicked.connect(self.select_csv_file)
        upload_button.setMinimumWidth(120)
        top_controls.addWidget(upload_button)
        
        # Export Button
        self.generate_button = QPushButton("Generovať a Exportovať CSV")
        self.generate_button.clicked.connect(self.generate_and_export_csv)
        self.generate_button.setVisible(False)
        self.generate_button.setMinimumWidth(180)
        top_controls.addWidget(self.generate_button)
        
        top_controls.addStretch(1)
        self.layout.addLayout(top_controls)
        
        # --- Drop Area ---
        self.drop_area = DropArea(self)
        self.layout.addWidget(self.drop_area)
        
        # --- Main Content - Split into filter panel and tables ---
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # --- Left Side: Filter Panel ---
        self.filter_group = QWidget()
        self.filter_group.setObjectName("glass")
        filter_layout = QVBoxLayout(self.filter_group)
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
        self.preserve_seo_checkbox.stateChanged.connect(self.filter_input_table)
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
        
        # --- Right Side: Tables Container ---
        tables_container = QWidget()
        tables_layout = QVBoxLayout(tables_container)
        tables_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tables splitter (vertical)
        tables_splitter = QSplitter(Qt.Vertical)
        
        # Input table (top)
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(5, 5, 5, 5)
        
        input_header = QLabel("Vstupné dáta (upraviteľné)")
        input_header.setStyleSheet("font-weight: bold; font-size: 14px;")
        input_layout.addWidget(input_header)
        
        self.input_table = QTableView()
        self.input_table.setAlternatingRowColors(True)
        self.input_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.input_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.input_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.input_table.horizontalHeader().setStretchLastSection(True)
        
        # Set edit triggers to make checkboxes clickable
        self.input_table.setEditTriggers(QAbstractItemView.DoubleClicked | 
                                      QAbstractItemView.SelectedClicked | 
                                      QAbstractItemView.EditKeyPressed)
                                      
        # Create model
        self.input_model = PandasTableModel(editable=True)
        
        # Create proxy model for sorting
        self.input_proxy_model = QSortFilterProxyModel()
        self.input_proxy_model.setSourceModel(self.input_model)
        self.input_proxy_model.setSortRole(Qt.DisplayRole)  # Use display role for sorting
        
        # Set the proxy model on the view
        self.input_table.setModel(self.input_proxy_model)
        
        # Set column width for checkbox column
        self.input_table.setColumnWidth(0, 40)  # Make checkbox column narrow
        
        # Enable sorting
        self.input_table.setSortingEnabled(True)
        self.input_table.horizontalHeader().setSortIndicatorShown(True)
        
        # Connect cell clicks to toggle checkboxes
        self.input_table.clicked.connect(self.handle_input_table_click)
        
        input_layout.addWidget(self.input_table)
        
        # Create button layout for selection controls
        self.input_buttons_layout = QHBoxLayout()
        
        # Create the 'Select All' button
        self.select_all_rows_button = QPushButton("Označiť všetky")
        self.select_all_rows_button.clicked.connect(self.check_all_visible_rows)
        self.select_all_rows_button.setVisible(False)  # Hidden initially until data is loaded
        self.input_buttons_layout.addWidget(self.select_all_rows_button)
        
        # Create the 'Clear All' button
        self.clear_all_rows_button = QPushButton("Odznačiť všetky")
        self.clear_all_rows_button.clicked.connect(self.uncheck_all_rows)
        self.clear_all_rows_button.setVisible(False)  # Hidden initially until data is loaded
        self.input_buttons_layout.addWidget(self.clear_all_rows_button)
        
        # Add spacer to push 'Add to output' button to the right
        self.input_buttons_layout.addStretch(1)
        
        # Create the 'Add to output' button
        self.add_to_output_button = QPushButton("Pridať vybrané riadky do výstupu")
        self.add_to_output_button.clicked.connect(self.add_selected_rows_to_output)
        self.add_to_output_button.setVisible(False)  # Hidden initially until data is loaded
        self.input_buttons_layout.addWidget(self.add_to_output_button)
        
        # Add the button layout to the main input layout
        input_layout.addLayout(self.input_buttons_layout)
        
        tables_splitter.addWidget(input_container)
        
        # Output table (bottom)
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(5, 5, 5, 5)
        
        output_header = QLabel("Výstupná tabuľka")
        output_header.setStyleSheet("font-weight: bold; font-size: 14px;")
        output_layout.addWidget(output_header)
        
        self.output_table = QTableView()
        self.output_table.setAlternatingRowColors(True)
        self.output_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.output_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.output_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.output_table.horizontalHeader().setStretchLastSection(True)
        self.output_model = PandasTableModel(editable=False)  # Output table is not editable
        
        # Create proxy model for sorting
        self.output_proxy_model = QSortFilterProxyModel()
        self.output_proxy_model.setSourceModel(self.output_model)
        self.output_proxy_model.setSortRole(Qt.DisplayRole)  # Use display role for sorting
        
        # Set proxy model on the view
        self.output_table.setModel(self.output_proxy_model)
        
        # Enable sorting
        self.output_table.setSortingEnabled(True)
        self.output_table.horizontalHeader().setSortIndicatorShown(True)
        
        output_layout.addWidget(self.output_table)
        tables_splitter.addWidget(output_container)
        
        # Set equal sizes for the tables
        tables_splitter.setSizes([300, 300])
        tables_layout.addWidget(tables_splitter)
        
        # Add both panels to the main splitter
        self.main_splitter.addWidget(self.filter_group)
        self.main_splitter.addWidget(tables_container)
        
        # Set initial sizes (30% for filter panel, 70% for tables)
        self.main_splitter.setSizes([300, 700])
        
        # Add main splitter to layout
        self.layout.addWidget(self.main_splitter)
        self.filter_group.setVisible(False)
        
        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.layout.addWidget(self.progress_bar)
        self.progress_bar.setVisible(False)

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.central_widget.setObjectName("central_widget dark")
            self.filter_group.setObjectName("glass dark")
            self.dark_mode_button.setText("Light Mode")
        else:
            self.central_widget.setObjectName("central_widget")
            self.filter_group.setObjectName("glass")
            self.dark_mode_button.setText("Dark Mode")
        self.load_stylesheet()

    def filter_categories(self, text):
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

    def _reset_ui(self):
        self.main_df = None
        self.drop_area.label.setText("Presuňte CSV súbor sem alebo kliknite na tlačidlo nižšie")
        self.drop_area.setMaximumHeight(200)  # Reset drop area height
        self.filter_group.setVisible(False)
        self.generate_button.setVisible(False)
        self.progress_bar.setVisible(False)
        self.seo_details_button.setVisible(False)
        self.seo_details_list.setVisible(False)
        self.seo_details_list.clear()
        self.seo_count_label.setText("(0)")
        self.add_to_output_button.setVisible(False)
        
        # Clear table models
        self.input_model.setDataFrame(pd.DataFrame())
        self.output_model.setDataFrame(pd.DataFrame())
        
    def check_all_visible_rows(self):
        """Check all visible rows in the input table"""
        if not self.input_model or self.input_model.getDataFrame().empty:
            return
            
        # Check all rows that are not hidden
        for proxy_row in range(self.input_proxy_model.rowCount()):
            if not self.input_table.isRowHidden(proxy_row):
                # Map proxy row to source row
                source_index = self.input_proxy_model.mapToSource(self.input_proxy_model.index(proxy_row, 0))
                source_row = source_index.row()
                # Check the row in the source model
                self.input_model.setRowChecked(source_row, True)
                
        # Update the view
        self.input_table.viewport().update()
        
        QMessageBox.information(self, "Označené všetky riadky", "Všetky viditeľné riadky boli označené.")
        
    def uncheck_all_rows(self):
        """Uncheck all rows in the input table"""
        if not self.input_model or self.input_model.getDataFrame().empty:
            return
            
        # Uncheck all rows by clearing the checked rows set
        self.input_model.clearCheckedRows()
        
        # Update the view
        self.input_table.viewport().update()
        
        QMessageBox.information(self, "Odznačené všetky riadky", "Všetky riadky boli odznačené.")
        
    def handle_input_table_click(self, proxy_index):
        """Handle clicks in the input table to toggle checkboxes"""
        if not proxy_index.isValid() or self.input_table.isRowHidden(proxy_index.row()):
            return
            
        # Toggle checkbox when clicking in the checkbox column (column 0)
        if proxy_index.column() == 0:
            # Map the proxy index to the source model index
            source_index = self.input_proxy_model.mapToSource(proxy_index)
            row = source_index.row()
            
            # Get current state from source model and toggle it
            current_state = self.input_model.data(source_index, Qt.CheckStateRole)
            new_state = Qt.Unchecked if current_state == Qt.Checked else Qt.Checked
            
            # Set the new state on the source model
            self.input_model.setData(source_index, new_state, Qt.CheckStateRole)
        
    def filter_input_table(self):
        """Filter the input table based on category selection and SEO preservation"""
        if self.main_df is None:
            return
            
        # Get current data from the input model (preserving any edits)
        current_df = self.input_model.getDataFrame()
        
        # Get selected categories
        selected_categories = []
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_categories.append(item.text())
        
        # Apply category filter
        category_mask = current_df['Hlavna kategória'].isin(selected_categories)
        
        # Apply SEO preservation filter if checked
        if self.preserve_seo_checkbox.isChecked():
            seo_mask = (
                (current_df['SEO titulka'].notna() & (current_df['SEO titulka'] != '')) | 
                (current_df['SEO popis'].notna() & (current_df['SEO popis'] != '')) | 
                (current_df['SEO kľúčové slová'].notna() & (current_df['SEO kľúčové slová'] != ''))
            )
            # Either matches category filter or has SEO data
            final_mask = category_mask | seo_mask
        else:
            final_mask = category_mask
            
        # Hide/show rows in the input table without changing the model
        for row in range(self.input_model.rowCount()):
            self.input_table.setRowHidden(row, not final_mask.iloc[row])
            
        # Update SEO count indicator
        self.update_seo_preserved_count()
    
    def add_selected_rows_to_output(self):
        """Add checked rows from input table to output table"""
        if not self.input_model or self.main_df is None or self.main_df.empty:
            return
            
        # Get checked rows from the model
        checked_rows = self.input_model.getCheckedRows()
        
        if not checked_rows:
            QMessageBox.information(self, "Nie je zaškrtnutý žiadny riadok", "Zaškrtnite aspoň jeden riadok v tabuľke vstupných dát.")
            return
            
        # Get the current input and output data
        input_df = self.input_model.getDataFrame()
        output_df = self.output_model.getDataFrame()
        
        # Get selected data directly using model method
        selected_data = self.input_model.getCheckedRowsData()
        
        # Add selected rows to output table, replacing duplicates based on catalog number
        if output_df.empty:
            # If output is empty, just use the selected data
            self.output_model.setDataFrame(selected_data)
        else:
            # Identify catalog number column if it exists
            catalog_col = None
            for col in output_df.columns:
                if "kat" in col.lower() and "slo" in col.lower():
                    catalog_col = col
                    break
            
            if catalog_col and catalog_col in selected_data.columns:
                # Handle duplicates - remove existing rows with same catalog numbers
                # from the output table and add the new ones
                selected_catalogs = set(selected_data[catalog_col].dropna())
                
                # Filter out rows with matching catalog numbers
                if not selected_catalogs.issubset({None, ''}):
                    output_df = output_df[~output_df[catalog_col].isin(selected_catalogs)]
                
                # Concatenate with selected rows
                output_df = pd.concat([output_df, selected_data], ignore_index=True)
                self.output_model.setDataFrame(output_df)
            else:
                # No catalog column found, just append the rows
                output_df = pd.concat([output_df, selected_data], ignore_index=True)
                self.output_model.setDataFrame(output_df)
        
        # Clear checkboxes after adding to output
        self.input_model.clearCheckedRows()
        self.input_table.viewport().update()
        
        # Auto-resize columns for better visibility
        self.resize_table_columns(self.output_table)
        
        # Show a status message
        count = len(checked_rows)
        QMessageBox.information(self, "Pridané riadky", f"{count} riadkov bolo pridaných do výstupnej tabuľky.")
    
        
    def update_seo_preserved_count(self):
        """Update the count of products preserved due to SEO data"""
        if self.main_df is None:
            self.seo_count_label.setText("(0)")
            return
            
        # Use the input model data which may have edits
        df = self.input_model.getDataFrame()
        
        # Get selected categories
        selected_categories = []
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_categories.append(item.text())

        # Only proceed if SEO preservation is enabled
        if not self.preserve_seo_checkbox.isChecked():
            self.seo_count_label.setText("(0)")
            self.seo_details_list.clear()
            self.seo_details_button.setVisible(False)
            return
            
        # Create mask for selected categories
        category_mask = df['Hlavna kategória'].isin(selected_categories)
        
        # Create mask for products with SEO data
        seo_mask = (
            (df['SEO titulka'].notna() & (df['SEO titulka'] != '')) | 
            (df['SEO popis'].notna() & (df['SEO popis'] != '')) | 
            (df['SEO kľúčové slová'].notna() & (df['SEO kľúčové slová'] != ''))
        )
        
        # Products that have SEO data but are not in selected categories
        seo_preserved = seo_mask & ~category_mask
        count = seo_preserved.sum()
        
        self.seo_count_label.setText(f"({count})")
        self.seo_details_button.setVisible(count > 0)

    def select_csv_file(self):
        downloads_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        file_path, _ = QFileDialog.getOpenFileName(self, "Vyberte CSV súbor", downloads_path, "CSV files (*.csv)")
        if file_path:
            self.load_csv_file(file_path)

    def load_csv_file(self, file_path):
        try:
            self.main_df = load_csv_data(file_path)
            
            if self.main_df is None or self.main_df.empty:
                self._reset_ui()
                return
            
            # Update only input table model with data, leaving output table empty
            self.input_model.setDataFrame(self.main_df)
            self.output_model.setDataFrame(pd.DataFrame())  # Empty output table initially
            
            # Auto-resize columns for better visibility
            self.resize_table_columns(self.input_table)
            
            # Update UI
            self.drop_area.label.setText(f"Nahraný súbor: {file_path.split('/')[-1]}")
            self.drop_area.setMaximumHeight(50)  # Reduce size after loading
            
            if 'Hlavna kategória' in self.main_df.columns:
                # Update the categories list for the filter panel
                self.categories = sorted(self.main_df['Hlavna kategória'].dropna().unique().tolist())
                self.category_list.clear()  # Clear previous categories
                
                # Add categories to the list with checkboxes
                for category in self.categories:
                    item = QListWidgetItem(category)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Checked)
                    item.setData(Qt.UserRole, category)
                    self.category_list.addItem(item)
                
                # Show filter panel and buttons
                self.filter_group.setVisible(True)
                self.generate_button.setVisible(True)
                
                # Show input table selection buttons
                self.add_to_output_button.setVisible(True)
                self.select_all_rows_button.setVisible(True)
                self.clear_all_rows_button.setVisible(True)
                
                # Connect input table changes
                self.input_model.dataChanged.connect(self.filter_input_table)
            else:
                QMessageBox.warning(self, "Chýbajúci stĺpec", "V CSV súbore nebol nájdený stĺpec 'Hlavna kategória'. Filtrovanie nie je možné.")
                self._reset_ui()

        except Exception as e:
            QMessageBox.critical(self, "Chyba načítania", f"Nepodarilo sa načítať CSV súbor.\nChyba: {e}")
            self._reset_ui()
        
        # Clear and populate the list
        self.category_list.clear()
        for category in self.categories:
            item = QListWidgetItem(category)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            # Connect item changes to update SEO count
            item.setData(Qt.UserRole, category)
            self.category_list.addItem(item)
            
        # Select all categories by default
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setCheckState(Qt.Checked)
            
        # Connect to itemChanged signal to detect checkbox changes
        self.category_list.itemChanged.connect(self.on_category_selection_changed)

    def select_all_categories(self):
        # Toggle between selecting all and deselecting all
        all_checked = True
        
        # Check if all items are already checked
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() != Qt.Checked:
                all_checked = False
                break
        
        # Set all items to the opposite state
        new_state = Qt.Unchecked if all_checked else Qt.Checked
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setCheckState(new_state)
            
    def toggle_filtered_categories(self):
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
                
        # Apply the determined state to all visible items
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if not item.isHidden():
                item.setCheckState(new_state)
                
    def update_seo_preserved_count(self):
        """Calculate and display the count of products that would be preserved due to SEO data"""
        if self.main_df is None:
            self.seo_count_label.setText("(0)")
            self.seo_details_button.setVisible(False)
            self.seo_details_list.setVisible(False)
            return
        
        # Get selected categories
        selected_categories = []
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_categories.append(item.text())
        
        # Create mask for selected categories
        category_mask = self.main_df['Hlavna kategória'].isin(selected_categories)
        
        # Create mask for products with SEO data
        seo_mask = (
            (self.main_df['SEO titulka'].notna() & (self.main_df['SEO titulka'] != '')) | 
            (self.main_df['SEO popis'].notna() & (self.main_df['SEO popis'] != '')) | 
            (self.main_df['SEO kľúčové slová'].notna() & (self.main_df['SEO kľúčové slová'] != ''))
        )
        
        # Get products that have SEO data but don't match selected categories
        preserved_products = self.main_df[seo_mask & ~category_mask]
        preserved_count = len(preserved_products)
        
        # Update count label
        self.seo_count_label.setText(f"({preserved_count})")
        
        # Update details button visibility
        self.seo_details_button.setVisible(preserved_count > 0 and self.preserve_seo_checkbox.isChecked())
        
        # Update SEO details list if it's visible
        if self.seo_details_list.isVisible():
            self.populate_seo_details_list(preserved_products)
    
    def populate_seo_details_list(self, preserved_products):
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
    
    def on_category_selection_changed(self, item):
        """Filter input table when category selection changes"""
        # Schedule update with a slight delay to avoid multiple rapid updates
        QTimer.singleShot(100, self.filter_input_table)
    
    def resize_table_columns(self, table_view):
        """Auto-resize columns for better visibility"""
        header = table_view.horizontalHeader()
        for column in range(table_view.model().columnCount()):
            # Limit width to reasonable values to avoid excessively wide columns
            width = min(250, table_view.sizeHintForColumn(column) + 20)  # Add some padding
            header.resizeSection(column, width)
            
    def update_output_preview(self):
        """Update the output table with filtered data based on selected categories"""
        if self.main_df is None:
            return
            
        # Get edited data from input model
        current_df = self.input_model.getDataFrame()
        
        # Get selected categories
        selected_categories = []
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_categories.append(item.text())
        
        # Apply category filter
        category_mask = current_df['Hlavna kategória'].isin(selected_categories)
        
        # Apply SEO preservation filter if checked
        if self.preserve_seo_checkbox.isChecked():
            seo_mask = (
                (current_df['SEO titulka'].notna() & (current_df['SEO titulka'] != '')) | 
                (current_df['SEO popis'].notna() & (current_df['SEO popis'] != '')) | 
                (current_df['SEO kľúčové slová'].notna() & (current_df['SEO kľúčové slová'] != ''))
            )
            # Combine filters to include both category matches and SEO products
            filtered_df = current_df[category_mask | seo_mask].copy()
        else:
            # Only filter by category
            filtered_df = current_df[category_mask].copy()
        
        # Update output model
        self.output_model.setDataFrame(filtered_df)
        
        # Update SEO count indicator
        self.update_seo_preserved_count()
    
    def toggle_seo_details(self):
        """Toggle visibility of SEO preserved products list"""
        # If list is not visible, populate and show it
        if not self.seo_details_list.isVisible():
            # Get selected categories
            selected_categories = []
            for i in range(self.category_list.count()):
                item = self.category_list.item(i)
                if item.checkState() == Qt.Checked:
                    selected_categories.append(item.text())
            
            # Create mask for selected categories
            category_mask = self.main_df['Hlavna kategória'].isin(selected_categories)
            
            # Create mask for products with SEO data
            seo_mask = (
                (self.main_df['SEO titulka'].notna() & (self.main_df['SEO titulka'] != '')) | 
                (self.main_df['SEO popis'].notna() & (self.main_df['SEO popis'] != '')) | 
                (self.main_df['SEO kľúčové slová'].notna() & (self.main_df['SEO kľúčové slová'] != ''))
            )
            
            # Get products that have SEO data but don't match selected categories
            preserved_products = self.main_df[seo_mask & ~category_mask]
            
            # Populate the list
            self.populate_seo_details_list(preserved_products)
            self.seo_details_list.setVisible(True)
            self.seo_details_button.setText("Skryť zachované SEO produkty")
        else:
            # Hide the list
            self.seo_details_list.setVisible(False)
            self.seo_details_button.setText("Zobraziť zachované SEO produkty")

    def generate_and_export_csv(self):
        # Check if we have data in the output table
        output_df = self.output_model.getDataFrame()
        
        if output_df.empty:
            QMessageBox.warning(self, "Prázdny výstup", "Tabuľka výstupu je prázdna. Pridajte produkty do výstupu pomocou tlačidla 'Pridať vybrané riadky do výstupu'.")
            return

        # Get save location
        output_file, _ = QFileDialog.getSaveFileName(self, "Uložiť CSV", "", "CSV súbory (*.csv)")
        if not output_file:
            return
            
        # Get selected categories for XML feed processing
        selected_categories = []
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_categories.append(item.text())

        # Set up worker
        self.thread = QThread()
        # Use data from output table directly
        self.worker = Worker(output_df, selected_categories, self.config, False)  # SEO preservation already handled in the table
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.display_error)
        self.worker.result.connect(lambda df: self.save_csv(df, output_file))

        # Start processing
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_bar.setFormat("Spracovanie dát...")
        self.generate_button.setEnabled(False)
        self.thread.start()
        self.generate_button.setEnabled(False)
        self.thread.finished.connect(lambda: self.generate_button.setEnabled(True))
        self.thread.finished.connect(lambda: self.progress_bar.setVisible(False))

    def update_progress(self, message):
        self.progress_bar.setFormat(message)
        
    def display_error(self, error_info):
        """Display error message from worker thread"""
        title, message = error_info
        QMessageBox.critical(self, title, message)
        self.progress_bar.setVisible(False)
        
    def save_csv(self, df, output_file):
        """Save the final processed dataframe as CSV"""
        try:
            df.to_csv(output_file, index=False, sep=';', encoding='utf-8-sig')
            self.progress_bar.setFormat("Export dokončený!")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Export dokončený", f"Dáta boli úspešne exportované do súboru:\n{output_file}")
        except Exception as e:
            QMessageBox.critical(self, "Chyba exportu", f"Nepodarilo sa exportovať dáta.\nChyba: {e}")
        finally:
            self.progress_bar.setVisible(False)

    def show_error_message(self, error_info):
        title, message = error_info
        QMessageBox.critical(self, title, message)

    def save_final_csv(self, final_df):
        save_path, _ = QFileDialog.getSaveFileName(self, "Uložiť výsledný CSV súbor", "Merged.csv", "CSV files (*.csv)")
        if save_path:
            try:
                final_df.to_csv(save_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "Great success!", f"Súbor bol úspešne uložený do: {save_path}")
            except Exception as e:
                self.show_error_message(("Chyba pri ukladaní", f"Pri ukladaní súboru došlo k chybe:\n{e}"))

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Ukončiť', "Naozaj chcete aplikáciu ukončiť?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = ProductManager()
    main_win.show()
    sys.exit(app.exec_())