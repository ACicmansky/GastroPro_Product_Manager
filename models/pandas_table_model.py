"""
Table model for displaying pandas DataFrame in QTableView
"""
import pandas as pd
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant

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
        
    def clearCheckedRows(self):
        """Clear all checked rows"""
        self._checked_rows.clear()
        
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
