# GastroPro Product Manager - Active Context

*Last updated: 2026-07-07 (UI/UX modernization)*

## Current State
The **layered architecture refactor is complete and audited**. The codebase moved from the old flat `src` layout (core/services/utils/parsers/mergers/...) to a clean layered structure: `src/pipeline` (orchestration), `src/data` (I/O), `src/domain` (business logic), `src/ai` (Gemini), `src/scrapers`, `src/gui`, `src/config`. Entry point is `main.py`. All 202 tests pass. Zero circular dependencies.

## Recent Changes (2026-07-06 — first production run failures fixed)
First real run after the refactor produced 1,935 of 9,642 products. Root causes found via DB forensics and fixed (see `journal/2026_07_06_production_run_data_loss.md`):
- `_remove_discontinued` (preserve-edits) deleted every product whose source feed wasn't fetched this run — now only products of feeds *actually fetched non-empty* can be discontinued; legacy `source="web_scraping"` rows require both scrapers to have run.
- `OutputTransformer.transform_category` still read legacy `Hlavna kategória` and wiped `defaultCategory`/`categoryText` to "" on every export — now reads `defaultCategory`.
- Feed download failures were silently swallowed — now collected into `PipelineResult.warnings` and shown in the GUI success dialog.
- GastroMarket/ForGastro checkboxes were ignored (pipeline fetched all feeds) — wired via `PipelineOptions.enabled_feeds` (None = all).
- Category recovery **done**: `2026_04_08_GastroPro_repaired.xlsx` (Downloads) backfilled 9,641/9,642 categories from `data/backups/products_20260322_201504.db`; use it as the next pipeline input (DB heals via upsert). IDE red underlines in `widgets.py` were phantom (wrong interpreter) — pinned `python.defaultInterpreterPath` in `.vscode/settings.json`; 69 real pyright-basic errors remain in `src` (deferred).

## Recent Changes (2026-07-06 — audit tooling)
- Persistent logging: `src/logging_setup.py` (rotating `logs/gastropro.log`), wired into `main.py` — previously the GUI configured no handler and all pipeline logs vanished. Pipeline now logs per-feed counts + merge stats.
- `scripts/pipeline_cli.py`: run any stage independently (`feeds` / `merge` / `categories` / `transform` / `ai` / `run`), files in → file out. REST API deliberately skipped (see `journal/2026_07_06_logging_and_stage_cli.md`).
- `ai` stage supports `--dry-run` (pending counts, no API), `--limit N` (micro-batch test), `--force`. AI state audit (2026-07-06): DB has 5,691 enhanced / 3,967 pending. `pytest -m ai_enhancement` marker was dead (0 collected) — restored via `pytestmark` in `test_ai_enhancer.py`.
- `tests/fixtures/` (sample main.xlsx + feed XMLs) + `tests/test_integration_pipeline.py`: offline e2e chain guarding the 2026-07-06 production bugs. `Pipeline.run` logs its options. Suite: 202 tests.

## Recent Changes (2026-07-07 — deterministic filters + 9 AI-output enhancements)
- **Deterministic filtering** (e-shop filters need stable values): units in headers (`Šírka (mm)`), bare numbers in values. 771 renames in `categories_with_parameters.json`; `ResultParser` whitelist + canonicalization + `normalize_param_value`; temperature 0. Verified live. **Open**: 0 of the 5,691 already-enhanced DB products have any filteringProperty values — full re-enhancement is queued; self-serve instructions in `runbook_full_reenhancement.md` (reset `aiProcessed` + chained `--limit` slices, not `--force`).
- **Model A/B** (`ai --model`): gemini-3.1-flash-lite fills fewer params and made factual errors; **staying on gemini-2.5-flash-lite**.
- **Nine AI-output enhancements** (details in `journal/2026_07_06_logging_and_stage_cli.md`): grounded `--fill-missing` second pass (+`--fill-model` for tiered escalation), ForGastro structured dims/weight → filter columns via `src/domain/products/feed_specs.py` (feed wins, runs after AI), fuzzy-match audit CSV, `classify` CLI (AI category suggestions → `suggestedCategory` review column), `existingParameters` in prompts for unique copy, seoTitle/metaDescription length+branding enforcement in code, plausibility validation (`src/ai/validation.py` → review CSV), enum-locked responseSchema on the main pass, per-job model override. Suite: 212 passed.

## Recent Changes (2026-07-07 — ponytail audit applied, ~-1,050 lines)
All 11 findings of the over-engineering audit applied (see `journal/2026_07_07_ponytail_audit.md`):
- Deleted 11 one-shot/debug scripts in `scripts/` (kept: `pipeline_cli.py`, `scraping_cli.py`, `categories.py`, `cleaning.py`).
- `DataLoaderFactory` + `XLSXLoader` class collapsed into `load_xlsx()` function (`src/data/loaders/xlsx_loader.py`); all call sites updated.
- requirements.txt fixed: `google-generativeai` → `google-genai` (code imports `from google import genai` — fresh installs were broken), removed unused `lxml` + `llm_output_parser`, deduped `python-dotenv`.
- Dead code removed: `XMLParserFactory.get_parser`, `BatchJobDB.get_job`, `EnrichmentResult.skipped`.
- Batch JSONL tmp dir moved from `src/ai/tmp/` to gitignored `out/batch_requests` (config override `ai_enhancement.tmp_dir` still honored). Stale JSONL debris in `src/ai/tmp/` awaits manual deletion.
- Suite: 206 passed (2 factory tests removed, `test_xlsx_loader.py` rewritten, `BatchJobDB` tests rewritten against `get_active_job`).

