# GastroPro Product Manager - Technical Context

## Technology Stack
- **Python 3.13**: Core programming language
- **PyQt5**: GUI framework for desktop application
- **Pandas**: Data manipulation library for CSV and data processing
- **openpyxl**: Excel file (XLSX) reading and writing
- **Requests**: HTTP client for XML feed fetching and web scraping
- **BeautifulSoup4**: HTML parsing for web scraping
- **ElementTree**: XML parsing library (built into Python standard library)
- **Concurrent.futures**: Multi-threading for parallel operations
- **difflib**: For string similarity comparison in variant detection
- **regex**: Advanced pattern matching for product difference extraction
- **google-generativeai**: For AI-powered product description enhancement
- **python-dotenv**: For managing environment variables (API keys)
- **threading**: For thread-safe quota management
- **pytest**: Testing framework (158 tests)

## Development Setup
- **Environment**: Windows operating system
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

## Data Structures
1. **Configuration (JSON)**:
   - App settings
   - Data source configurations
   - Output settings
   - Variant extraction rules (variant_extractions.json)
   - **Output mapping configuration** (output_mapping section):
     - Direct column mappings (internal → new format)
     - Special transformations (category, uppercase, image splitting)
     - Default values (applied only when empty)
     - Drop columns list

2. **Local CSV Structure**:
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
   - Multiple image columns: `defaultImage`, `image`, `image2-7`
   - Category fields with prefix: "Tovary a kategórie > ..."
   - Uppercase catalog codes
   - Raw data (no formatting) - e-shop handles display

4. **XML Feed Structure**:
   - **Gastromarket Feed**: RSS 2.0 with Google Base namespace
     - Prefixed namespace: `xmlns:g="http://base.google.com/ns/1.0"`
     - RSS structure elements (`<rss>`, `<channel>`, `<item>`) are NOT namespaced
     - Data elements use `g:` prefix: `<g:KATALOG_CISLO>`, `<g:MENO>`, etc.
     - Parsed using ElementTree with namespace dictionary
   - **ForGastro Feed**: Standard XML without namespace
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
1. **Base Scraper Class**: `TopchladenieScraper`
   - Core scraping logic and methods
   - Session management and request handling
   - Data extraction and parsing

2. **Enhanced Scraper**: `FastTopchladenieScraper`
   - Extends base scraper with multi-threading capabilities
   - Parallel product page processing
   - Thread-safe progress tracking
   - Optimized for performance with large catalogs

3. **Integration Points**:
   - Direct integration in Worker class for live scraping
   - Alternative offline CSV loading via dedicated UI component
   - Mutual exclusivity between scraping and CSV loading

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

### Legacy Structure (Old Format)
- **main.py**: Original application entry point
- **src/core/**: Core business logic with old `DataPipeline`
- **src/gui/**: Original PyQt5 UI (`MainWindow`, `Worker`)
- **src/services/**: External services (scraper, old ai_enhancer, variant_matcher)
- **src/utils/**: Helper modules (data_loader, config_loader, category_mapper)

### New Format Structure (138-Column)
- **main_new_format.py**: New application entry point
- **src/parsers/**: XML parsing for new format
  - `xml_parser_new_format.py` - Gastromarket & ForGastro parsers with namespace support
  - `xml_parser_factory.py` - Parser factory
  - **Namespace Handling**: Proper ElementTree prefix-based namespace parsing for Gastromarket RSS feed
- **src/mergers/**: Smart data merging
  - `data_merger_new_format.py` - Image priority merging
- **src/mappers/**: Category transformation
  - `category_mapper_new_format.py` - Category formatting
- **src/transformers/**: Output transformation
  - `output_transformer.py` - Final format transformation
- **src/ai/**: AI enhancement
  - `ai_enhancer_new_format.py` - Description generation with tracking
- **src/loaders/**: File I/O
  - `csv_loader.py` - CSV operations
  - `xlsx_loader.py` - XLSX operations
  - `data_loader_factory.py` - Format detection
- **src/pipeline/**: Complete integration
  - `pipeline_new_format.py` - End-to-end pipeline
- **src/gui/**: New GUI components
  - `main_window_new_format.py` - Modern interface
  - `worker_new_format.py` - Background processing
- **tests/**: Comprehensive test suite (158 tests)
  - Test files for each component
  - Integration tests
  - Edge case coverage

## AI Enhancement Architecture

- **Model & Tooling**: Gemini (google-generativeai) configured with a Google Search grounding tool to retrieve missing context when product inputs are sparse.
- **Content Outputs**: Generates/improves B2B "Krátky popis" and "Dlhý popis" (HTML), plus SEO metadata: "SEO titulka", "SEO popis", "SEO kľúčové slová".
- **Parallelism & Quotas**: Processes products in parallel batches via ThreadPoolExecutor while respecting API quotas (15 calls/min, 250k tokens/min) with token tracking and automatic backoff.
- **Prompt Engineering**: Structured, domain-specific system prompt enforces professional B2B tone, HTML structure, and strict JSON-only responses for reliable parsing.
- **Data Update Flow**: Fuzzy name matching updates the working DataFrame in-place; progress is saved incrementally with encoding fallback.

## File Operations
- Reading/writing CSV files
- Parsing XML from URLs
- Managing configuration JSON

## Network Operations
- HTTP requests to XML feed URLs
- Error handling for network failures
- Timeout handling

