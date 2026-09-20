# GastroPro Product Manager - System Patterns

## Architecture Overview
Pragmatic Hexagonal Architecture (Ports and Adapters) refactor (September 2026). Decouples core business rules and use cases from external drivers (PyQt5 GUI, CLI scripts) and driven dependencies (SQLite, Gemini API, XML parsers, Excel I/O). Dependencies flow inward towards domain and use cases. Zero circular dependencies.

```
src/
├── pipeline/          # Application Use Cases & Facade
│   ├── use_cases/     # Focused business workflows
│   │   ├── sync_catalog.py      # SyncCatalogUseCase (full multi-source flow)
│   │   ├── export_catalog.py    # ExportCatalogUseCase (direct DB -> 138-col XLSX)
│   │   ├── resume_ai.py         # ResumeAiUseCase (resuming interrupted batch jobs)
│   │   └── enrich_categories.py # EnrichCategoriesUseCase (category-scoped AI re-runs)
│   ├── pipeline.py    # Pipeline — backward-compatible facade & composition root
│   └── scraping.py    # ScrapingOrchestrator — satisfies ScraperGatewayPort
├── domain/            # Pure business logic & ports
│   ├── ports/         # Python Protocols (driven & driving interfaces)
│   │   ├── repositories.py      # ProductRepositoryPort, RunRepositoryPort
│   │   ├── gateways.py          # FeedGatewayPort, ScraperGatewayPort, AiEnricherPort, ExcelIOPort
│   │   ├── events.py            # EventSinkPort, NullEventSink, CallbackEventSink, ConsoleEventSink
│   │   └── resolution.py        # UserResolutionPort, AutoSkipResolution, CallbackResolution
│   ├── products/      # ProductMerger, get_pair_code, feed_specs
│   ├── categories/    # CategoryService (mapping, suggestions, filter extraction)
│   ├── pricing/       # PricingService (table_bases_prices.json records)
│   ├── transform/     # OutputTransformer (138-column output)
│   └── models.py      # MergeResult, MergeStats, PipelineOptions, PipelineResult...
├── data/              # Driven adapters (I/O)
│   ├── excel.py       # Consolidated XLSX loading and writing (ExcelIOPort)
│   ├── parsers/       # Config-driven XML feed parser (FeedGatewayPort)
│   └── database/      # ProductDB (JSON document store), RunDB (run/chunk tracking)
├── ai/                # Driven adapter: Gemini integration (AiEnricherPort)
│   ├── api_client.py          # GeminiClient (quota, upload, batch jobs)
│   ├── batch_orchestrator.py  # BatchOrchestrator (JSONL build, poll, resume)
│   ├── product_enricher.py    # ProductEnricher (satisfies AiEnricherPort)
│   ├── prompts.py             # Dual prompt system
│   ├── result_parser.py       # ResultParser (3-strategy fuzzy matching)
│   └── image_generator.py     # ProductImageGenerator (Nano Banana studio photos)
├── scrapers/          # Driven adapter: Web scrapers (ScraperGatewayPort)
├── gui/               # Driving adapter: PyQt5 GUI
│   ├── main_window.py # MainWindow (UI cards, actions, settings)
│   ├── worker.py      # Thin PipelineWorker + QtSignalEventSink + QtDialogResolver
│   └── widgets.py     # UI components, dialogs, toasts
└── config/            # Config loading and schema
```

