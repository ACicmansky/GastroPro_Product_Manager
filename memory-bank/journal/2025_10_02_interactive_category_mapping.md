# Interactive Category Mapping Feature

**Date**: 2025-10-02  
**Status**: Completed

## Overview
Implemented an interactive category mapping feature that pauses the entire data processing pipeline when an unmapped category is encountered, displays a modal dialog for user input, and resumes processing with the user-provided category name.

## Problem Statement
During XML parsing and web scraping, the application would encounter categories without existing mappings in `categories.json`. Previously, these would either be logged as warnings or left unmapped, requiring post-processing or manual configuration file updates.

## Solution

### Architecture
Implemented a callback-based system with thread-safe signal/slot communication between the worker thread (data pipeline) and the UI thread:

```
[Worker Thread]              [UI Thread]
DataPipeline                 MainWindow
    ↓                            ↑
get_scraped_products         CategoryMappingDialog
    ↓                            ↑
map_category() ----------→ [Signal/Slot] → show dialog
    ↓                            ↓
[Wait for result] ←-------- user input
    ↓
Continue processing
```

### Components Created/Modified

#### 1. **CategoryMappingDialog** (`src/gui/widgets.py`)
- Modal dialog with:
  - Label displaying the unmapped category
  - Input field for new category name
  - OK button to confirm and resume
- Auto-focuses input field for quick data entry
- Returns user-provided category name

#### 2. **Worker Thread Signals** (`src/gui/worker.py`)
- Added `request_category_mapping` signal (str)
- Implemented `request_category_mapping_sync()` method:
  - Emits signal to UI thread
  - Uses `QEventLoop` to block worker thread
  - Waits synchronously for user input
  - Returns result to caller
- Added `set_category_mapping_result()` method:
  - Called by UI thread with user input
  - Quits event loop to resume worker

#### 3. **Category Mapper** (`src/utils/category_mapper.py`)
- Modified `map_category()` to accept optional `interactive_callback` parameter
- Invokes callback when no mapping is found in configuration
- Falls back to original category if callback returns None

#### 4. **Scraper Service** (`src/services/scraper.py`)
- Updated `TopchladenieScraper.__init__()` to accept `category_mapping_callback`
- Modified `map_category()` method to use interactive callback
- Updated `FastTopchladenieScraper` to pass callback through
- Updated `get_scraped_products()` to accept and forward callback

#### 5. **Data Pipeline** (`src/core/data_pipeline.py`)
- Modified `__init__()` to accept `category_mapping_callback`
- Updated `_process_scraping()` to pass callback to scraper

#### 6. **Main Window** (`src/gui/main_window.py`)
- Connected `worker.request_category_mapping` signal to handler
- Implemented `handle_category_mapping_request()`:
  - Creates and displays `CategoryMappingDialog`
  - Passes user input back to worker thread
  - Handles dialog cancellation gracefully

## Technical Implementation Details

### Thread Safety
- Used Qt's signal/slot mechanism for cross-thread communication
- Worker thread blocks using `QEventLoop.exec_()` while waiting
- UI thread remains responsive to handle dialog interaction
- Event loop is quit when result is provided

### Flow Control
1. Worker encounters unmapped category during scraping
2. Emits `request_category_mapping` signal with category URL/name
3. Worker blocks on event loop
4. UI thread receives signal and displays dialog
5. User enters new category name and clicks OK
6. UI thread calls `worker.set_category_mapping_result()`
7. Event loop quits, worker unblocks
8. Processing continues with user-provided category

### Error Handling
- Dialog cancellation returns original unmapped category
- Empty input is rejected (OK button requires non-empty text)
- Graceful fallback if callback is not provided

## Integration Points

### Before Line: `category_mapper.py:L30`
```python
# No mapping found - use interactive callback if provided
if interactive_callback:
    new_category = interactive_callback(category)
    if new_category:
        return new_category

return category
```

### Before Line: `scraper.py:L220`
```python
# No mapping found - use interactive callback if provided
if self.category_mapping_callback:
    logger.info(f"Requesting interactive mapping for category URL: {category_url}")
    new_category = self.category_mapping_callback(category_url)
    if new_category:
        return new_category

logger.warning(f"No mapping found for category URL: {category_url}")
return category_url
```

### XML Feed Processing Integration
The callback was also integrated into XML feed processing:

**`feed_processor.py:L70` and `L81`**
- Modified `process_gastromarket_text()` to accept `category_mapping_callback`
- Modified `process_forgastro_category()` to accept `category_mapping_callback`
- Updated `parse_xml_feed()` to accept and forward the callback
- Both gastromarket and forgastro feeds now support interactive category mapping

**Flow in DataPipeline**
```python
parse_xml_feed(
    root, 
    feed_info['root_element'], 
    feed_info['mapping'], 
    feed_name,
    category_mapping_callback=self.category_mapping_callback
)
```

