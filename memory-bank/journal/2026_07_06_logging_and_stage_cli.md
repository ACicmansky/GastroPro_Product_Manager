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

## Verification
Offline smoke chain on fixtures: `merge` (created=1 updated=1 kept=1 removed=0 → 3 rows) → `categories` → `transform` (329 cols); `logs/gastropro.log` written with timestamped entries. Full suite: 199 passed.
