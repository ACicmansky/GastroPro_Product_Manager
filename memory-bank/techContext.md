# GastroPro Product Manager - Technical Context

## Technology Stack
- **Python 3.13**: Core programming language
- **SQLite3**: Lightweight relational database mapped to dynamic schema for data persistence
- **PyQt5**: GUI framework for desktop application
- **Pandas**: Data manipulation library for CSV and data processing
- **openpyxl**: Excel file (XLSX) reading and writing
- **Network & AI**:
  - `requests` for fetching Google Sheets, web scraping, and API calls (Feed/Scraping/API integration)
  - `beautifulsoup4` and `lxml` for HTML parsing
  - `playwright` for end-to-end automated testing
  - `google-generativeai` and `google-cloud-storage` for invoking the async Google Gemini Batch API.
- **Data Persistence**:
  - `sqlite3` for robust local state and mapping schemas to flexible document blob structures.
- **Concurrent.futures**: Multi-threading for parallel operations
- **difflib**: For string similarity comparison in variant detection
- **regex**: Advanced pattern matching for product difference extraction
- **python-dotenv**: For managing environment variables (API keys)
- **threading**: For thread-safe quota management
- **pytest**: Testing framework (196 tests)

## Development Setup
- **Environment**: Windows operating system
- **Line Endings**: Requires Windows standard CRLF.
- **Path Standard**: Windows-compatible paths (`\\` or raw paths) must be used.
- **Methodology**: TDD (Test-Driven Development) is enforced.
- **IDE**: Compatible with standard Python IDEs
- **Version Control**: Git repository
- **Environment Variables**:
  - `GOOGLE_API_KEY`: Required for Gemini API access

## Technical Constraints
- **Performance**: Must handle CSV files with potentially thousands of products
- **Memory Usage**: Efficient memory management for large datasets
- **Error Handling**: Robust error handling for network failures and malformed data
- **Encoding**: Support for UTF-8, cp1250 with fallback to UTF-8
- **Variant Detection**: Configurable similarity threshold (default: 0.98) for product grouping
- **Extraction Rules**: Category-specific configuration for difference extraction
- **API Quotas**:
  - Max 15 API calls per minute
  - Max 250,000 tokens per minute
  - Automatic retry with exponential backoff

## Dependencies
- Python 3.13
- sqlite3 (Standard Library)
- PyQt5
- pandas
- openpyxl (XLSX support)
- requests
- beautifulsoup4
- tqdm (for progress reporting)
- regex (for advanced pattern matching)
- google-generativeai>=0.5.0
- python-dotenv>=1.0.0
- pytest (testing framework)
- rapidfuzz (category matching)
- playwright (dynamic web scraping)

## Data Structures
1. **Configuration (JSON)**:
   - App settings
   - Data source configurations
   - Output settings
   - Variant extraction rules (variant_extractions.json)
   - Dataset paths including `db_path`
   - **Output mapping configuration** (output_mapping section):
     - Direct column mappings (internal → new format)
     - Special transformations (category, uppercase, image splitting)
     - Default values (applied only when empty)
     - Drop columns list

2. **SQLite Database (`data/products.db`)**:
   - Single source of truth containing a dynamic flexible `products` table schema generated from `config.json`.
   - Stores all products across sessions, enabling safety via automated backups.

3. **Local CSV Structure**:
   - Product ID
   - Product name
   - Price
   - Description
   - "Hlavna kategória" (Main category) - used for filtering
   - "Spracovane AI" - Tracks if product was processed by AI (TRUE/FALSE)
   - "AI_Processed_Date" - Timestamp of last AI processing
   - Other product attributes

3. **New Output Format (138 columns)**:
   - E-shop compatible format
   - Includes all product data, variants, pricing, flags, marketplace settings
   - AI tracking columns: `aiProcessed`, `aiProcessedDate`
   - Multiple image columns: `image`, `image2-7`
   - Category fields with prefix: "Tovary a kategórie > ..."
   - Uppercase catalog codes
   - Raw data (no formatting) - e-shop handles display

4. **XML Feed Structure**:
   - **Gastromarket Feed**: RSS 2.0 with Google Base namespace
     - Prefixed namespace: `xmlns:g="http://base.google.com/ns/1.0"`
     - RSS structure elements (`<rss>`, `<channel>`, `<item>`) are NOT namespaced
     - Data elements use `g:` prefix: `<g:KATALOG_CISLO>`, `<g:MENO>`, etc.
   1. **Google Gemini API**: Used via `google-generativeai` asynchronously using Google's newest Batch API for maximum parallel generation speeds at half costs.
