# Plan — Resumable AI enhancement runs with UI tracking & controls

*Status: PLANNED (2026-07-07), not implemented. Goal: user can Continue an interrupted AI run "like nothing happened" — after money running out, network loss, API outage, app close.*

## Why the current design can't resume properly

`BatchOrchestrator.process()` submits the **whole run as ONE batch job** (all requests in one JSONL → one upload → one `create_batch_job` → poll → download → apply). Consequences:

- Results apply only after the *entire* job reaches `JOB_STATE_SUCCEEDED`. Failure/expiry mid-job = **zero products saved**.
- `batch_jobs` table tracks only the job pointer, not which products a run intended to cover — a force-run restart re-enqueues all ~9,657 products.
- The polling loop retries forever on network errors (`time.sleep(30); continue`) — GUI thread hangs indefinitely with no way out.
- No pause/cancel; no run-level progress; AI runs only inside the full GUI pipeline, so "resume" would require re-running feeds/merge.

## Core design: runs → chunks → jobs

A **run** = one enhancement campaign over a fixed product set. It is split into **chunks** (~500 products each, config `ai_enhancement.chunk_size`). Each chunk becomes its own small batch job, processed **sequentially**: build JSONL → upload → create job → poll → download → parse → apply to df → **upsert chunk's rows to ProductDB → mark chunk applied**. Interruption at any point loses at most one chunk's cloud time (the job keeps running server-side and is picked up on resume via its stored `job_name`).

### New SQLite tables (same DB file as `batch_jobs`; new class `RunDB` in `src/data/database/run_db.py`)

```sql
CREATE TABLE enhancement_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,           -- running | paused | interrupted | completed | cancelled
    force_reprocess INTEGER,
    total_products INTEGER,
    processed_products INTEGER DEFAULT 0,
    detail TEXT DEFAULT '',         -- human reason: "quota exceeded", "network lost", ...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE run_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES enhancement_runs(id),
    chunk_index INTEGER NOT NULL,
    codes TEXT NOT NULL,            -- JSON array of product codes in this chunk
    job_name TEXT DEFAULT '',       -- set once submitted
    status TEXT NOT NULL,           -- pending | submitted | applied | failed
    detail TEXT DEFAULT ''
);
```

API: `create_run(force, chunks) -> run_id`, `get_resumable_run()` (latest run with status in running/paused/interrupted), `chunks_for(run_id)`, `mark_chunk(chunk_id, status, job_name='', detail='')`, `update_run(run_id, status=..., processed=...)`. Chunk codes are stored explicitly so resume is exact regardless of `aiProcessed` flags or force mode.

### Resume semantics

On `Continue`:
1. Load products **from ProductDB** (source of truth — no file re-upload, no feeds/merge).
2. For each chunk of the run: `applied` → skip; `submitted` → resume its job via `_monitor_and_apply` (job kept running in the cloud); `pending`/`failed` → (re)submit.
3. Run completes when all chunks are `applied` (chunks that fail twice stay `failed`; run finishes as `completed` with a warning listing failed chunk codes — no infinite retry).

Because a run pins its chunk membership at creation, resume never re-selects by `aiProcessed`/force — it continues exactly the original product set.

## Code changes by file

1. **`src/data/database/run_db.py`** (new): `RunDB` as above. Unit tests mirror `tests/test_database.py` style.
2. **`src/ai/batch_orchestrator.py`** (restructure `process`):
   - Selection logic unchanged (force / `aiProcessed != "1"`), then split `needs_processing` into chunks of `chunk_size` **by product code**, create run + chunk rows.
   - New `_process_chunk(df, chunk)` = current `_submit_and_monitor` scoped to one chunk's requests (`_build_category_requests` already takes an index set — reuse per chunk).
   - After each chunk's `parse_batch_results`: call new callback `on_chunk_applied(updated_rows_df)` (pipeline upserts to ProductDB), `mark_chunk(applied)`, `update_run(processed+=n)`.
   - New `resume(df, run_id, ...)` implementing the semantics above.
   - **Cancellation/pause**: accept a `control` object (`threading.Event` pair `pause_requested` / `cancel_requested`), checked every poll iteration and between chunks. Pause → persist state, return partial result with run left `paused`. Cancel → `client.cancel_batch_job(job_name)` for in-flight chunk, run → `cancelled`.
   - **Poll failure ceiling**: after N consecutive poll exceptions (config `poll_failure_limit`, default 20 ≈ 10 min) mark run `interrupted` ("network/API unreachable") and return instead of looping forever. Same for upload/create failures (e.g. quota/billing) — run `interrupted` with the exception text in `detail`.
