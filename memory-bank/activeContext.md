# GastroPro Product Manager - Active Context

*Last updated: 2026-09-15 (Input pruning optimization & Gemini 3.8 Flash upgrade)*

## Current State
The project has achieved **State-Of-The-Art (SOTA)** status with a complete developer experience, testing, CI/CD, and packaging toolchain:
- **Fast Tooling**: `uv` package manager, PEP 621 `pyproject.toml`, deterministic `uv.lock`, isolated `.venv`, and `poethepoet` task runner (`uv run poe ...`).
- **Code Quality**: `ruff` linter + formatter with format-on-save in VS Code, and `.pre-commit-config.yaml` git hooks.
- **Testing & QA**: 240 tests passing in parallel with `pytest-xdist` (`test:fast`), full branch coverage reporting with `pytest-cov` (`test:cov`).
- **Type Safety**: `PyQt5-stubs` installed and `pyrightconfig.json` calibrated with `.venv` and path exclusions.
- **CI/CD**: GitHub Actions workflow (`.github/workflows/ci.yml`) leveraging `astral-sh/setup-uv@v5` caching on `windows-latest`.
- **Packaging**: PyInstaller spec (`gastropro.spec`) and automated build script (`scripts/build_exe.py` / `uv run poe build`) with frozen asset path resolution in `src/gui/theme.py`.
- **Crash Resilience**: Global `sys.excepthook` handler (`src/gui/crash_handler.py`) providing logging to `logs/gastropro.log` and user-facing recovery dialogs.
## Recent Changes (2026-09-16 — Thinking Budget Calibration & Chunk Size Reduction)
- Lowered `chunk_size` from 500 to 100 in `config.json` to prevent long Google Batch scheduling delays and worker node preemption timeouts (`code: 13`). Chunks now finish every ~25-35 minutes instead of 5+ hours.
- Calibrated `thinking_budget: 3072` tokens in `config.json` and updated `src/ai/batch_orchestrator.py` with `_get_thinking_config()` to pass `{"thinkingBudget": 3072}` to Gemini API generationConfig.
- Bounded reasoning prevents runaway internal reasoning tokens while preserving deep technical extraction and FAQ quality.
- Verified mutual exclusivity handling for Gemini API (`thinkingBudget` vs `thinkingLevel`) with automated test. Suite: **245 tests passing** via `uv run poe check`.

## Recent Changes (2026-09-16 — Autonomous Categorization Subagent)
- Implemented and executed autonomous classification subagent (`scripts/auto_categorize.py`) using `gemini-3.8-flash` across 4 concurrent worker threads.
- Classified all 3,319 previously uncategorized products against the 211 authoritative categories from `categories_with_parameters.json`.
- Achieved >99.9% exact taxonomy match in 190.1 seconds (~3.1 minutes).
- Automatically updated `data/products.db` and active Excel file `C:/Users/Andrej/Downloads/2026_09_16_GastroPro.xlsx` (with `.bak` safety backup).
- **Result: 9,712 / 9,712 products (100.0%) in database are now fully categorized.**
- Detailed report generated in `out/categorization_report.json`.

## Recent Changes (2026-09-16 — BatchJobDB Schema Migration & Resumable Run Recovery)
- Added `updated_at` column to `batch_jobs` in `data/products.db` to fix `OperationalError: no such column: updated_at`.
- Updated `BatchJobDB._init_table()` in `src/data/database/batch_job_db.py` to inspect `PRAGMA table_info` and automatically migrate missing columns (`updated_at`, `details`).
- Updated `MainWindow._check_resumable_ai_run` and `PipelineWorker.run` to ensure interrupted runs cleanly present the resume banner.
- Verified test suite: **244 tests passing** via `uv run poe check`.

## Recent Changes (2026-09-15 — Authoritative Live Categories & Ponytail Cleanup)
- Enforced live website categories (from uploaded input file and DB `source="core"` products) as permanently authoritative: never remapped and never prompted.
- Deleted obsolete, unreferenced `unique_categories.txt` file.
- `CategoryService`: `file_categories` are recognized as valid targets in `is_target_category` and `get_unique_target_categories`, and preserved as-is in `map_or_ask`.
- `Pipeline`: Automatically registers unique categories from both input file (`main_df`) and core DB products (`db_df`).
- `MainWindow` & `CategoryMappingDialog`: Removed redundant category forcing checkboxes and buttons; live categories are preserved by default.
- Suite: **244 tests passing** via `uv run poe check`.

