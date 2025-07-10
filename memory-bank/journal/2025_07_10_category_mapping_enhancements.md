# Category Mapping Enhancements (2025-07-10)

## Summary
Enhanced the category mapping functionality in GastroPro Product Manager to standardize categories from both XML feeds and the input CSV file using a unified mapping approach.

## Implementation Details

### Core Changes
1. **Universal Category Mapping Structure**:
   - Modified `load_category_mappings()` to work with a simplified universal JSON array format 
   - Changed the return type from dict to list for simpler processing
   - Each mapping entry has "oldCategory" and "newCategory" properties

2. **Centralized Mapping Functions**:
   - Added `map_category()` function to map individual category strings
   - Created `map_dataframe_categories()` function to process entire DataFrames

3. **Flexible Category Mapping Application**:
   - Added a UI checkbox "Migrovat CSV kategorie" to control whether CSV categories are mapped
   - Moved category mapping from CSV load time to export time
   - Applied mapping just before XML feed fetching to ensure consistent processing

4. **UX Improvements**:
   - Added progress messages during category mapping
   - Made category mapping optional via checkbox (enabled by default)

### Technical Notes
- Category mappings now follow a standardized format across all data sources
- The same code path is used for mapping categories from XML feeds and CSV input
- Comprehensive logging reports how many categories were mapped
- User can choose whether to apply mappings at export time

## Code Locations
- **utils.py**: Added `map_category()` and `map_dataframe_categories()` functions
- **app.py**: 
  - Updated Worker class to perform mapping during export
  - Added checkbox to the filter UI section
  - Removed closeEvent method (user requested removal)