3. **`src/ai/api_client.py`**: add `cancel_batch_job(name)` (`client.batches.cancel`).
4. **`src/ai/product_enricher.py`**: pass through `control`, `on_chunk_applied`, `resume_run_id`.
5. **`src/pipeline/pipeline.py`**:
   - AI stage passes `on_chunk_applied` = upsert to ProductDB (chunk-level durability).
   - New `run_ai_resume(control, on_progress)`: loads df from ProductDB, calls enricher resume. No feeds/merge/load.
6. **`src/gui/worker.py`**: new lightweight `AIResumeWorker` (QThread pattern like `PipelineWorker`) exposing `pause()`/`cancel()` (sets events) and a structured signal `ai_progress(dict)` — `{run_id, chunk, chunks_total, products_done, products_total, state, message}`. `PipelineWorker` forwards the same events for AI-inside-pipeline runs.
7. **`src/gui/main_window.py`** — AI processing panel:
   - Progress bar (products_done/products_total — real progress, per chunk) + status label ("Beh 3: dávka 5/20, 2 250/9 657 produktov, stav: spracováva sa").
   - Buttons: **Pozastaviť** (pause), **Zrušiť** (cancel, with confirm dialog), **Pokračovať** (continue).
   - On startup and after any run ends: query `get_resumable_run()`; if found, show banner "Prerušené AI spracovanie: X/Y produktov hotových" + enable Pokračovať → starts `AIResumeWorker`. This works across app restarts.
   - Starting a new AI run while a resumable one exists → dialog: Continue old / Discard old (mark cancelled) & start new.
8. **`scripts/pipeline_cli.py`**: `ai --resume` (continue latest resumable run from DB) and `ai --status` (print run/chunk table). Shares all logic; makes phase 1 testable without GUI.
9. **Config** (`config.json` → `ai_enhancement`): `chunk_size: 500`, `poll_failure_limit: 20`. `batch_size` (products per request) unchanged.

## Phasing (each phase shippable + tested)

- **Phase 1 — durable core (no GUI)**: RunDB + chunked orchestrator + per-chunk ProductDB upsert + resume + failure ceilings + CLI `--resume`/`--status`. Tests: RunDB round-trips; orchestrator with mocked GeminiClient — happy path (2 chunks), kill-after-chunk-1-resume-completes-only-chunk-2, poll-failure→interrupted→resume, failed-chunk-retry-once. *This phase alone delivers the end-game via CLI.*
- **Phase 2 — GUI**: AIResumeWorker, panel, buttons, startup resume banner, pipeline-run integration.
- **Phase 3 — polish**: cancel_batch_job API, discard-old-run dialog, failed-chunk report in success dialog, update `runbook_full_reenhancement.md` (the `--limit` slicing workaround becomes obsolete — resume replaces it).

## Deliberate simplifications (ponytail)

- Sequential chunks, one in-flight job max — parallel chunk jobs only if throughput proves too slow (Batch API is async anyway; parallelism adds little).
- One resumable run at a time (`get_resumable_run` returns latest) — multi-run bookkeeping when a real need appears.
- Pause leaves the in-flight cloud job running (it's prepaid work); resume harvests it. No job suspension.
- No ETA estimation; elapsed time + counts suffice.

## Estimated diff

~350–450 new lines (RunDB ~90, orchestrator restructure ~120, worker ~60, GUI panel ~80, CLI ~30, api_client ~10) + ~150 test lines. No new dependencies.