## Recent Changes (2026-07-07 — resumable AI runs, all 3 phases)
Implemented `plan_resumable_ai_runs.md` in full (details in `journal/2026_07_07_resumable_ai_runs.md`):
- **`RunDB`** (`src/data/database/run_db.py`): new SQLite tables `enhancement_runs`/`run_chunks`. A run pins a fixed product-code set at creation, split into ~500-product chunks (`ai_enhancement.chunk_size`), each its own Gemini Batch job — applied + DB-upserted immediately after each chunk succeeds, bounding data loss on interruption to one in-flight chunk.
- **`BatchOrchestrator`** rewritten around a sequential per-chunk loop (`src/ai/batch_orchestrator.py`): resumes `submitted` chunks via their stored `job_name` (no resubmission), replaces the old infinite poll-retry with a `poll_failure_limit` (default 20) that marks the run "interrupted" instead of hanging, and checks a `RunControl` (`src/ai/run_control.py`, pause/cancel `threading.Event`s) between chunks.
- **Resume path**: `ProductEnricher.resume()` / `Pipeline.run_ai_resume()` reload products fresh from `ProductDB` (not from any file) — this is what makes "continue like nothing happened" work across app restarts. CLI: `pipeline_cli.py ai --resume` / `--status`.
- **GUI**: `MainWindow` shows a resume banner on launch if `RunDB.get_resumable_run()` finds one, plus Pause/Cancel buttons during an AI run (`AIResumeWorker`, `src/gui/worker.py`).
- `runbook_full_reenhancement.md` updated: the old `--limit`-slicing interruption workaround is now optional (kept for micro-testing), resuming is automatic/native.
- Suite: 212 passed (206 + `test_run_db.py` + `test_batch_resume.py`, the latter using a fake Gemini client to cover interrupt→resume-without-resubmit, pause, and cancel).

## Recent Changes (2026-07-07 — UI/UX modernization, Level 1 + 2)
GUI modernized in two passes (details in `journal/2026_07_07_ui_modernization.md`):
- **Level 1** (committed by user as 858136d): `src/gui/theme.py` (Fusion + Segoe UI + QPalette + token-substituted QSS applied app-wide, auto light/dark from Windows registry, `set_variant`), `styles/main.qss` rewritten as a $token template (old one was broken — `PUSHButton` typo, unsupported CSS), card group boxes / accent primary buttons / check indicators (`styles/check.svg`) / dialog cards; dead `DropArea` classes deleted.
- **Level 2**: two-pane landscape layout (1080×720) with header + theme toggle (Auto/Light/Dark, QSettings-persisted, live re-apply), pipeline stage tracker (`Pipeline.run(on_stage=...)` → worker `stage` signal → QSS `[stage=...]`), status line under the indeterminate progress bar (its `setFormat` text was never visible), KPI result tiles (old stats panel read keys the worker never emitted — showed zeros), drag&drop XLSX, Ctrl+O/Ctrl+R. `tests/test_gui_window.py` added.
- **Test-pollution fix**: `test_category_mapper_new_format.py` used to WRITE to production `categories.json` each run and depended on its content (broken by user's `update_categories.py` prefix migration) — now isolated to tmp files. Suite: 215 passed, categories.json untouched by tests.

## Earlier Changes (July 2026 — post-refactor audit)
- **Regressions from the refactor found and fixed:**
  - Interactive price mapping was silently disabled (hardcoded `False`, broken signal signature, worker never blocked on the dialog). Restored end-to-end: `Pipeline._map_prices` runs pre-merge on the Mebella feed; worker blocks via `QEventLoop`; `PricingService` now stores records (`[{code, dimension, price}]`) preserving dimension data, with legacy dict migration.
  - `pairCode` was never assigned to scraped Mebella products — restored in `ScrapingOrchestrator` via `get_pair_code` (AI variant grouping and variantVisibility depend on it).
  - Error dialog handler crashed on tuple unpacking — fixed.
  - `scripts/scraping_cli.py`, `scripts/categories.py`, `scripts/cleaning.py` imported deleted modules — rewritten against the new structure.
- **Improvements:** `ProductMerger.merge` (145 lines, deep nesting) split into `_merge_feed_products` / `_keep_main_products` / `_remove_discontinued` / `_update_from_feed`; dead `BatchOrchestrator.resume_active_job` deleted (resume happens inside `process()`); tests added for `PricingService`, `ProductDB`, `BatchJobDB`.
- **Docs:** CLAUDE.md updated to post-refactor architecture; memory bank refreshed and integration slimmed to a project skill.

## Active Decisions
- SQLite document store (`data/products.db`, 6-column schema with JSON `product_data` blob) is the source of truth; `aiProcessed`/`aiProcessedDate` survive client re-uploads.
- AI enhancement uses the asynchronous Gemini **Batch API**, chunked into ~500-product jobs tracked in `RunDB` (`enhancement_runs`/`run_chunks`); a run resumes automatically (GUI banner / CLI `--resume`) from wherever it was interrupted, reloading products from the DB rather than a file.
- Variants (products with `pairCode`) get dimension-free AI prompts; others get the standard prompt.
- Feed products always included in merge; main data filtered by selected categories; image merge prefers the source with more images; `PRESERVED_FIELDS` (AI/manual text) never overwritten by feeds.
- AI enhancement disabled by default in the UI (cost control).
- KISS + TDD: tests required for new non-trivial logic; no unrequested complexity.

## Known Gaps / Next Candidates
- Stale JSONL debris in `src/ai/tmp/` from before the tmp-dir move to `out/batch_requests` — safe to delete manually.
- pyright runs in `typeCheckingMode: "off"` — switching to "basic" would need cleanup of loose typing first (deliberately deferred, not requested).
- Manual end-to-end run with production feeds after the audit fixes is still pending.
