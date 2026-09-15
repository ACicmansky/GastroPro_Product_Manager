# Journal Entry: September 15, 2026 - Authoritative Live Categories & Ponytail Cleanup

## Problem
The user pointed out that the input file is an export directly from their live website and must always be treated as authoritative (never remapped, never questioned). Previously, forcing input categories was an optional unchecked toggle in the GUI, which meant that running web scraping or AI tasks without an uploaded input file caused the app to question and prompt for live categories stored in the database. Additionally, `unique_categories.txt` was an obsolete unreferenced file.

## Solution (Ponytail)
Applied the Ponytail engineering principles (YAGNI, minimal working code, deletion over addition):
1. **Deleted `unique_categories.txt`**: Unreferenced dead file left over from a deleted script.
2. **Authoritative Live Categories**:
   - `CategoryService`: Made `map_or_ask` immediately preserve `file_categories` as-is.
   - `CategoryService.is_target_category`: Categories in `file_categories` are recognized as valid targets.
   - `CategoryService.get_unique_target_categories`: Combines `categories.json` mappings with `file_categories`.
   - `Pipeline.run`: Automatically registers categories from both the input file and existing `source="core"` DB products into `file_categories`.
   - `PipelineOptions`: `force_file_categories: bool = True` set as default.
   - `BatchOrchestrator`: Added `_get_expected_params(cat)` to cleanly handle category lookup with or without the legacy `"Tovary a kategórie > "` prefix.
3. **UI Simplification**:
   - Removed `force_file_categories_checkbox` from `MainWindow` (live category preservation is now always on).
   - Removed `apply_to_all_from_file_cb` and `force_file_button` from `CategoryMappingDialog` (dialog only prompts for external feed/scraper products).

## Verification
- Added tests in `tests/test_category_service.py` and `tests/test_pipeline_new_format.py` validating that file and DB core categories skip callbacks and act as targets.
- Ran `uv run poe check`: all 244 tests passing, clean Ruff lint and format.
