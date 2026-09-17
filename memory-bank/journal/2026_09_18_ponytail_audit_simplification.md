# 2026-09-18 Ponytail Audit Simplification & Over-engineering Pruning

## Rationale
Following `/ponytail-audit` and an approved execution plan, the codebase underwent a major simplification to eliminate over-engineering, dead one-shot scripts, duplicate parsing methods, legacy database tables, redundant factory layers, and orphaned UI attributes while strictly preserving business behavior, CLI utilities, GUI functions, and tests.

## Changes Completed

### 1. Obsolete Scripts Cleaned & Auto-Categorization Parameterized
- **Deleted one-shot scripts**: `scripts/generate_product_image.py`, `scripts/cleaning.py`, `scripts/restore_product_images.py`, `scripts/categories.py`.
- **Sanitized `scripts/auto_categorize.py`**: retained and parameterized via `argparse` (`--db`, `--excel`, `--categories`, `--batch-size`, `--max-workers`), eliminating hardcoded local user directories while providing a clean, reusable tool to categorize new products coming from feeds in the future.

### 2. Consolidated XML Parsing
- Replaced 3 duplicated 60-line parser methods (`parse_gastromarket`, `parse_gastromarket_stalgast`, `parse_forgastro`) with a single config-driven `parse_feed(feed_name, xml_content)` in `src/data/parsers/xml_parser.py`.
- Inlined top-level convenience functions `fetch_and_parse` and `parse` into `xml_parser.py`.
- Deleted superfluous indirection `src/data/parsers/xml_parser_factory.py`.

### 3. Removed Legacy BatchJobDB
- Replaced legacy April 2026 `BatchJobDB` table with the unified July 2026 `RunDB` across `src/ai/batch_orchestrator.py`, `src/ai/product_enricher.py`, `src/pipeline/pipeline.py`, and `scripts/pipeline_cli.py`.
- Removed `src/data/database/batch_job_db.py` and `TestBatchJobDB`.

### 4. Excel I/O & Helper Modules Consolidated
- Merged `src/data/loaders/xlsx_loader.py` and `src/data/writers/xlsx_writer.py` into a single module `src/data/excel.py` (`load_xlsx`, `write_xlsx`), deleting `src/data/loaders/` and `src/data/writers/`.
- Inlined `extract_categories` and `search_categories` into `CategoryService` (`src/domain/categories/category_service.py`), deleted `src/domain/categories/category_filter.py`, and removed dead `map_dataframe` and legacy test file `tests/test_category_mapper_new_format.py`.
- Inlined `get_pair_code` into `src/domain/products/merger.py` and re-exported from `src/domain/products/__init__.py`, deleting `src/domain/products/variant_service.py`.

### 5. Targeted Code Shrinks & Dead Flag Removal
- `src/ai/image_generator.py`: delegated HTML sanitization to `src.ai.pruning.prune_text`.
- `src/domain/transform/output_transformer.py`: deduplicated image column initialization loop in `split_images`.
- `src/gui/widgets.py` & `src/gui/worker.py`: removed dead `is_from_file`, `has_input_file`, and `should_apply_to_all_from_file` remnants.
- `src/config/config_loader.py`: simplified `read_api_key` using `dotenv.get_key()`.

## Verification Results
- `ruff check`: All checks passed.
- `ruff format`: Formatted cleanly.
- `pytest`: 249 passed, 0 failures (100% passing across the entire test suite).
- Impact: 40 files changed, 233 additions, 1,510 deletions (net **1,277 lines removed**, 13 obsolete files eliminated).