## Benefits
1. **User Control**: Operators can define mappings on-the-fly during processing
2. **No Process Interruption**: Pipeline continues seamlessly after user input
3. **Immediate Feedback**: Users see exactly which categories need mapping
4. **Flexible Workflow**: Optional feature - works with or without callback
5. **Thread-Safe**: Properly handles cross-thread communication

## Implemented Enhancements

### ✅ Automatic Saving to categories.json
- **Implementation Date**: 2025-10-02
- New mappings are automatically saved to `categories.json` when user provides input
- Thread-safe file writing with Lock mechanism
- Duplicate check prevents overwriting existing mappings
- Visual feedback shows saved mapping in progress bar
- Proper JSON formatting with UTF-8 encoding

**Implementation Details:**
1. Added `save_category_mapping()` function to `src/utils/config_loader.py`
2. Thread-safe with `_category_mappings_lock`
3. Loads existing mappings, checks for duplicates, appends new mapping, saves with proper formatting
4. MainWindow's `handle_category_mapping_request()` automatically calls save function
5. User sees confirmation in progress bar when mapping is saved

**Benefits:**
- No manual editing of `categories.json` required
- Mappings persist across application sessions
- Reduces repeated prompts for same category
- Maintains clean JSON formatting

### ✅ Smart Category Suggestions
- **Implementation Date**: 2025-10-02
- Suggests top 5 similar categories using rapidfuzz + hierarchical matching
- Shows similarity percentage for each suggestion
- Clickable suggestions populate the input field
- High confidence matches (≥80%) displayed in bold
- Sources categories from both existing mappings and loaded CSV

### ✅ Product Name Context Display
- **Implementation Date**: 2025-10-02
- Dialog now shows the product name that triggered the unmapped category
- Provides better context for category mapping decisions
- Product name displayed in highlighted blue box above category
- Works for both web scraping and XML feed processing

**Similarity Algorithm:**
1. **Full string similarity** (40% weight) - Overall match
2. **Token sort similarity** (30% weight) - Handles word order differences  
3. **Partial similarity** (20% weight) - Handles substring matches
4. **Hierarchical bonus** (10% weight) - Rewards shared parent paths in category hierarchy

**Implementation Details:**
1. Added `get_category_suggestions()` function to `src/utils/category_mapper.py`
2. Uses rapidfuzz.fuzz for multiple similarity metrics
3. Handles hierarchical categories (split by "/") with bonus for shared structure
4. Updated `CategoryMappingDialog` with QListWidget for suggestions + product name display
5. MainWindow collects categories from mappings + CSV before showing dialog
6. Suggestions are clickable and populate input field for user adjustment
7. Callback signature updated to pass product_name through entire chain (scraper → map_category → worker → dialog)
8. Product name extracted from scraped data and XML feed rows

**Benefits:**
- Reduces user typing and errors
- Learns from existing category structure
- Respects hierarchical category organization
- Visual confidence indicators (percentage + bold for high matches)
- Users can still customize suggestions before confirming

## Future Enhancements
- Cache of interactive mappings per session to avoid repeated prompts during same run
- Batch mode: collect all unmapped categories first, then prompt once
- UI button to review and edit saved mappings
- Machine learning to improve suggestions over time

## Files Modified
- `src/gui/widgets.py` - Added CategoryMappingDialog with suggestions list UI
- `src/gui/worker.py` - Added signal/event loop mechanism + tracking of original category
- `src/gui/main_window.py` - Added signal handler + automatic saving logic + suggestion collection
- `src/utils/category_mapper.py` - Added callback parameter + get_category_suggestions() function
- `src/utils/config_loader.py` - Added save_category_mapping() function with thread safety
- `src/utils/feed_processor.py` - Added callback parameter to all processing functions
- `src/services/scraper.py` - Added callback parameter and invocation
- `src/core/data_pipeline.py` - Added callback parameter propagation to both feeds and scraper

## Testing Considerations
- Test dialog appearance and behavior
- Verify thread blocking/unblocking works correctly
- Test cancellation handling
- Verify empty input rejection
- Test with and without callback provided
- Verify mappings are saved correctly to categories.json
- Test duplicate mapping prevention
- Verify JSON formatting remains valid after save
- Test concurrent save attempts (thread safety)
- Verify progress bar shows save confirmation
- Test that saved mappings persist across application restarts
- Test suggestions with various unmapped categories
- Verify similarity percentages are accurate
- Test clicking suggestions populates input field correctly
- Verify bold formatting for high confidence matches (≥80%)
- Test with hierarchical vs flat category structures
- Verify suggestions when no existing categories available
- Test user can modify suggested category before confirming
- Verify product name displays correctly in dialog
- Test product name display for web scraped products
- Test product name display for XML feed products (gastromarket, forgastro)
- Verify dialog still works when product name is None/empty
