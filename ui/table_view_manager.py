"""
Table view manager component for handling input and output tables
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableView,
    QPushButton, QMessageBox, QHeaderView, QAbstractItemView, QSplitter
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, pyqtSignal

from models.pandas_table_model import PandasTableModel
import pandas as pd

class TableViewManager(QWidget):
    """
    Manages the input and output data tables
    Handles display, filtering, and data operations
    """
    # Signals
    dataChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Input Table (Top) ---
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
        self.input_proxy_model.setSortRole(Qt.DisplayRole)
        
        # Set the proxy model on the view
        self.input_table.setModel(self.input_proxy_model)
        
        # Set column width for checkbox column
        self.input_table.setColumnWidth(0, 40)  # Make checkbox column narrow
        
        # Enable sorting
        self.input_table.setSortingEnabled(True)
        self.input_table.horizontalHeader().setSortIndicatorShown(True)
        
        # Connect cell clicks to toggle checkboxes
        self.input_table.clicked.connect(self._handle_input_table_click)
        
        input_layout.addWidget(self.input_table)
        
        # Input table control buttons
        self.input_buttons_layout = QHBoxLayout()
        
        # 'Select All' button
        self.select_all_rows_button = QPushButton("Označiť všetky")
        self.select_all_rows_button.clicked.connect(self.check_all_visible_rows)
        self.select_all_rows_button.setVisible(False)  # Hidden initially until data is loaded
        self.input_buttons_layout.addWidget(self.select_all_rows_button)
        
        # 'Clear All' button
        self.clear_all_rows_button = QPushButton("Odznačiť všetky")
        self.clear_all_rows_button.clicked.connect(self.uncheck_all_rows)
        self.clear_all_rows_button.setVisible(False)  # Hidden initially until data is loaded
        self.input_buttons_layout.addWidget(self.clear_all_rows_button)
        
        # Add spacer to push 'Add to output' button to the right
        self.input_buttons_layout.addStretch(1)
        
        # 'Add to output' button
        self.add_to_output_button = QPushButton("Pridať vybrané riadky do výstupu")
        self.add_to_output_button.clicked.connect(self.add_selected_rows_to_output)
        self.add_to_output_button.setVisible(False)  # Hidden initially until data is loaded
        self.input_buttons_layout.addWidget(self.add_to_output_button)
        
        input_layout.addLayout(self.input_buttons_layout)
        
        # --- Output Table (Bottom) ---
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
        self.output_proxy_model.setSortRole(Qt.DisplayRole)
        
        # Set proxy model on the view
        self.output_table.setModel(self.output_proxy_model)
        
        # Enable sorting
        self.output_table.setSortingEnabled(True)
        self.output_table.horizontalHeader().setSortIndicatorShown(True)
        
        output_layout.addWidget(self.output_table)
        
        # Add to main layout with splitter
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(input_container)
        self.splitter.addWidget(output_container)
        self.splitter.setSizes([300, 300])  # Equal initial sizes
        
        layout.addWidget(self.splitter)
        
        # Connect to data changed signals
        self.input_model.dataChanged.connect(self._on_data_changed)
    
    def set_input_data(self, dataframe):
        """Set the input table data"""
        self.input_model.setDataFrame(dataframe)
        self.resize_table_columns(self.input_table)
        
        # Show control buttons if we have data
        has_data = not dataframe.empty if dataframe is not None else False
        self.select_all_rows_button.setVisible(has_data)
        self.clear_all_rows_button.setVisible(has_data)
        self.add_to_output_button.setVisible(has_data)
        
    def set_output_data(self, dataframe):
        """Set the output table data"""
        self.output_model.setDataFrame(dataframe)
        self.resize_table_columns(self.output_table)
        
    def get_input_data(self):
        """Get the current input data"""
        return self.input_model.getDataFrame()
        
    def get_output_data(self):
        """Get the current output data"""
        return self.output_model.getDataFrame()
    
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
        
    def _handle_input_table_click(self, proxy_index):
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
    
    def add_selected_rows_to_output(self):
        """Add checked rows from input table to output table"""
        if not self.input_model or self.input_model.getDataFrame().empty:
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
    
    def filter_input_rows(self, mask):
        """
        Filter input table rows based on the given boolean mask
        Does not modify the data model, only hides/shows rows
        """
        if self.input_model.getDataFrame().empty:
            return
            
        # Hide/show rows in the input table without changing the model
        for row in range(self.input_model.rowCount()):
            self.input_table.setRowHidden(row, not mask.iloc[row])
    
    def resize_table_columns(self, table_view):
        """Auto-resize columns for better visibility"""
        header = table_view.horizontalHeader()
        for column in range(table_view.model().columnCount()):
            # Limit width to reasonable values to avoid excessively wide columns
            width = min(250, table_view.sizeHintForColumn(column) + 20)  # Add some padding
            header.resizeSection(column, width)
    
    def reset(self):
        """Reset the table views"""
        self.input_model.setDataFrame(pd.DataFrame())
        self.output_model.setDataFrame(pd.DataFrame())
        self.select_all_rows_button.setVisible(False)
        self.clear_all_rows_button.setVisible(False)
        self.add_to_output_button.setVisible(False)
    
    def _on_data_changed(self):
        """Handle data changes in the input model"""
        self.dataChanged.emit()
