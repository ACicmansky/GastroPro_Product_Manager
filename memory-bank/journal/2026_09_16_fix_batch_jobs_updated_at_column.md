# Fix missing `updated_at` column in `batch_jobs` table

## Date
2026-09-16

## Problem
During a full catalog run, the worker crashed right after successfully submitting the first batch job to Google Cloud (`batches/m0exw8msh1ldil6tsyeljnxiqp1r5dmhzka1`):
```
sqlite3.OperationalError: no such column: updated_at
  File "src/ai/batch_orchestrator.py", line 368, in _wait_for_job
    self.batch_job_db.update_status(job_name, state)
  File "src/data/database/batch_job_db.py", line 58, in update_status
```
The existing `batch_jobs` table in `data/products.db` lacked the `updated_at` column because SQLite's `CREATE TABLE IF NOT EXISTS` does not modify preexisting tables when new columns are defined.

## Changes
1. **Schema Migration in Code**:
   - Updated `BatchJobDB._init_table()` in `src/data/database/batch_job_db.py` to check `PRAGMA table_info(batch_jobs)` and automatically run `ALTER TABLE batch_jobs ADD COLUMN updated_at TIMESTAMP` (and `details`) if missing.
2. **Database Fix**:
   - Executed `ALTER TABLE batch_jobs ADD COLUMN updated_at TIMESTAMP;` on `data/products.db`.
3. **Resumable State Recovery**:
   - Updated `src/gui/main_window.py` so that `_check_resumable_ai_run` recognizes runs in `"running"` as well as `"interrupted"`/`"paused"`, correctly rendering the resume banner.
   - Updated `src/gui/worker.py` to catch unhandled exceptions and set `RunDB` status to `"interrupted"`.
   - Updated Run 1 status in `enhancement_runs` to `"interrupted"`.

## Verification
- Checked Google Cloud Gemini Batch API: Job `batches/m0exw8msh1ldil6tsyeljnxiqp1r5dmhzka1` is still running in Google's cloud (`JOB_STATE_RUNNING`).
- Tested `BatchJobDB.update_status()`: succeeds with zero SQLite errors.
- Ran test suite: All 244 tests pass (`uv run poe check`).
- Ready to resume without re-running or losing any work.
