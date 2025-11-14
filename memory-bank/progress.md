# GastroPro Product Manager - Progress

## Completed Features
- ✅ **Major Codebase Refactoring**: Restructured the application into a modular `src` package, separating concerns (GUI, core logic, services, utils) and improving maintainability.
- ✅ Basic application framework with PyQt5
- ✅ Configuration management (load/save config)
- ✅ Local CSV file import functionality with drag & drop + clickable area
- ✅ Basic UI components and layout
- ✅ Output CSV saving functionality with encoding fallback
- ✅ XML feed fetching and parsing
- ✅ Feed-specific data processing (forgastro, gastromarket)
- ✅ Data merging with multiple feeds (outer join)
- ✅ Specialized HTML content extraction for product descriptions
- ✅ Handling special characters and formatting in feeds
- ✅ Setting "Viditeľný" field to "1" for all imported feed products
- ✅ Universal category mapping system for all data sources
- ✅ Optional user-controlled CSV category mapping at export time
- ✅ Interactive real-time category mapping dialog during processing
- ✅ Automatic saving of new category mappings to categories.json with thread safety
- ✅ Smart category suggestions using rapidfuzz + hierarchical matching with confidence scores
- ✅ CategoryMappingManager with centralized caching and single-source-of-truth architecture
- ✅ Product name context display in category mapping dialog
- ✅ Category filtering with text search and toggle selection
- ✅ Progress indicators for long-running operations
- ✅ Topchladenie.sk web scraping with multi-threading
- ✅ Alternative CSV loading for Topchladenie.sk products
- ✅ Dedicated drag & drop area for Topchladenie CSV files
- ✅ Mutual exclusivity between scraping and CSV loading
- ✅ Enhanced data validation with empty catalog number filtering
- ✅ Detailed statistics reporting in export summary dialog
- ✅ Fixed semicolon separator handling for Topchladenie CSV files
- ✅ Product variant detection based on name similarity
- ✅ Configuration-based difference extraction for product variants
- ✅ Human-readable variant difference reports
- ✅ Category-specific difference extraction rules
- ✅ AI-powered product description enhancement
- ✅ SEO metadata generation (SEO titulka, SEO popis, SEO kľúčové slová)
- ✅ Web search grounding to enrich missing context during AI processing
- ✅ Parallel batch processing with ThreadPoolExecutor
- ✅ API quota management (15 calls/minute, 250k tokens/minute)
- ✅ Token tracking and rate limiting
- ✅ Automatic retry with exponential backoff
- ✅ Incremental progress saving with encoding fallback (cp1250/UTF-8)
- ✅ Processing status tracking (Spracovane AI, AI_Processed_Date)
- ✅ **New E-shop Output Format (147 columns)**: Complete configuration and transformation script
- ✅ Output mapping configuration with direct mappings, special transformations, and default values
- ✅ Image URL splitting (comma-separated → 8 separate columns)
- ✅ Category transformation (add prefix, change separator)
- ✅ Catalog code uppercase transformation
- ✅ Standalone transformation script (`scripts/transform_to_new_format.py`)
- ✅ AI tracking columns in output (`aiProcessed`, `aiProcessedDate`)

## In Progress
- 🔄 **Migration to New 147-Column Format (TDD Approach)**
  - Setting up test infrastructure
  - Writing tests for current implementation
  - Creating OutputTransformer module
  - Updating all components to use new format
  - Implementing XLSX support
  - Removing variant matcher (not used)

## Pending
- ⏳ Data preview functionality
- ⏳ Enhanced variant difference visualization
- ⏳ User interface for managing variant extraction rules
- ⏳ Performance optimizations for large variant groups

## Known Issues
- Some minor memory optimization needed for very large datasets
- Limited validation for optional CSV fields and their formats
- Configuration could store more processing preferences
- No confirmation when replacing existing data in export file
- Variant detection may require fine-tuning for certain product categories

