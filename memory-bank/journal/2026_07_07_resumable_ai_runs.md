# Resumable AI runs (all 3 phases of `plan_resumable_ai_runs.md`)

## Problem
The AI enhancement stage submitted an entire re-enhancement run (thousands of products) as ONE Gemini Batch job. Any interruption — quota exhaustion, network drop, app closed — lost the whole in-flight job, and the polling loop retried network errors forever (`while True: ... sleep(30); continue`), so a dead connection just hung silently.

## Design
Runs → chunks → jobs. A "run" pins a fixed product-code set at creation (survives DB/df changes), split into ~500-product chunks (`ai_enhancement.chunk_size`). Each chunk is its own small Batch job, processed sequentially; results are applied and DB-upserted immediately after each chunk succeeds. Interruption now loses at most one in-flight chunk instead of the whole run.

## What changed
- `src/data/database/run_db.py` (new): `RunDB` — `enhancement_runs` + `run_chunks` tables. `create_run`, `get_resumable_run` (active states: running/paused/interrupted), `mark_chunk`, `update_run`.
- `src/ai/run_control.py` (new): `RunControl` — pause/cancel via `threading.Event`, checked between chunks and during polling.
- `src/ai/batch_orchestrator.py`: rewritten around `_run_chunks()` — resumed `submitted` chunks re-attach to their stored `job_name` instead of resubmitting; `_wait_for_job()` replaces the infinite retry with `poll_failure_limit` (default 20 ≈ 10 min) before marking the run "interrupted".
- `src/ai/result_parser.py`: `parse_batch_results` takes `valid_indices` so a chunk only writes results for its own product codes (no cross-chunk collision).
- `src/ai/product_enricher.py`: `resume()` reloads products from `ProductDB` (not a file) and continues the pinned run.
- `src/pipeline/pipeline.py`: `run_ai_resume()`, `get_resumable_ai_run()`; normal `run()` wires `on_chunk_applied=self.db.upsert` for automatic chunk-level durability even without touching pause/cancel.
- `src/gui/worker.py` + `main_window.py`: resume banner on launch, Pause/Cancel buttons during an AI run (`AIResumeWorker`).
- `scripts/pipeline_cli.py`: `ai --resume`, `ai --status`.
- `config.json`: `ai_enhancement.chunk_size` (500), `poll_failure_limit` (20).

## Tests
`tests/test_run_db.py` (RunDB round-trip/state filtering) + `tests/test_batch_resume.py` (orchestrator-level, fake Gemini client): interrupted chunk resumes without resubmitting the cloud job, pause leaves the run resumable, cancel stops it. Full suite: 212 passed.

## Skipped (ponytail)
- Resumed chunks don't persist `uploaded_file_name`, so post-download `delete_file` cleanup is skipped for them — Google auto-expires uploaded files, so no new DB column was added for this.
- `runbook_full_reenhancement.md`'s manual `--limit`-slicing workaround is now optional (kept for micro-testing) since resume is native.
