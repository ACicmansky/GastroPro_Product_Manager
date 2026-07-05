# GastroPro Product Manager - Active Context

*Last updated: 2026-07-05*

## Current State
The **layered architecture refactor is complete and audited**. The codebase moved from the old flat `src` layout (core/services/utils/parsers/mergers/...) to a clean layered structure: `src/pipeline` (orchestration), `src/data` (I/O), `src/domain` (business logic), `src/ai` (Gemini), `src/scrapers`, `src/gui`, `src/config`. Entry point is `main.py`. All 196 tests pass. Zero circular dependencies.

## Recent Changes (July 2026 — post-refactor audit)
- **Regressions from the refactor found and fixed:**
  - Interactive price mapping was silently disabled (hardcoded `False`, broken signal signature, worker never blocked on the dialog). Restored end-to-end: `Pipeline._map_prices` runs pre-merge on the Mebella feed; worker blocks via `QEventLoop`; `PricingService` now stores records (`[{code, dimension, price}]`) preserving dimension data, with legacy dict migration.
  - `pairCode` was never assigned to scraped Mebella products — restored in `ScrapingOrchestrator` via `get_pair_code` (AI variant grouping and variantVisibility depend on it).
  - Error dialog handler crashed on tuple unpacking — fixed.
  - `scripts/scraping_cli.py`, `scripts/categories.py`, `scripts/cleaning.py` imported deleted modules — rewritten against the new structure.
- **Improvements:** `ProductMerger.merge` (145 lines, deep nesting) split into `_merge_feed_products` / `_keep_main_products` / `_remove_discontinued` / `_update_from_feed`; dead `BatchOrchestrator.resume_active_job` deleted (resume happens inside `process()`); tests added for `PricingService`, `ProductDB`, `BatchJobDB`.
- **Docs:** CLAUDE.md updated to post-refactor architecture; memory bank refreshed and integration slimmed to a project skill.

## Active Decisions
- SQLite document store (`data/products.db`, 6-column schema with JSON `product_data` blob) is the source of truth; `aiProcessed`/`aiProcessedDate` survive client re-uploads.
- AI enhancement uses the asynchronous Gemini **Batch API** (job state tracked in `batch_jobs` SQLite table; interrupted jobs resume automatically inside `BatchOrchestrator.process`).
- Variants (products with `pairCode`) get dimension-free AI prompts; others get the standard prompt.
- Feed products always included in merge; main data filtered by selected categories; image merge prefers the source with more images; `PRESERVED_FIELDS` (AI/manual text) never overwritten by feeds.
- AI enhancement disabled by default in the UI (cost control).
- KISS + TDD: tests required for new non-trivial logic; no unrequested complexity.

## Known Gaps / Next Candidates
- pyright runs in `typeCheckingMode: "off"` — switching to "basic" would need cleanup of loose typing first (deliberately deferred, not requested).
- Manual end-to-end run with production feeds after the audit fixes is still pending.