### AI Enhancement Layer
```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                AI Enhancement                                 │
│  ┌─────────────┐     ┌────────────────┐     ┌─────────────────────────┐       │
│  │  Categories │     │  Batch API     │     │  Background Job       │       │
│  │  Grouper    │◄───►│  Generation    │◄───►│  Polling (SQLite)       │       │
│  └─────────────┘     └────────────────┘     └─────────────────────────┘       │
│         │                      │                       │                      │
│         ▼                      ▼                       ▼                      │
│  ┌─────────────┐     ┌────────────────┐     ┌─────────────────────────┐       │
│  │  Prompt     │     │  Asynchronous  │     │  DataFrame UI           │       │
│  │  Injection  │     │  Retrieval     │     │  Event Blocking         │       │
│  └─────────────┘     └────────────────┘     └─────────────────────────┘       │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Design Patterns
1. **MVC Pattern**:
   - **Model**: Data structures for product information
   - **View**: PyQt5-based GUI components
   - **Controller**: Application logic in the MainWindow class

2. **Parallel Processing Pattern**:
   - ThreadPoolExecutor for concurrent batch processing
   - Configurable thread pool size (max_parallel_calls)
   - Thread-safe quota and token management
   - Progress tracking across multiple threads
   - Applied to both AI enhancement batches and multi-threaded web scraping

3. **Rate Limiter Pattern**:
   - Enforces API call limits (15/minute)
   - Token bucket algorithm for token management
   - Automatic wait and retry on quota limits
   - Thread-safe counters with locks

4. **Strategy Pattern**:
   - Used in variant detection with different similarity comparison strategies
   - Token-based quota management (250k tokens/minute)
   - Automatic retry with exponential backoff
   - Progress tracking and incremental saving
   - Thread-safe API call management
   - Encoding fallback (cp1250 → UTF-8)
   - Status tracking with timestamps
   - Grounded web search tool (Google Search) for contextual enrichment when inputs are sparse
   - Structured prompt engineering for B2B tone, HTML formatting, and strict JSON-only outputs

6. **Interactive Callback Pattern**:
   - Thread-safe signal/slot communication between worker and UI threads
   - QEventLoop for synchronous blocking in worker thread while awaiting user input
   - Modal dialog pauses pipeline execution for user interaction
   - Graceful fallback when callback is not provided

7. **Category Mapping System**:
   - Universal JSON array format for mapping definitions
   - Centralized mapping functions for consistent application
   - User-controlled application at export time
   - Interactive on-the-fly mapping via CategoryMappingDialog
   - **Smart Mapping Priority**:
     1. Check explicit mappings (Manager & Custom)
     2. Check if already a valid target category (prevents redundant prompts)
     3. Interactive callback (if enabled)
     4. Return original category
   - **Root Category Enforcement**: Mappings must aggressively roll up under primary root labels (e.g., `Gastro Prevádzky a Profesionáli >` or `Domácnosť a Kulinári >`) to handle inconsistent external XML category hierarchies.
   - Optional callback mechanism for real-time unmapped category resolution
   - Detailed logging of mapping operations

8. **Advanced Merging Logic with Category Filtering**:
   - **Feed Priority**: Products from XML feeds and web scraping always included
   - **Smart Updates**: Feed products update price and images in main data (if more images)
   - **Category Filtering**: Main data products filtered by selected categories
   - **Removal Logic**: Main data products in unchecked categories removed (unless updated by feeds)
   - **Source Tracking**: Every product tagged with origin (gastromarket, forgastro, web_scraping, core)
   - **Timestamp Tracking**: All products have last_updated timestamp
   - **Detailed Statistics**: Track created/updated/kept/removed counts by source
   - **Two-Step Process**:
     1. Process feed/scraped products (always included, update existing)
     2. Process main data products (category filtered, skip if already processed)

9. **AI Enhancement System (Phase 13 / April 2026 Update)**:
   - **Full Gemini API Integration**: Real API client utilizing asynchronous **Batch API**.
   - **JSON-based Parsing**: Gemini produces `application/json` enforced schemas, avoiding markdown code-block discrepancies entirely.
   - **Parameter Extraction**: AI groups products by category automatically drawing exact attributes matching `categories_with_parameters.json`.
   - **Background Polling**: GUI seamlessly locks overlapping activities while tracking the backend API request across days via SQLite persistence.
   - **Enhanced Fields**: shortDescription, description, seoTitle, seoDescription, seoKeywords, *and* unpredictable `filteringProperty:{parameter_name}` columns.

10. **AI Enhancement Grouping Logic (November 2025)**:
    - **Product Variants (Group 1)**: Products with `pairCode` OR whose `code` is used as a `pairCode` by another product
    - **Standard Products (Group 2)**: All other products without variant relationships
    - **Dual Prompt System**:
      - Group 1 uses `create_system_prompt_no_dimensions()` - excludes dimension keywords
      - Group 2 uses `create_system_prompt()` - standard prompt with all features
    - **Negative Constraints for Variants**: Prevents AI from generating "výška", "šírka", "dĺžka", "hĺbka", "rozmery", "mm", "cm", "m" in text fields
    - **Batch Processing**: Separate batches created for each group with appropriate config
    - **Data Preservation**: `pairCode` preserved through merger via `DataMergerNewFormat`
    - **Verification**: `verify_ai_grouping.py` script confirms correct prompt selection

11. **Database as Single Source of Truth (Document Store)**:
    - **Persistence Paradigm**: Completely abstracts multi-column formats to a flexible 6-column database core treating properties as a dynamic `product_data` JSON.
    - **Robust Upsert**: In and outbound data operates universally seamlessly; `get_all_products` unpacks the JSON back into wide pandas data.
    - **Automated Backup**: Native rotation and retention.

## Component Relationships
- **main.py**: Entry point; initializes and runs the GUI (`MainWindow`).
- **src/gui/main_window.py**: `MainWindow` manages the UI and delegates processing to `PipelineWorker`.
- **src/gui/worker.py**: Thin `QThread` worker running `Pipeline` in the background. Blocking interactive callbacks (category mapping, price mapping) use signal → dialog → `QEventLoop` → `set_*_result`.
- **src/pipeline/pipeline.py**: `Pipeline` orchestrates the flow: load → parse feeds → scrape → price-map (pre-merge, Mebella) → merge → map categories → AI enhance → transform → export.
- **src/domain/**: Pure business logic — `ProductMerger` (with `get_pair_code`), `CategoryService`, `PricingService`, `OutputTransformer`.
- **src/data/**: Excel I/O (`excel.py`), config-driven `XMLParser`, document store (`ProductDB`), and run tracker (`RunDB`).
- **src/ai/**: `BatchOrchestrator` drives the Gemini Batch API through `GeminiClient`; `ResultParser` applies results back via 3-strategy fuzzy matching.

## Technical Decisions
1. **PyQt5 for GUI**: Provides robust desktop application interface
2. **Pandas for Data Manipulation**: Efficient handling of tabular data
3. **JSON for Configuration**: Human-readable and easily modifiable
4. **ElementTree for XML Parsing**: Standard library solution for XML processing
5. **Database as Single Source of Truth**: Replaces transient memory states with robust upsert workflows.
6. **Strict Legacy Deprecation**: Do not mix legacy implementations with the modern pipeline (`PipelineNewFormat`, 138-column format). Legacy code is actively deprecated.
7. **TDD (Test-Driven Development)**: Always write or maintain existing tests before/after implementing features.
8. **KISS Principle**: Do not proactively propose unrequested features or complexity; adhere to the simplest robust implementation.
9. **Windows OS First**: Ensure Windows-compatible paths (`\\` or raw strings) and `CRLF` line endings.

## Future Considerations
- Potential for plugin architecture to support additional data formats
- Database integration for persistent storage
- Caching mechanism for XML feeds to reduce network requests

10. **Scraper Caching Strategy**:
    - **JSON-based Caching**: Stores scraped URLs/data in `cache/` directory
    - **Validity Period**: Configurable expiration (e.g., 7 days) to prevent stale data
    - **Hash-based Keys**: Uses MD5 hash of URLs for unique filenames
    - **Performance**: Skips expensive scraping steps (Playwright/scrolling) if cache is valid
