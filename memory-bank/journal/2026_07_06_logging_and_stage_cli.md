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

## Verification
Offline smoke chain on fixtures: `merge` (created=1 updated=1 kept=1 removed=0 → 3 rows) → `categories` → `transform` (329 cols); `logs/gastropro.log` written with timestamped entries. Full suite: 199 passed.
