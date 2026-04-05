# GastroPro Product Manager — Layered Architecture Refactor

**Date:** 2026-04-06
**Status:** Approved
**Approach:** Full restructure into layered architecture

## Problem Statement

The data flow has become too complicated due to:
- Business logic scattered across worker (431 lines), main window (1,042 lines), and database (330 lines)
- AI enhancer god class (794 lines) mixing 9 concerns
- Category mapping duplicated across 3 separate systems
- Database making business decisions (upsert_from_client merge strategy)
- No clear ownership of responsibilities across layers

This makes it hard to add new data sources, debug data issues, and change business rules.

## Design Decisions

- **Full restructure** into layered architecture with strict dependency rules
- **Drop all `_new_format` suffixes** — the "new" format is the only format
- **No constraints** — free to restructure everything, app just needs to keep working
- **XLSX only** — no CSV support needed (input or output)

## Directory Structure

```
src/
  data/                        # Pure I/O layer
    loaders/
      xlsx_loader.py
      loader_factory.py
    parsers/
      xml_parser.py
      xml_parser_factory.py
    database/
      product_db.py            # thin: CRUD + JSON pack/unpack only
      batch_job_db.py          # AI batch job tracking (separate concern)
    writers/
      xlsx_writer.py           # output file writing (extracted from pipeline)

  domain/                      # Business logic layer
    products/
      merger.py                # pure merge logic (no DB awareness)
      variant_service.py       # pair code / variant rules
    categories/
      category_service.py      # single unified system (replaces 3 current ones)
      category_filter.py       # selection/filtering
    pricing/
      pricing_service.py       # price mapping logic (extracted from worker)
    transform/
      output_transformer.py    # 138-column transformation

  ai/                          # AI enhancement layer
    api_client.py              # Gemini API calls + quota management
    batch_orchestrator.py      # batch creation, monitoring, polling
    result_parser.py           # JSONL parsing + fuzzy matching
    product_enricher.py        # applying AI results to DataFrame
    prompts.py                 # prompt templates

  pipeline/                    # Orchestration layer
    pipeline.py                # coordinates everything, owns the data flow
    scraping.py                # scraper orchestration (extracted from worker)

  gui/                         # Presentation layer
    main_window.py             # UI only, no business logic
    worker.py                  # thin: calls pipeline, emits signals
    widgets.py
    column_config_dialog.py

  config/                      # Configuration
    config_loader.py
    schema.py                  # output column definitions (generated, not hardcoded)
```

## Dependency Rules

```
gui -> pipeline -> domain + ai -> data
                   ai -> data
```

No layer imports from a layer above it. `domain` and `ai` are peers — pipeline coordinates both. `data` depends on nothing in `src/`.

## Layer Designs

### Data Layer

Pure I/O — reads and writes but never makes business decisions.

#### Database

**ProductDB** — thin document store:

```python
class ProductDB:
    def get_all() -> pd.DataFrame        # unpack JSON -> flat DataFrame
    def upsert(df: pd.DataFrame)          # pack DataFrame -> JSON, save
    def backup()                          # rotating backups
    def delete_by_codes(codes: list)      # remove products
```

No merge strategy, no "preserve edits" logic, no column filtering. The caller decides what data to pass in.

**BatchJobDB** — separate class for AI batch job tracking. Owned by the AI layer, not the product pipeline.

#### Parsers

`xml_parser.py` — config-driven field mapping, handles Gastromarket (namespaced) and ForGastro feeds. No structural change, just drop the suffix.

#### Writers

`xlsx_writer.py` — takes a DataFrame + path, writes XLSX output. Extracted from pipeline.

#### Loaders

`loader_factory.py` delegates to `XLSXLoader`. XLSX only.

### Domain Layer

All business logic lives here.

#### Products: Merger

```python
class ProductMerger:
    def merge(
        main_df: pd.DataFrame,
        feed_dfs: dict[str, pd.DataFrame],
        selected_categories: list[str],
        preserve_edits: bool = False
    ) -> MergeResult

@dataclass
class MergeResult:
    products: pd.DataFrame      # merged output (new copy, inputs untouched)
    stats: MergeStats           # created/updated/removed/kept counts
```

