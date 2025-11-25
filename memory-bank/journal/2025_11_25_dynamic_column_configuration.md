# Journal Entry: Dynamic Column Configuration

**Date**: November 25, 2025
**Focus**: Implementing automatic column configuration update based on input file.

## 1. Context
The user requested a feature to automatically detect new or missing columns when loading an input XLSX file, and provide a GUI to update `config.json` accordingly. The goal was to ensure all input columns can be included in the output, and unused columns can be removed from the configuration.

## 2. Changes Implemented

### A. New Dialog: `ColumnConfigDialog`
- **File**: `src/gui/column_config_dialog.py` (NEW)
- **Purpose**: Present users with two lists:
  1. **Columns to Add**: Found in input but missing from config
  2. **Columns to Remove**: Present in config but missing from input
- **Features**:
  - Each item has a checkbox for user selection
  - "Add" list has items checked by default
  - "Remove" list has items unchecked by default (safety)
  - OK/Cancel buttons for confirmation

### B. Configuration Utility
- **File**: `src/utils/config_loader.py`
- **Action**: Added `save_config(config, config_path)` function
- **Purpose**: Persist configuration changes to disk in JSON format with proper encoding

### C. Main Window Integration
- **File**: `src/gui/main_window_new_format.py`
- **Method**: `_check_column_configuration(df)`
- **Logic**:
  1. Compare input columns with `config["new_output_columns"]`
  2. Identify columns to add (in input, not in config)
  3. Identify columns to remove (in config, not in input)
  4. Filter out generated columns from removal suggestions (variants, images, AI tracking)
  5. Show dialog if differences exist
  6. Update config on user confirmation
  7. Display success/failure message

### D. Imports
- Added imports for `ColumnConfigDialog` and `save_config` in `main_window_new_format.py`

## 3. Verification
Created and ran `tests/verify_column_config.py`:
- **Test 1**: Changes detected → Dialog triggered → Config updated correctly
- **Test 2**: No changes → Dialog NOT triggered
- **Result**: All tests passed ✅

## 4. User Testing
User successfully loaded a test XLSX file with 6415 rows and 139 columns, confirming the feature works as expected.

## 5. Benefits
- **Flexibility**: Users can easily adapt to new data schemas
- **Safety**: Shows what will change before applying
- **Transparency**: Clear indication of what was added/removed
- **Automation**: Reduces manual config.json editing errors
