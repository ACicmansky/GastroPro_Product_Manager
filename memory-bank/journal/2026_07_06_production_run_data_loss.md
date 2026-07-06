# 2026-07-06: First Production Run — 9.6k → 1.9k Product Loss

## Context
First real pipeline run after the layered refactor (input: `2026_04_08_GastroPro.xlsx`, 9,642 products, preserve-edits checked) produced only 1,935 products. Diagnosed without logs, purely from on-disk forensics: DB `last_updated` grouping showed exactly 1,300 `core` + 635 `forgastro` rows touched that run, matching the input file's `source` column distribution.

## Root Causes
1. **`ProductMerger._remove_discontinued`** (preserve-edits mode) removed every product whose `source` wasn't `core` and whose code wasn't in *this run's* feed data — without checking whether that source was fetched at all. That night both Gastromarket feeds failed to download (same host) and scraping was off, so 7,709 products (gastromarket_stalgast 4,441 + gastromarket 2,454 + web_scraping 814) were deleted as "discontinued".
2. **`OutputTransformer.transform_category`** still read the legacy Slovak column `Hlavna kategória`; the internal model uses `defaultCategory`, so every export since the rename wiped `defaultCategory` and `categoryText` to "" (verified: April and July exports have 100% empty categories). Found by the user's other assistant; two of its other three claims were refuted by forensics (main products were NOT dropped for a missing `code` column; the GUI category filter reads the correct column — it was empty input data).
3. **Feed fetch failures were silent**: `XMLParserFactory.fetch_and_parse` logs and returns an empty DataFrame; the pipeline just skipped it.
4. **GUI feed checkboxes were dead**: pipeline fetched all configured `xml_feeds` regardless.

## Fixes
- `merger.py::_remove_discontinued`: only products whose source is in the fetched `feed_dfs` keys are removable; legacy `source="web_scraping"` (predates per-scraper names `mebella`/`topchladenie`) is removable only when both scrapers ran. New `SCRAPER_SOURCES` class constant.
- `output_transformer.py::transform_category`: reads `defaultCategory` instead of `Hlavna kategória`.
- `pipeline.py`: empty/failed feed → warning into `PipelineResult.warnings` (new field) + progress message; feeds filtered by new `PipelineOptions.enabled_feeds` (None = all).
- `main_window.py`: passes `enabled_feeds` from the three feed checkboxes; success dialog shows warnings with a warning icon.
- Tests: 3 new in `test_merger.py::TestRemoveDiscontinued` (unfetched source survives / fetched-but-missing removed / legacy web_scraping both-scrapers rule); `test_output_transformer.py` category tests switched to `defaultCategory` input.

## Verification
`pytest -q` → 199 passed. Live Gastromarket fetch re-tested OK (4,180 products) — the failure was transient/host-side.

## Data Recovery Notes
- No data was lost: the run only writes upserts (never deletes from DB); input XLSX untouched; pre-run backup `products_backup_20260705_235338.db` exists.
- Categories: current DB has `defaultCategory` in `product_data` for 7,721 of 9,654 products, but **0 of the 1,300 core products**. Full category data (9,651 products, incl. core) lives in `data/backups/products_20260322_201504.db` (old 521-column schema) — usable for a one-off backfill if needed.

## Follow-up (same day)
- User reported the category selector still hidden + red underlines in `widgets.py`. Underlines were phantom: pyright (basic, per local gitignored `pyrightconfig.json`) reports 0 issues in `widgets.py` — the IDE was analyzing with an interpreter lacking PyQt5/rapidfuzz/stubs. Fixed by pinning `python.defaultInterpreterPath` (MS Store Python 3.13) in `.vscode/settings.json`.
- Selector was hidden because the input file's categories were empty (transformer wipe). **Backfill executed**: `2026_04_08_GastroPro_repaired.xlsx` written to Downloads — 9,641/9,642 rows filled from the March backup; `CategoryFilter.extract_categories` on it yields 199 categories. Next pipeline run with this file also heals the DB via upsert.
- `src` has 69 real pyright-basic errors (widgets.py: 0; main_window.py: 26, mostly `self.layout`/`self.thread` shadowing QObject methods + Optional item() access) — pre-existing, still deferred.

## Deferred
- Off-by-one: merged 1,935 vs. user-reported 1,934 output rows — not chased.
- GUI `handle_statistics` reads stat keys the worker never emits (stats panel partially dead) — pre-existing, untouched.
