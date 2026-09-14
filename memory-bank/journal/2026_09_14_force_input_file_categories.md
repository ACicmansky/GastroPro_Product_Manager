# Category Mapping — Force Names from Input File & "Apply to All" Checkbox

## Context
During the category mapping stage (`Mapping categories...`), when products from an uploaded input file (e.g., `products (2).xlsx`) contained categories not yet present in `categories.json` and not starting with `"Tovary a kategórie > "`, `CategoryMappingDialog` repeatedly prompted the user for each individual product. Accepting the original category did not cache identity mappings in memory, leading to repeated prompts for the same category across thousands of rows.

## What Was Done
1. **CategoryService Enhancements (`src/domain/categories/category_service.py`)**:
   - Added `file_categories: set[str]` and `force_file_categories: bool` (with `set_file_categories` and `set_force_file_categories`).
   - Added an in-memory `_session_mappings: dict[str, str]` cache so any category resolved during the session (whether mapped, kept as-is, or forced) is cached and never asked again in the same run.
   - When `force_file_categories` is enabled and `old_category in file_categories`, `map_or_ask` immediately returns `old_category` without calling the interactive callback.
2. **CategoryMappingDialog (`src/gui/widgets.py`)**:
   - Added `is_from_file` and `has_input_file` parameters to the dialog.
   - Added `apply_to_all_from_file_cb` checkbox (`"Aplikovať na všetky kategórie zo súboru"`).
   - Added `force_file_button` (`"📁 Vnútiť názov zo súboru"`), allowing immediate acceptance with the original category name.
   - Added `should_apply_to_all_from_file() -> bool`.
3. **PipelineWorker (`src/gui/worker.py`)**:
   - Extended `set_category_mapping_result(new_category, apply_to_all_from_file=False)` to dynamically enable `category_service.set_force_file_categories(True)`.
4. **Pipeline Orchestrator (`src/pipeline/pipeline.py` & `src/domain/models.py`)**:
   - Added `force_file_categories: bool = False` to `PipelineOptions`.
   - In `Pipeline.run`, extracted unique `file_categories` from `main_df` and passed them to `category_service`.
5. **MainWindow (`src/gui/main_window.py`)**:
   - Added `force_file_categories_checkbox` (`"Vnútiť kategórie zo vstupného súboru"`) under "Možnosti spracovania".
   - Enabled/disabled based on whether main data is loaded.
   - Updated `handle_category_mapping_request` to detect `is_from_file`, pass context to `CategoryMappingDialog`, and propagate `apply_to_all`.

## Verification
- Added unit tests in `tests/test_category_service.py`:
  - `test_force_file_categories_skips_callback`
  - `test_force_file_categories_still_calls_callback_for_non_file_categories`
  - `test_session_mappings_prevents_duplicate_prompts_for_identical_categories`
- Added GUI unit tests in `tests/test_gui_window.py`:
  - `test_mapping_dialog_force_file_and_apply_to_all`
  - `test_main_window_force_file_categories_toggles`
- Added integration test in `tests/test_pipeline_new_format.py`:
  - `test_pipeline_force_file_categories`
- Ran full test suite via `uv run poe check`: all 231 tests passed with clean linting and formatting.

## Deferred Items
None.
