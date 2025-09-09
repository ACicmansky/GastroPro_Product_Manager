# GastroPro Product Manager - Technical Context

## Technology Stack
- **Python 3.x**: Core programming language
- **PyQt5**: GUI framework for desktop application
- **Pandas**: Data manipulation library for CSV and data processing
- **Requests**: HTTP client for XML feed fetching and web scraping
- **BeautifulSoup4**: HTML parsing for web scraping
- **ElementTree**: XML parsing library (built into Python standard library)
- **Concurrent.futures**: Multi-threading for parallel operations
- **difflib**: For string similarity comparison in variant detection
- **regex**: Advanced pattern matching for product difference extraction
- **google-generativeai**: For AI-powered product description enhancement
- **python-dotenv**: For managing environment variables (API keys)
- **threading**: For thread-safe quota management

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
- Python 3.x
- PyQt5
- pandas
- requests
- beautifulsoup4
- tqdm (for progress reporting)
- regex (for advanced pattern matching)
- google-generativeai>=0.5.0
- python-dotenv>=1.0.0

## Data Structures
1. **Configuration (JSON)**:
   - App settings
   - Data source configurations
   - Output settings
   - Variant extraction rules (variant_extractions.json)

2. **Local CSV Structure**:
   - Product ID
   - Product name
   - Price
   - Description
   - "Hlavna kategória" (Main category) - used for filtering
   - "Spracovane AI" - Tracks if product was processed by AI (TRUE/FALSE)
   - "AI_Processed_Date" - Timestamp of last AI processing
   - Other product attributes

3. **XML Feed Structure** (Typical):
   - Product entries
   - Product identifiers
   - Product details (name, price, description, etc.)
   - Category information

4. **Internal Data Representation**:
   - Pandas DataFrames for both local and processed data
   - Dictionary mappings for configuration
   - Standardized column names across data sources

5. **Scraped Data Structure**:
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

- **main.py**: Application entry point.
- **src/core/**: Contains the core business logic, including the main `DataPipeline`.
- **src/gui/**: All PyQt5 user interface components, including the `MainWindow`, custom widgets, and the background `Worker` thread.
- **src/services/**: Houses modules for interacting with external services, such as `scraper`, `ai_enhancer`, and `variant_matcher`.
- **src/utils/**: A collection of helper modules for common tasks like loading data and configurations, processing feeds, and mapping categories.

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

