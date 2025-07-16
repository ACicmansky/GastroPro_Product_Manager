# GastroPro Product Manager - Technical Context

## Technology Stack
- **Python 3.x**: Core programming language
- **PyQt5**: GUI framework for desktop application
- **Pandas**: Data manipulation library for CSV and data processing
- **Requests**: HTTP client for XML feed fetching and web scraping
- **BeautifulSoup4**: HTML parsing for web scraping
- **ElementTree**: XML parsing library (built into Python standard library)
- **Concurrent.futures**: Multi-threading for parallel scraping operations

## Development Setup
- **Environment**: Windows operating system
- **IDE**: Compatible with standard Python IDEs
- **Version Control**: Git repository

## Technical Constraints
- **Performance**: Must handle CSV files with potentially thousands of products
- **Memory Usage**: Efficient memory management for large datasets
- **Error Handling**: Robust error handling for network failures and malformed data
- **Encoding**: Support for UTF-8 and other encodings common in CSV files

## Dependencies
- Python 3.x
- PyQt5
- pandas
- requests
- beautifulsoup4
- tqdm (optional, for progress reporting)

## Data Structures
1. **Configuration (JSON)**:
   - App settings
   - Data source configurations
   - Output settings

2. **Local CSV Structure**:
   - Product ID
   - Product name
   - Price
   - Description
   - "Hlavna kategória" (Main category) - used for filtering
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

## File Operations
- Reading/writing CSV files
- Parsing XML from URLs
- Managing configuration JSON

## Network Operations
- HTTP requests to XML feed URLs
- Error handling for network failures
- Timeout handling