Key rules:
- Works on copies, never mutates inputs
- Returns typed result instead of loose dict
- Image priority logic stays here (it's a merge rule)

#### Products: Variant Service

Extracts `get_pair_code()` and variant-related logic from worker. Small, testable module.

#### Categories: Category Service (unifies 3 systems)

Replaces `category_mapper.py`, `category_mapper_new_format.py`, and `CategoryMappingManager`:

```python
class CategoryService:
    def __init__(self, mappings_path: str)
    def map(old_category: str) -> str | None
    def suggest(old_category: str) -> list[str]    # fuzzy suggestions
    def add_mapping(old: str, new: str)
    def get_all_mappings() -> dict[str, str]
```

- Loads from `categories.json` once, caches in memory
- Fuzzy matching from old `get_category_suggestions()` lives here
- Thread lock removed (single-threaded GUI doesn't need it)

#### Categories: Category Filter

Stays mostly as-is, moves from `src/filters/` into `domain/categories/`.

#### Pricing: Pricing Service

Extracted from worker (200+ lines):

```python
class PricingService:
    def identify_unmapped(products: pd.DataFrame) -> list[str]
    def apply_mappings(products: pd.DataFrame, mappings: dict) -> pd.DataFrame
```

GUI interaction (price mapping dialog) stays in worker as a signal. Service does the data work.

#### Transform: Output Transformer

Stays mostly as-is. Gets its column list from `config/schema.py` instead of config.json.

### AI Layer

Split from 1 god class (794 lines) into 5 focused modules.

#### API Client

```python
class GeminiClient:
    def __init__(self, api_key: str, model: str, config: dict)
    def call(self, system_prompt: str, user_prompt: str) -> str
    def check_quota(self) -> bool
    def wait_for_quota(self)
```

Owns: API initialization, quota tracking with thread-safe lock, retry logic.

#### Prompts

Existing `ai_prompts.py` — drop suffix. Category parameter loading moves here (it's about building prompts).

#### Batch Orchestrator

```python
class BatchOrchestrator:
    def __init__(self, client: GeminiClient, batch_job_db: BatchJobDB)
    def process(self, batches: list[pd.DataFrame], prompt_builder) -> list[BatchResult]
    def resume_active_job(self) -> BatchResult | None
```

Owns: Batch creation, monitoring, polling, resuming interrupted jobs.

#### Result Parser

```python
class ResultParser:
    def parse_batch_results(self, raw_results: str) -> list[dict]
    def find_best_match(self, ai_product: dict, source_products: pd.DataFrame) -> int | None
```

Owns: JSONL parsing, fuzzy matching (rapidfuzz). Pure logic, no I/O.

#### Product Enricher

```python
class ProductEnricher:
    def __init__(self, client: GeminiClient, orchestrator: BatchOrchestrator, parser: ResultParser)
    def enrich(self, df: pd.DataFrame, categories: list[str]) -> EnrichmentResult
```

High-level coordinator the pipeline calls. Filters products needing enhancement, groups by category, delegates to orchestrator, uses parser to match results, returns enriched DataFrame + stats.

### Pipeline Layer

#### Pipeline

```python
class Pipeline:
    def __init__(self, config: dict):
        self.db = ProductDB(config["db_path"])
        self.merger = ProductMerger()
        self.category_service = CategoryService(config["categories_path"])
        self.transformer = OutputTransformer()
        self.enricher = ProductEnricher(...)
        self.pricing_service = PricingService(...)
        self.scraping = ScrapingOrchestrator(...)

    def run(self, options: PipelineOptions) -> PipelineResult:
        # Linear data flow:
        # 1. Load existing data from DB
        # 2. Load main file (XLSX)
        # 3. Parse XML feeds
        # 4. Scrape (if enabled)
        # 5. Merge all sources
        # 6. Map categories (with callback for unknowns)
        # 7. Apply pricing (with callback for unmapped)
        # 8. AI enhancement (if enabled)
        # 9. Transform to output format
        # 10. Save to DB
        # 11. Write output file
```

- **PipelineOptions** — typed dataclass replacing the loose options dict
- **PipelineResult** — dataclass with output path, merge stats, AI stats, timing info
- **Callbacks** for user interaction: `on_unknown_category`, `on_unmapped_price`
- **Linear flow** — each step takes input and returns output, no hidden side effects

#### Scraping Orchestrator

```python
class ScrapingOrchestrator:
    def scrape(self, feeds: list[dict]) -> dict[str, pd.DataFrame]
```

Calls Mebella/Topchladenie scrapers, returns source-tagged DataFrames.

### GUI Layer

#### Worker (thin)

```python
class PipelineWorker(QThread):
    progress = Signal(str)
    result = Signal(PipelineResult)
    category_mapping_needed = Signal(str, list)
    price_mapping_needed = Signal(list)

    def run(self):
        result = self.pipeline.run(
            self.options,
            on_progress=self.progress.emit,
            on_unknown_category=self._handle_category,
            on_unmapped_price=self._handle_price,
        )
        self.result.emit(result)
```

Worker does nothing except bridge pipeline callbacks to Qt signals and emit the result. ~50 lines.

#### Main Window

UI layout and event handling only. Business logic (category extraction, column config decisions) delegated to domain layer and pipeline.

### Configuration

#### Config Loader

```python
def load_config(path: str = "config.json") -> dict
def save_config(config: dict, path: str = "config.json")
```

#### Column Schema

Replace 138+ hardcoded column list with programmatic generation:

```python
def get_output_columns() -> list[str]:
    base = ["code", "name", "description", "price", "category", ...]
    images = [f"image{i}" for i in range(1, 151)]
    image_descs = [f"imageDesc{i}" for i in range(1, 151)]
    return base + images + image_descs
```

Removes ~500 lines from config.json.

#### Slimmer config.json

After extraction, config contains only:
- `xml_feeds` — feed URLs and field mappings
- `ai_enhancement` — model, batch size, temperature, rate limits
- `db_path` — database location
- `output_mapping` — field transformation rules
- `paths` — categories.json, categories_with_parameters.json, table_bases_prices.json

## What Gets Deleted

| Old | Replaced By |
|-----|-------------|
| `src/utils/category_mapper.py` | `domain/categories/category_service.py` |
| `src/mappers/` directory | `domain/categories/` |
| `src/filters/` directory | `domain/categories/category_filter.py` |
| `src/services/` directory | Not needed |
| All `_new_format` suffixes | Clean names |
| 138+ columns in config.json | `config/schema.py` |

## Testing Strategy

**Must-have tests during refactor:**
- `ResultParser.find_best_match()` — fuzzy matching logic, currently untested
- `CategoryService` — mapping, suggestions, persistence
- `ProductMerger` — merge logic with both preserve/non-preserve modes
- `Pipeline` integration test — end-to-end with mocked I/O

**Existing tests** get updated to match new import paths. No test logic changes since behavior stays the same.

## Migration Strategy

Parallel build, then swap. Bottom-up, each phase results in a working application.

```
Phase 1: Data layer     (loaders, parsers, database — reorganize, no behavior change)
Phase 2: Domain layer   (extract business logic from worker/DB/GUI into domain/)
Phase 3: AI layer       (split ai_enhancer into 5 modules)
Phase 4: Pipeline layer (rewrite pipeline as linear coordinator, extract scraping)
Phase 5: GUI layer      (slim down worker and main_window)
Phase 6: Config         (extract schema, slim config.json)
Phase 7: Cleanup        (delete old dirs, update all imports, run tests)
```

## Summary of Impact

| Before | After |
|--------|-------|
| Business logic in worker (431 lines) | Worker ~50 lines, bridges signals only |
| AI enhancer god class (794 lines) | 5 focused modules (~150-200 lines each) |
| 3 category mapping systems | 1 CategoryService |
| Database makes merge decisions | Database is thin CRUD |
| 138 columns hardcoded in JSON | Generated in schema.py |
| `_new_format` suffixes everywhere | Clean names |
| Loose dicts for options/results | Typed dataclasses |
| Unclear data ownership | Strict layer dependency rules |
