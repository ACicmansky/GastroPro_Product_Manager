# 2026-07-07 — Ponytail over-engineering audit applied

Repo-wide audit (`/ponytail:ponytail-audit`) produced 11 findings; all applied. Net ≈ **-1,050 lines, -3 deps, 1 dep corrected**.

## Deletions
- `scripts/`: 11 one-shot migration/debug scripts removed via `git rm` (~880 lines): extract_name_and_descriptions, fetch_mebella_product, find_unused_methods, get_unique_categories, scrape_one_mebella, test_mebella_{access,multithreading,pagination,scraping}, transform_categories_to_new_format, transform_to_new_format. Kept: `pipeline_cli.py`, `scraping_cli.py`, `categories.py`, `cleaning.py`.
- `src/data/loaders/loader_factory.py` deleted; `XLSXLoader` class collapsed into a single `load_xlsx()` function in `xlsx_loader.py`. Call sites updated: `pipeline.py`, `pipeline_cli.py`, `main_window.py`, tests. Package `__init__` exports adjusted.
- `XMLParserFactory.get_parser` removed (ignored feed_name, always returned `XMLParser(config)`); `parse()` constructs `XMLParser(config)` directly.
- `BatchJobDB.get_job` removed (zero callers); its tests rewritten against `get_active_job`.
- `EnrichmentResult.skipped` field removed (always 0, never read); both constructions in `product_enricher.py` updated.

## requirements.txt
- **Correctness fix**: `google-generativeai` → `google-genai` (code uses `from google import genai; from google.genai import types` — fresh `pip install -r requirements.txt` produced a broken install).
- Removed never-imported `lxml`, `llm_output_parser`; deduped `python-dotenv`.

## Batch tmp dir
- `BatchOrchestrator.tmp_dir` default moved from `src/ai/tmp/` to gitignored `out/batch_requests`; `ai_enhancement.tmp_dir` config override still honored. Old `src/ai/tmp/*.jsonl` debris left for manual deletion (rm was declined).

## Verification
- `python -m pytest`: **206 passed** (baseline 212; 2 obsolete factory tests removed, `test_xlsx_loader.py` rewritten to 7 tests, 3 `BatchJobDB` tests rewritten).
- Sweep grep for `XLSXLoader|DataLoaderFactory|loader_factory|get_parser|skipped=`: clean.

Not committed — awaiting user.