## Recent Changes (2026-09-15 — Single-Product Prompt Optimization via Prompt Engineering)
- Redesigned `create_system_prompt()` in `src/ai/prompts.py` using core prompt engineering patterns (Instruction Hierarchy, singular framing, and redundancy removal).
- Converted prompt from legacy multi-product batch phrasing to laser-focused single-product generation, eliminating confusion from cross-product references.
- Removed duplicate 15-line validation checklist since constraints are enforced by `responseSchema`.
- Suite: **241 tests passing** via `uv run poe check`.

## Recent Changes (2026-09-15 — Batch Size 1 & Product Consistency Optimization)
- Calibrated `config.json` to `"batch_size": 1`: each product is an independent request in the Gemini Batch API JSONL, eliminating anti-repetition bias, attention decay, and token truncation risks while leveraging full Google cloud parallelism.
- Updated `src/ai/prompts.py` to instruct model on strict **consistency, standardized terminology, and professional B2B structure** across product lines instead of forced variation.
- Added deterministic sorting by `pairCode` and `code` in `BatchOrchestrator._build_category_requests`.
- Suite: **241 tests passing** via `uv run poe check`.

## Recent Changes (2026-09-15 — FAQ Generation in AI Prompts & High Thinking)
- Added explicit instructions in `create_system_prompt()` (`src/ai/prompts.py`) to generate 4–5 practical B2B FAQs appended to `description` (Dlhý popis) using semantic HTML (`<h3>Často kladené otázky (FAQ)</h3>`, `<p><strong>Otázka: ...?</strong><br>Odpoveď: ...</p>`).
- Adjusted `description` target word count to 300–800 words to give the FAQ block ample room.
- Extended negative dimension constraints in `create_system_prompt_no_dimensions()` to cover the FAQ section for product variants.
- Added automated test in `tests/test_ai_enhancer.py`. Suite: **241 tests passing** via `uv run poe check`.

## Recent Changes (2026-09-15 — Input Pruning Optimization & Token Savings)
- Implemented intelligent input pruning utility (`src/ai/pruning.py`, `prune_text`): strips bloated HTML tags, unescapes entities, preserves semantic linebreaks, and truncates text on word boundaries.
- Integrated input pruning into `BatchOrchestrator._build_category_requests` and `_build_missing_param_requests`, capping incoming `description` to 1,200 chars and `shortDescription` to 500 chars (`max_desc_chars` / `max_short_desc_chars` in `config.json`).
- Cuts catalog raw description characters from 14.3M down to 8.9M (a **37.8% reduction**, saving ~1.8M – 2.2M input tokens).
- Suite: 240 tests passing (`test:fast` in ~9s).

## Recent Changes (2026-09-15 — Upgrade to Gemini 3.8 Flash & Thinking Level Configuration)
- Upgraded default AI model from `gemini-2.5-flash-lite` to Google's reasoning model `gemini-3.8-flash` in `config.json` and `GeminiClient`.
- Integrated `thinking_level` setting (`"high"` configured for maximum copywriting quality) into `config.json`, `BatchOrchestrator`, and `SettingsDialog` GUI.
- `BatchOrchestrator` serializes `"thinkingConfig": {"thinkingLevel": "HIGH"}` into batch JSONL `generationConfig` payloads.

## Recent Changes (2026-09-14 — Force category names from input file & "Apply to All" checkbox)
- Implemented option to force category names from the input file when mapping categories (see `journal/2026_09_14_force_input_file_categories.md`).
- `CategoryService`: Added `file_categories` tracking, `force_file_categories` flag, and in-memory `_session_mappings` cache to eliminate repetitive prompts for identical unmapped categories.
- `CategoryMappingDialog`: Added "Aplikovať na všetky kategórie zo súboru" checkbox and "📁 Vnútiť názov zo súboru" button with input file origin badge.
- `MainWindow` & `PipelineWorker`: Added "Vnútiť kategórie zo vstupného súboru" checkbox in processing options, wired to `PipelineOptions.force_file_categories`, dynamically activatable from mapping dialog.
- Suite: 231 tests passing (`test:fast` in ~8s).

