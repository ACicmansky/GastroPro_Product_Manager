# 2026-09-17: Export Products from Database to Final Excel Functionality

## Context & User Need
Users frequently maintain and update the product catalog directly within the local SQLite database (`data/products.db`), where products have undergone AI copywriting, FAQ generation, category parameter extraction, and image restoration. Previously, generating the final Excel file required initiating the full pipeline (`process_and_export`), which involves XML feed downloads, scraping, and potential re-merging. Users needed a direct, one-click mechanism (via a button) to export the catalog from the database into the final 138-column e-shop Excel (`.xlsx`) format.

## Implementation Details

1. **Pipeline Core (`src/pipeline/pipeline.py`)**:
   - Added `export_from_db(output_path, selected_categories=None, on_progress=None) -> PipelineResult`.
   - Fetches products from `ProductDB.get_all()`.
   - Validates non-empty product set (raises `RuntimeError` if empty).
   - Filters by `selected_categories` if a category subset is provided.
   - Applies `apply_feed_specs(df)` for deterministic feed dimension/weight overrides.
   - Transforms data via `OutputTransformer.transform(df)`.
   - Serializes to Excel via `write_xlsx(output_df, output_path)`.

2. **Output Transformer Optimization (`src/domain/transform/output_transformer.py`)**:
   - Updated `apply_direct_mappings()` to explicitly preserve and forward all dynamic `filteringProperty:*` columns from incoming DataFrame, ensuring extracted AI filter parameters (e.g. `filteringProperty:Šírka (mm)`) are preserved in exported files.

3. **Background Worker & Threading (`src/gui/worker.py`)**:
   - Added `DBExportWorker(QObject)` executing `Pipeline.export_from_db` on a background `QThread`.
   - Emits Qt signals: `progress`, `statistics` (`total_products`, `duration`), `result`, `error`, and `finished`.

4. **GUI Main Window & Styling (`src/gui/main_window.py`, `styles/main.qss`)**:
   - Added `export_db_button` (`💾 Exportovať z databázy`) into a horizontal layout alongside the primary process button.
   - Registered keyboard shortcut `Ctrl+E` for quick export.
   - Wired `export_from_db` with `QFileDialog.getSaveFileName` pre-filled with date-stamped filename.
   - UI states: disables inputs during export, sets stage tracker to `export`, provides toast notifications with 1-click open actions ("Otvoriť" / "Otvoriť priečinok").
   - Styled `QPushButton#exportDbButton` in `main.qss`.

5. **CLI Tooling (`scripts/pipeline_cli.py`)**:
   - Added `export` subcommand (`python scripts/pipeline_cli.py export -o final.xlsx [--categories ...]`).

6. **Automated Testing (`tests/`)**:
   - Added 3 unit tests in `tests/test_pipeline_new_format.py` covering full DB export, category filtering, and empty DB error handling.
   - Added 2 UI tests in `tests/test_gui_window.py` for button properties, shortcut, and worker execution.
   - Test suite: **255 tests passing** (100% pass rate).
