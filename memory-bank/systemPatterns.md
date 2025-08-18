# GastroPro Product Manager - System Patterns

## Architecture Overview
GastroPro Product Manager follows a modular architecture with clear separation of concerns:

```
┌───────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌───────────────┐
│  User         │     │  Data           │     │  AI              │     │  Output       │
│  Interface    │◄────┤  Processing     │◄────┤  Enhancement     │◄────┤  Generation   │
└───────────────┘     └─────────────────┘     └──────────────────┘     └───────────────┘
        │                     │                        │                       │
        ▼                     ▼                        ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌───────────────┐
│  Input        │     │  Data           │     │  Product         │     │  Config       │
│  Handling     │     │  Storage        │     │  Variant         │     │  Management   │
└───────────────┘     └─────────────────┘     └──────────────────┘     └───────────────┘
```

### AI Enhancement Layer
```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                AI Enhancement                                 │
│  ┌─────────────┐     ┌────────────────┐     ┌─────────────────────────┐     │
│  │  Batch      │     │  Parallel      │     │  Quota & Rate          │     │
│  │  Processor  │◄───►│  Executor      │◄───►│  Limiter               │     │
│  └─────────────┘     └────────────────┘     └─────────────────────────┘     │
│         │                      │                       │                     │
│         ▼                      ▼                       ▼                     │
│  ┌─────────────┐     ┌────────────────┐     ┌─────────────────────────┐     │
│  │  Progress   │     │  Error         │     │  Token & Call           │     │
│  │  Tracking   │     │  Handling      │     │  Management             │     │
│  └─────────────┘     └────────────────┘     └─────────────────────────┘     │
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
   - Configurable extraction rules for different product categories
   - Flexible prompt engineering for different product types

2. **Configuration Management Pattern**:
   - External JSON configuration file
   - Runtime config updates
   - Default configuration fallback

3. **Data Processing Pipeline**:
   - Input stage: CSV loading and preparation
   - Processing stage: Category filtering, mapping, and XML feed integration
   - Web scraping stage: Multi-threaded acquisition of additional products and attributes (optional)
   - Variant Detection: Product grouping and difference extraction
   - Output stage: CSV generation and report export

4. **Variant Detection System**:
   - Product similarity analysis using name patterns
   - Configurable extraction of differences (dimensions, power, etc.)
   - Category-specific extraction rules
   - Human-readable reporting of variant groups

5. **AI Enhancement System**:
   - Parallel batch processing with configurable batch sizes
   - Token-based quota management (250k tokens/minute)
   - Automatic retry with exponential backoff
   - Progress tracking and incremental saving
   - Thread-safe API call management
   - Encoding fallback (cp1250 → UTF-8)
   - Status tracking with timestamps
   - Grounded web search tool (Google Search) for contextual enrichment when inputs are sparse
   - Structured prompt engineering for B2B tone, HTML formatting, and strict JSON-only outputs

4. **Category Mapping System**:
   - Universal JSON array format for mapping definitions
   - Centralized mapping functions for consistent application
   - User-controlled application at export time
   - Detailed logging of mapping operations

## Component Relationships
- **MainWindow Class**: Core controller that manages the application flow
- **ProductVariantMatcher**: Handles variant detection and difference extraction
- **Utils Module**: Handles file operations, configuration, and external data fetching
- **Data Models**: Pandas DataFrames for data manipulation
- **Config Files**: External configurations for app settings, data sources, and variant extraction rules

## Technical Decisions
1. **PyQt5 for GUI**: Provides robust desktop application interface
2. **Pandas for Data Manipulation**: Efficient handling of tabular data
3. **JSON for Configuration**: Human-readable and easily modifiable
4. **ElementTree for XML Parsing**: Standard library solution for XML processing

## Future Considerations
- Potential for plugin architecture to support additional data formats
- Database integration for persistent storage
- Caching mechanism for XML feeds to reduce network requests