## Recent Changes (2026-09-12 — SOTA engineering enhancements)
- Implemented Pre-commit hooks (`.pre-commit-config.yaml`), VS Code workspace configuration, and `poethepoet` tasks (`test:fast`, `test:cov`, `lint`, `format`, `check`, `build`, `run`).
- Integrated `pytest-xdist` and `pytest-cov` for multi-core testing and branch coverage reporting.
- Added `PyQt5-stubs` and updated `pyrightconfig.json`.
- Created GitHub Actions CI matrix with `astral-sh/setup-uv@v5`.
- Built standalone desktop distribution spec (`gastropro.spec`) and `scripts/build_exe.py`.
- Implemented global GUI exception hook (`src/gui/crash_handler.py`) with 4 dedicated unit tests (225 tests total).


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

## Recent Changes (2026-07-07 — UI/UX modernization, Levels 1–3)
GUI modernized in two passes (details in `journal/2026_07_07_ui_modernization.md`):
- **Level 1** (committed by user as 858136d): `src/gui/theme.py` (Fusion + Segoe UI + QPalette + token-substituted QSS applied app-wide, auto light/dark from Windows registry, `set_variant`), `styles/main.qss` rewritten as a $token template (old one was broken — `PUSHButton` typo, unsupported CSS), card group boxes / accent primary buttons / check indicators (`styles/check.svg`) / dialog cards; dead `DropArea` classes deleted.
- **Level 2**: two-pane landscape layout (1080×720) with header + theme toggle (Auto/Light/Dark, QSettings-persisted, live re-apply), pipeline stage tracker (`Pipeline.run(on_stage=...)` → worker `stage` signal → QSS `[stage=...]`), status line under the indeterminate progress bar (its `setFormat` text was never visible), KPI result tiles (old stats panel read keys the worker never emitted — showed zeros), drag&drop XLSX, Ctrl+O/Ctrl+R. `tests/test_gui_window.py` added.
- **Test-pollution fix**: `test_category_mapper_new_format.py` used to WRITE to production `categories.json` each run and depended on its content (broken by user's `update_categories.py` prefix migration) — now isolated to tmp files. categories.json untouched by tests.
- **Level 3 (SOTA interaction)**: toast notifications (`src/gui/toast.py`, replaced all runtime QMessageBoxes), export completion flow (open file/folder actions in results card, warnings inline + logged), determinate AI progress (`on_ai_progress(current,total,msg)` through Pipeline→worker→GUI, N/M produktov on the bar), collapsible timestamped activity log, session persistence via QSettings (geometry, source checkboxes — AI ones deliberately not persisted, last export dir), busy CTA. Suite: 218 passed.

## Recent Changes (2026-07-08 — mapping-dialog UX, settings UI, category-scoped AI)
- **CategoryMappingDialog UX**: selectable label + copy button, prefilled input, "⛔ Zrušiť celý proces" (→ `PipelineCancelled` abort path); `is_target_category` now accepts the "Tovary a kategórie > " prefix so final-format categories skip the dialog (journal `2026_07_07_ui_modernization.md` follow-up).
- **Settings UI + scoped AI runs** (journal `2026_07_08_settings_and_category_scoped_ai.md`): `src/gui/settings_dialog.py` — ⚙️ header button opens tabs for API key (per-user `.env` via `config_loader.save_api_key`, test button), AI values + feed URLs (config.json), and category AI parameters (searchable editor over `categories_with_parameters.json`; removing a param clears its `filteringProperty:` values in DB; "🤖 Spustiť AI pre kategóriu" triggers a scoped re-run with cost confirm). Engine: `BatchOrchestrator.process(only_categories=...)` → `Pipeline.run_ai_for_categories` → `AIResumeWorker(categories=...)`. **`_category_of` now normalizes the missing "Tovary a kategórie > " prefix on stale pre-migration DB rows** — this also fixed param lookup silently missing for all 9,692 DB products. First-run toast when no API key. Suite: 221 passed.

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
