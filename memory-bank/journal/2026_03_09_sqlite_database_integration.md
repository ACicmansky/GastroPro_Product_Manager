# SQLite Database Integration

**Date:** 2026-03-09

## Objective
The application suffered data loss when clients took the system-generated XLSX export, modified it inside their e-shop or Excel, and uploaded it back to the program. E-shops typically strip internal contextual columns not relevant to the user, like `aiProcessed`, `aiProcessedDate`, `source`, and `last_updated`.

To prevent this data destruction, the objective was to implement a local SQLite Database to act as the single source of truth for the application. The system would use the database as the foundational load layer. Incoming client files would merely UPSERT the database, ensuring that internal identifiers were safely preserved.

## Implementation Details

### Database Manager (`ProductDatabase`)
Created `src/core/database.py` with `ProductDatabase` using `sqlite3`.
The manager initiates an internal `sqlite3` connection allowing queries across multiple threads (`check_same_thread=False`). The internal table schema is dynamically constructed on the fly reading from `config.json` parameter arrays `final_csv_columns` and `new_output_columns`, with columns defaulting to `TEXT`.

### Upsert Logic 
Designed `upsert_from_client(df)` which efficiently loops over the client's dataset. Crucially, the system attempts to pull `aiProcessed`, `aiProcessedDate`, `source`, and `last_updated` from the database directly matching the specific row. If these are found in the DB but absent or null in the client file, the DB values forcefully replace the missing data on the loaded DataFrame frame.
The rest of the pipeline executes identically.
Finally `upsert_final(df)` uses standard SQLite `INSERT OR REPLACE INTO` behavior from a temporary table to efficiently overwrite all modifications.

### Automatic Rotating Backups
Implemented `backup_db()` to create an instant copy of `products.db` directly into `data/backups/products_YYYYMMDD_HHMMSS.db`. Limit policies restrict the amount of backups stored to 10 across runs, ensuring zero data loss incase the UPSERT goes catastrophically wrong, but minimal disk space consumption.

### Component Integration & Bug Fixes
- Config file `config.json` was augmented with the `db_path` config targeting `data/products.db`. 
- Modified `PipelineNewFormat` entirely natively, pushing instantiation to load the DB prior to returning the worker DataFrame.
- Addressed `KeyError` and `IndexError` index alignment anomalies inside `OutputTransformer.apply_direct_mappings()` after `aiProcessed` row removals decoupled indices. Safely ensured non-existent dataset selections don't throw during CSV validation. 
- Passed all comprehensive automated test suites successfully.

## Significance
This transition formally separates data presentation from data state. The application can now safely accept destructively modified spreadsheets from third party E-shop systems without purging critical historical ML processing timestamps.
