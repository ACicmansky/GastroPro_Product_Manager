# CategoryMappingManager Implementation

**Date**: 2025-10-02
**Status**: ✅ Completed

## Problem Statement

Prior to this implementation, category mappings were loaded from disk (`categories.json`) multiple times across different components:
- `DataPipeline` loaded mappings when processing CSV categories
- `Scraper` loaded mappings in `__init__`
- `parse_xml_feed` loaded mappings for each feed

This resulted in:
1. **Duplicate disk I/O** - Same file loaded multiple times per run
2. **No in-memory caching** - New mappings saved during processing weren't immediately available
3. **Repeated user prompts** - If two products had the same unmapped category, user was prompted twice
4. **Scattered state management** - No single source of truth for mappings

## Solution: CategoryMappingManager

Created a centralized manager class in `src/utils/config_loader.py` that provides:

### Core Features

1. **Single Load**: Mappings loaded once on initialization
2. **In-Memory Cache**: Fast lookups without disk I/O
3. **Immediate Updates**: New mappings added to both cache AND disk
4. **Thread-Safe**: Uses existing `_category_mappings_lock`
5. **Single Source of Truth**: All components access same manager instance

### API Methods

```python
class CategoryMappingManager:
    def __init__(self, mappings_path='categories.json')
        # Loads mappings from disk into memory cache
    
    def reload()
        # Reload mappings from disk (if file changed externally)
    
    def get_all() -> List[Dict]
        # Get copy of all mappings
    
    def find_mapping(old_category: str) -> str
        # Fast lookup in cache, returns None if not found
    
    def add_mapping(old_category: str, new_category: str) -> bool
        # Add to cache + save to disk, prevents duplicates
    
    def get_unique_categories() -> List[str]
        # Get unique target categories for suggestions
```

## Implementation Details

### Architecture Flow

```
DataPipeline.__init__
    ↓
Creates CategoryMappingManager (loads categories.json once)
    ↓
Passes to Scraper + parse_xml_feed
    ↓
When unmapped category found:
    1. Check manager.find_mapping() (fast cache lookup)
    2. If not found → trigger interactive callback
    3. User provides mapping
    4. manager.add_mapping() → updates cache + saves to disk
    5. Next product with same category → found in cache (no prompt!)
```

### Files Modified

1. **`src/utils/config_loader.py`**
   - Added `CategoryMappingManager` class (118 lines)
   - Methods: `__init__`, `reload`, `get_all`, `find_mapping`, `add_mapping`, `get_unique_categories`
   
2. **`src/core/data_pipeline.py`**
   - Creates `CategoryMappingManager` in `__init__`
   - Passes to scraper and feed processor
   - Uses manager for CSV category mapping

3. **`src/services/scraper.py`**
   - Accepts `category_manager` parameter
   - `map_category()` uses manager for lookups and adds
   - Removed local `load_category_mappings()` call

4. **`src/utils/feed_processor.py`**
   - `parse_xml_feed()` accepts `category_manager`
   - `process_gastromarket_text()` uses manager
   - `process_forgastro_category()` uses manager
   - Removed imports of `map_category` and `load_category_mappings`

5. **`src/gui/worker.py`**
   - Stores `pipeline` reference for MainWindow access

6. **`src/gui/main_window.py`**
   - Accesses manager via `worker.pipeline.category_manager`
   - Uses `manager.get_unique_categories()` for suggestions
   - Removed redundant `save_category_mapping()` call
   - Removed unused imports

## Benefits

### Performance
- ✅ **Single disk read** instead of 4+ reads per run
- ✅ **O(n) cache lookups** instead of repeated file parsing
- ✅ **Instant availability** of new mappings

### User Experience
- ✅ **No duplicate prompts** - Same category asked once per session
- ✅ **Faster processing** - No waiting for disk I/O
- ✅ **Consistent state** - All components see same mappings

### Code Quality
- ✅ **Single responsibility** - Manager owns all mapping logic
- ✅ **Reduced coupling** - Components depend on manager, not file system
- ✅ **Easier testing** - Can mock manager instead of file I/O
- ✅ **Cleaner code** - No scattered `load_category_mappings()` calls

## Testing Considerations

- Verify manager created once per pipeline run
- Test duplicate category doesn't prompt twice
- Verify new mapping immediately available to subsequent products
- Test thread safety with concurrent mapping requests
- Verify mappings persist to disk correctly
- Test manager works with empty/missing categories.json
- Verify suggestions list includes newly added categories

## Example Scenario

**Before CategoryMappingManager:**
```
Product 1: Category "/e-shop/chladnicky" → Not found → User prompted
Product 2: Same category → Load from disk → Not found → User prompted again! ❌
```

**After CategoryMappingManager:**
```
Product 1: Category "/e-shop/chladnicky" → cache.find() → Not found → User prompted
         → User maps to "Chladenie/Chladničky"
         → manager.add_mapping() → cache updated + disk saved
Product 2: Same category → cache.find() → "Chladenie/Chladničky" ✅ (no prompt!)
```

## Related Features

This enhancement works in conjunction with:
- Interactive category mapping dialog (2025-10-02)
- Smart category suggestions with rapidfuzz (2025-10-02)
- Product name context display (2025-10-02)
- Auto-save to categories.json (2025-10-02)

## Future Enhancements

- Session-based mapping cache (in-memory only, not persisted)
- Analytics: track most frequently mapped categories
- Bulk import/export of mappings
- Mapping validation and conflict detection
- Category hierarchy analysis and suggestions
