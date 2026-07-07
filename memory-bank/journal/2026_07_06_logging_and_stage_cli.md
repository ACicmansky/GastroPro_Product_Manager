# 2026-07-06: Persistent Logging + Stage CLI (audit tooling)

## Why
The production-run incident (see `2026_07_06_production_run_data_loss.md`) had to be diagnosed with zero logs: `main.py` never configured a logging handler, so every `logger.info` in the pipeline vanished. Also no way to run/inspect a single pipeline stage in isolation.

## What
- **`src/logging_setup.py`** — `setup_logging()`: console + `RotatingFileHandler` → `logs/gastropro.log` (UTF-8, 5 MB × 5 backups), idempotent (no-op if root already has handlers). Called from `main.py` and the new CLI. `logs/` + `out/` gitignored.
- **Pipeline audit lines** (`pipeline.py`): per-feed product counts after fetch; merge stats line (`created/updated/kept/removed -> N products`) after merge.
- **`scripts/pipeline_cli.py`** — argparse subcommands wrapping existing components, files in → file out (intermediates = audit artifacts):
  - `feeds [--only name…] [--out-dir]` — one xlsx per fetched feed
  - `merge main.xlsx --feeds f1.xlsx… [-o] [--preserve-edits]` — feed name = filename stem
  - `categories in.xlsx [-o]` — non-interactive categories.json mapping, logs each unmapped category
  - `transform in.xlsx [-o]` — 138-column output format
  - `run main.xlsx [-o] [--preserve-edits] [--only feed…]` — full headless pipeline (no scraping/AI)

## Skipped (deliberately)
- REST/FastAPI server — single-user desktop app; CLI gives per-stage control with zero server code. Add when a second process/machine needs to call the pipeline.
- Per-stage DataFrame snapshots in GUI runs — the log lines (feed counts, merge stats, warnings) cover the forensics that mattered in the incident; full snapshots available on demand via the CLI.

## Follow-up: fixtures + e2e test (same day)
Goal: user shows a log, Claude diagnoses and re-runs individual stages. Added:
- `tests/fixtures/` — anonymized `main.xlsx` (8 rows: core w/ + w/o category, feed rows incl. one discontinued, legacy `web_scraping`, `pairCode` variant pair) + `gastromarket.xml` (rss + `g:` namespace) and `forgastro.xml` mirroring real feed structures.
- `tests/test_integration_pipeline.py` (`@pytest.mark.integration`, 3 tests) — parse → merge(preserve_edits) → transform chain; guards both 2026-07-06 production bugs (unfetched-source purge, category wipe).
- `Pipeline.run` logs its `PipelineOptions` at start, so the log alone shows how a run was configured.
Suite: 202 passed.

## First real payoff (same evening)
User ran the GUI pipeline and showed the log. Diagnosed from log alone:
- `gastromarket_stalgast` got a transient HTTP 502 (gateway failed in <1 s; feed is generated on demand server-side, ~14 s + 7.5 MB when it works). Fix: `fetch_and_parse` now retries 3× with 5 s/10 s backoff (+ unit test with mocked urlopen).
- "Category widget not visible" — log line `Extracted 0 unique categories` + `main_file_path=...2026_04_08_GastroPro.xlsx`: user loaded the **original** file, not `2026_04_08_GastroPro_repaired.xlsx`. Not a bug; wrong input file. That run also upserted category-less core products into the DB again — heals by re-running with the repaired file.

## AI stage added to CLI (same evening)
User asked how AI enhancement state is tracked and how to test it cheaply.
- Tracking: `aiProcessed`/`aiProcessedDate` set by `ResultParser` on match, persisted in DB (dedicated columns) and forwarded through the output file (`internal_tracking` in OutputTransformer; `"Spracovane AI"` maps back on load). Merger `PRESERVED_FIELDS` keeps AI text safe from feed overwrites. DB state: 5,691 enhanced / 3,967 pending.
- Only-unprocessed is already the default (`df[aiProcessed != "1"]`); `force_reprocess` overrides.
- New: `pipeline_cli.py ai <in.xlsx> [--dry-run] [--limit N] [--force] [-o out.xlsx]` — micro-batch testing against the real Gemini Batch API; no `batch_job_db` passed, so test runs never resume/persist jobs. Test: `test_cli_ai_dry_run_selects_only_unprocessed`.
- Fixed dead `pytest -m ai_enhancement` marker (CLAUDE.md documented it; 0 tests collected) via `pytestmark`.
- **Live micro-batch test found a real bug**: `_build_category_requests` used `r.get("newCategory", r.get("defaultCategory", ""))` — falls back only when the *column is missing*, not when the value is empty. DB exports carry an empty `newCategory` column → all products skipped ("no category"). Fixed with `BatchOrchestrator._category_of` (first non-empty of newCategory/defaultCategory, NaN-safe) + unit test. Retest reached JSONL build + upload; blocked only by Google billing (`429 RESOURCE_EXHAUSTED: prepayment credits depleted`) — code path verified to the paid boundary. After top-up, live micro-batch succeeded: 3/3 processed in ~2 min, correct Slovak copy + category filteringProperty params + aiProcessed flags in `out/ai_test.xlsx`. AI enhancement confirmed working end-to-end.
- Fixture row `GM001` (from `tests/conftest.py` sample XML, upserted 2026-04-08) leaked into `data/products.db`. Root cause: the `config` test fixture returned the real `config.json` without a `db_path` override, so `Pipeline(config)` in tests pointed at the production DB. Fixed: fixture now redirects `db_path` to `tmp_path`; GM001 deleted (backup taken first, 9,657 products remain); stale `data/test_products.db` removed. Full suite (205) leaves `data/` untouched.
- Caveat noted: `Pipeline.run` loads `db.get_all()` but uses it only when no main file is given — a fresh e-shop export without the `Spracovane AI` column would look 100% unprocessed; DB flags are not merged into a loaded main file.

