# 2026-07-05: Layered Architecture Refactor — Audit & Fixes

## Context
After the big layered-architecture refactor (src/pipeline, src/data, src/domain, src/ai, src/scrapers, src/gui, src/config), a full audit was run: completeness, structure, functionality.

## Regressions Found & Fixed
1. **Interactive price mapping silently dead** (4 compounding bugs):
   - `enable_price_mapping` hardcoded `False` in MainWindow → now bound to the Mebella checkbox.
   - Worker signal signature mismatch (`pyqtSignal(list)` vs 2-arg handler) → `pyqtSignal(dict, object)`.
   - Worker never blocked for the dialog result → restored `QEventLoop` block + `set_price_mapping_result`.
   - `PricingService._save` wrote a plain dict, which would corrupt `table_bases_prices.json` and drop dimension data → rewritten to records format `[{code, dimension, price}]` with legacy dict migration on load. Dimension feeds PriceMappingDialog fuzzy suggestions.
   - Price mapping now runs **pre-merge** on the Mebella feed (`Pipeline._map_prices`).
2. **pairCode never assigned** to scraped Mebella products (scraper hardcodes `""`) → `ScrapingOrchestrator` applies `get_pair_code`; AI variant grouping and variantVisibility depend on it.
3. **Error dialog crash**: handler unpacked `error(str)` as a tuple → fixed to single-arg `show_error_message`.
4. **Broken scripts**: `scraping_cli.py` imported deleted `src.services.scraper` → rewritten against `TopchladenieScraper`; `categories.py`/`cleaning.py` now import `load_config` from `src.config.config_loader`.

## Improvements
- `ProductMerger.merge` (145 lines, cyclomatic 33, nesting 9) split into `_merge_feed_products`, `_keep_main_products`, `_remove_discontinued`, `_update_from_feed`, `_normalize_codes`, `_count_images`. Behavior-identical (21 existing merger tests as safety net).
- Deleted dead `BatchOrchestrator.resume_active_job` (resume lives inside `process()`).
- New tests: `test_pricing_service.py` (5), `test_database.py` (11, ProductDB + BatchJobDB). Suite: 196 passing.
- Nine dead pre-refactor src directories deleted; CLAUDE.md and memory bank updated; `.gitignore` extended (`src/ai/tmp/`, `.tokensave/`, `graphify-out/`).

## Verification
`pytest -q` → 196 passed. tokensave graph: 0 circular deps, 0 duplicated bodies.

## Deferred
- pyright stays at `typeCheckingMode: "off"` (switching to "basic" needs typing cleanup first).
- Manual end-to-end run with production feeds still pending.