2. **Gastromarket (Stalgast) Feed**: XML feed serving as the primary automated data source
3. **Google Sheets**: Optional source mapping configurations
4. **Local Document Store Database**: Maintained SQLite schema transitioning from 138-rigid columns to a 6 column paradigm (`product_data` serving as a text JSON blob) for endless parameter generation scale by AI (handling infinite `filteringProperty:{parameter_name}` fields).
   - Product entries with identifiers, details, and category information

5. **Internal Data Representation**:
   - Pandas DataFrames for both local and processed data
   - Dictionary mappings for configuration
   - Standardized column names across data sources

6. **Scraped Data Structure**:
   - Catalog number ("Kat. číslo") as primary key
   - Product name
   - Price information
   - Product descriptions
   - Category path
   - Stock availability
   - Images (URLs)
   
## Web Scraping Architecture

### Scraping Components
1. **Base Class**: `BaseScraper` (src/scrapers/base_scraper.py)
   - Configurable multi-threading (`max_threads` clamped to 1-16), session management, progress callbacks

2. **Scrapers**:
   - `TopchladenieScraper` — multi-threaded (default 8 workers)
   - `MebellaScraper` — Playwright with infinite scroll; caches URLs for 7 days in `cache/`

3. **Integration Points**:
   - `ScrapingOrchestrator` (src/pipeline/scraping.py) runs enabled scrapers, tags `source="web_scraping"`, assigns `pairCode` to Mebella products
   - Alternative offline CSV loading for Topchladenie (mutually exclusive with live scraping)
   - CLI: `scripts/scraping_cli.py`

### Scraping Process Flow
1. **Initialization**: Create scraper instance with configuration
2. **Category Discovery**: Identify product categories to scrape
3. **Product List Extraction**: Obtain product URLs from category pages
4. **Parallel Processing**: Distribute product page scraping across worker threads
5. **Data Normalization**: Format extracted data to match application schema
6. **DataFrame Construction**: Convert normalized data to pandas DataFrame
7. **Data Cleaning**: Filter out products with empty catalog numbers
8. **Integration**: Merge with other data sources according to priority rules

## File Structure
The application is organized into a `src` package to ensure clear separation of concerns:

### Current Structure (post July 2026 layered refactor)
- **main.py**: Application entry point (GUI, 138-column format)
- **src/pipeline/**: `pipeline.py` (Pipeline coordinator), `scraping.py` (ScrapingOrchestrator)
- **src/data/**: `loaders/` (CSV/XLSX + factory), `parsers/` (XMLParserFactory; Gastromarket namespaced `g:` prefix, ForGastro plain), `writers/`, `database/` (ProductDB document store, BatchJobDB)
- **src/domain/**: `products/` (ProductMerger, variant_service), `categories/` (CategoryService, filter), `pricing/` (PricingService), `transform/` (OutputTransformer, 138 columns), `models.py`
- **src/ai/**: `api_client.py` (GeminiClient), `batch_orchestrator.py`, `product_enricher.py`, `prompts.py`, `result_parser.py`
- **src/scrapers/**: `base_scraper.py`, `topchladenie_scraper.py`, `mebella_scraper.py`
- **src/gui/**: `main_window.py`, `worker.py` (thin PipelineWorker), `widgets.py`, dialogs
- **src/config/**: config loading and schema
- **tests/**: 196 tests (unit + integration, pytest markers)

## AI Enhancement Architecture

- **Model**: `gemini-2.5-flash-lite` via the asynchronous **Gemini Batch API** (`client.batches.create`) — JSONL requests built per category, uploaded, polled every 30s until completion.
- **Content Outputs**: B2B short/long descriptions (HTML) plus SEO metadata and `filteringProperty:{parameter}` columns per category.
- **Dual Prompts**: Products with `pairCode` (variants) get dimension-free prompts; standard products get the full prompt.
- **Job Tracking**: `batch_jobs` SQLite table; interrupted jobs resume automatically inside `BatchOrchestrator.process()`.
- **Result Application**: `ResultParser` with 3-strategy fuzzy matching (exact code → fuzzy code → fuzzy name) updates the DataFrame; `aiProcessed`/`aiProcessedDate` track state.

## File Operations
- Reading/writing CSV files
- Parsing XML from URLs
- Managing configuration JSON

## Network Operations
- HTTP requests to XML feed URLs
- Error handling for network failures
- Timeout handling