## Deterministic filtering parameters (same evening)
E-shop filters need stable values. Convention chosen: **units in headers, bare numbers in values** (all lengths mm, weights kg, power W, voltage V, temp °C).
- `categories_with_parameters.json`: 771 renames (`Šírka` → `Šírka (mm)` etc.); counts/categoricals/composites untouched.
- `ResultParser`: whitelist of allowed param keys (union of all `filtre`; unit-less echoes canonicalized back, ad-hoc keys dropped) + `normalize_param_value` (bare numbers for scalar-unit headers, canonical Áno/Nie; "rozsah" params keep range text).
- Prompt: values must be bare numbers, units are in the key name; exact key names required. `temperature` 0.1 → 0 in config.json.
- Live retest: 3/3, zero ad-hoc keys, `Príkon (W): 550`, `Šírka (mm): 800`, `So zásuvkou (Áno/Nie): Nie`. Suite: 206 passed.
- Known ceiling: categorical values can still drift ("Nerez" vs "Nerezová oceľ") — escalation path is enum-constrained response schema per category.
- **Open**: 5,691 already-enhanced products in DB carry old-style keys (`filteringProperty:Šírka`, values with units) — need key-rename+normalize migration or forced re-enhancement before e-shop import, else filters fragment old vs new.

## Nine AI-output enhancements implemented (2026-07-07)
All nine brainstormed options landed in one pass ("implement all of them 1 to 9"):
1. **Grounded second pass** — `BatchOrchestrator.process_missing_params` + `create_params_only_prompt`: per-product `chybajuce_parametre` re-asked with `"tools": [{"google_search": {}}]` at batch-request level; no `responseMimeType` (conflicts with grounding), parser strips fences. Params-only responses can't clobber text fields (parser writes fields only `if field in enhanced`). `ProductEnricher.fill_missing_params`; CLI `ai --fill-missing`.
2. **Feed structured specs** — config.json forgastro mapping += `product_width/length/height/lwh_uom` → `feedWidth/feedDepth/feedHeight/feedDimUnit`; new `src/domain/products/feed_specs.py` `apply_feed_specs` (CM/M→mm, weight→kg, forgastro-only, zeros/garbage skipped). Runs AFTER AI in `Pipeline.run` and `cmd_ai` so verified feed numbers win. Gastromarket feeds have no structured dims (audited).
3. **Fuzzy-match audit** — `ResultParser.match_audit` records strategy/ai_code/matched_code on every non-exact match + WARNING log; CLI exports `<out>_match_review.csv`.
4. **Category classification** — CLI `classify in.xlsx`: products with empty/"Neznáma" category get AI-suggested category from the 211-key tree, written to `suggestedCategory` only (never defaultCategory — human review).
5. **Duplicate-content mitigation** — main-pass payload includes `existingParameters` (filled filteringProperty values); prompt requires unique copy per product using them.
6. **Format guarantees** — `ResultParser.enforce_format`: seoTitle ≤60, metaDescription ≤155 + `GastroPro.sk | ` prefix, word-boundary truncation; applied at the single write choke point.
7. **Plausibility validation** — `src/ai/validation.py` `find_implausible`: Napätie ∈ {12,24,230,400,230/400}, dims 50–6000 mm, weight 0.1–2000 kg, Príkon 5–100000 W; CLI exports `<out>_param_review.csv` (motivating case: ForGastro typo w=3800).
8. **Response schema** — `build_response_schema` per category: enum-locked Áno/Nie params, required text fields; attached as `responseSchema` in main-pass generationConfig.
9. **Tiered models** — `create_batch_job(model=...)` override; `--fill-model` runs the second pass on a stronger model.
Suite: 212 passed. Live micro-tests (both JOB_STATE_SUCCEEDED in ~90 s):
- **Main pass w/ responseSchema**: 2/2 processed — Gemini accepts property keys with diacritics/parens/spaces; format guarantees held (seoTitle 51/50 chars, metaDescription prefixed + ≤155).
- **Grounded fill pass**: S721128 went 3→6 params with web-sourced dims (420×210×338, Napätie 230); `Kapacita (GN): 2x GN1/1` preserved. Two live-found fixes: xlsx round-trip floats ("230.0") false-flagged by the voltage enum → strip `.0` in `find_implausible`; one batch response had a candidate without `content.parts` → parser now warns (with finishReason) instead of erroring the line. Re-verified: 0 implausible on live output, suite 212.

## Verification
Offline smoke chain on fixtures: `merge` (created=1 updated=1 kept=1 removed=0 → 3 rows) → `categories` → `transform` (329 cols); `logs/gastropro.log` written with timestamped entries. Full suite: 199 passed.
