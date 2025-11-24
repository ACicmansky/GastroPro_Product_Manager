# GastroPro Product Manager - System Patterns

## Architecture Overview
The application follows a modular, package-based architecture with a clear separation of concerns, organized within the `src` directory. This structure promotes maintainability, scalability, and testability.

```
src/
├── core/         # Core business logic and data pipeline
│   ├── data_pipeline.py
│   └── models.py
├── gui/          # All PyQt5 UI components and logic
│   ├── main_window.py
│   ├── widgets.py
│   └── worker.py
├── services/     # External service integrations
│   ├── ai_enhancer.py
│   ├── scraper.py
│   └── variant_matcher.py
└── utils/        # Shared utility functions
    ├── config_loader.py
    ├── data_loader.py
    ├── category_mapper.py
    ├── feed_processor.py
    └── helpers.py
```

### AI Enhancement Layer
```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                AI Enhancement                                 │
│  ┌─────────────┐     ┌────────────────┐     ┌─────────────────────────┐       │
│  │  Batch      │     │  Parallel      │     │  Quota & Rate           │       │
│  │  Processor  │◄───►│  Executor      │◄───►│  Limiter                │       │
│  └─────────────┘     └────────────────┘     └─────────────────────────┘       │
│         │                      │                       │                      │
│         ▼                      ▼                       ▼                      │
│  ┌─────────────┐     ┌────────────────┐     ┌─────────────────────────┐       │
│  │  Progress   │     │  Error         │     │  Token & Call           │       │
│  │  Tracking   │     │  Handling      │     │  Management             │       │
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

9. **AI Enhancement System (Phase 13)**:
   - **Full Gemini API Integration**: Real API client with web search grounding
   - **Quota Management**: Thread-safe tracking (15 calls/min, 250K tokens/min)
   - **Batch Processing**: Configurable batch size (45 products), parallel execution
   - **Retry Logic**: 3 attempts with exponential backoff, rate limit detection
   - **Fuzzy Matching**: 3-strategy matching (exact code, fuzzy code, fuzzy name)
   - **Parallel Processing**: ThreadPoolExecutor with 5 workers
   - **Incremental Saving**: Progress saved after each batch
   - **Column Name Migration**: Slovak → English (code, name, shortDescription, etc.)
   - **Enhanced Fields**: shortDescription, description, seoTitle, seoDescription, seoKeywords
   - **Processing Tracking**: aiProcessed flag, aiProcessedDate timestamp

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

## Component Relationships
- **main.py**: The main entry point of the application; initializes and runs the GUI.
- **src/gui/main_window.py**: Contains the `MainWindow` class, which manages the entire UI, its state, and user interactions. It delegates data processing to the `worker`.
- **src/gui/worker.py**: A thin `QThread` worker that runs the `DataPipeline` in the background to keep the UI responsive.
- **src/core/data_pipeline.py**: The heart of the application's business logic. It orchestrates the entire data processing flow, from loading and filtering to merging, variant matching, and AI enhancement.
- **src/services/**: A package containing modules that interact with external systems or perform complex, self-contained tasks (e.g., web scraping, AI enhancement, variant matching).
- **src/utils/**: A package of small, focused modules providing reusable helper functions for tasks like loading data, processing feeds, and mapping categories.

## Technical Decisions
1. **PyQt5 for GUI**: Provides robust desktop application interface
2. **Pandas for Data Manipulation**: Efficient handling of tabular data
3. **JSON for Configuration**: Human-readable and easily modifiable
4. **ElementTree for XML Parsing**: Standard library solution for XML processing

## Future Considerations
- Potential for plugin architecture to support additional data formats
- Database integration for persistent storage
- Caching mechanism for XML feeds to reduce network requests

10. **Scraper Caching Strategy**:
    - **JSON-based Caching**: Stores scraped URLs/data in `cache/` directory
    - **Validity Period**: Configurable expiration (e.g., 7 days) to prevent stale data
    - **Hash-based Keys**: Uses MD5 hash of URLs for unique filenames
    - **Performance**: Skips expensive scraping steps (Playwright/scrolling) if cache is valid
