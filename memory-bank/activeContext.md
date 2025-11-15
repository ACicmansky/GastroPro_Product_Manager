# GastroPro Product Manager - Active Context

## Current Focus
- **Manual Testing of New Format GUI**: Testing complete new format pipeline with real data
- **Production Deployment Preparation**: Finalizing configuration and documentation
- **GUI Integration**: New simplified GUI ready for production use

## Recent Changes
- **CategoryMappingManager**: Implemented centralized category mapping management with in-memory caching. Eliminates duplicate disk I/O, provides immediate availability of new mappings during processing, and ensures no repeated prompts for same category in single run
- **Interactive Category Mapping with Auto-Save & Smart Suggestions**: Implemented real-time category mapping dialog that pauses processing when unmapped categories are encountered during XML parsing and web scraping. Features include: on-the-fly user input, automatic saving to `categories.json` with thread-safe operations, smart suggestions using rapidfuzz + hierarchical matching showing top 5 similar categories with confidence percentages, and product name context display
- **Major Codebase Refactoring**: The entire application was refactored into a modular `src` package structure to improve maintainability and adhere to SOLID principles. This involved separating the GUI, core business logic, services, and utilities into distinct modules.
- Enhanced Topchladenie.sk data acquisition with dual approach:
  - Live scraping with multi-threaded parallel processing
  - Alternative offline CSV loading with dedicated drop area
- Fixed CSV loading to properly handle semicolon (;) separators for Topchladenie CSV files
- Implemented enhanced data cleaning by filtering out products with empty catalog numbers
- Added detailed statistics reporting in export success dialog
- Enhanced category mapping system with unified approach for XML feeds and CSV input
- Implemented optional user-controlled category mapping at export time
- Added UI checkbox to control CSV category mapping behavior
- Restructured category mapping to use a simpler universal JSON array format
- Created centralized mapping functions to ensure consistent category standardization
- Successfully implemented XML feed fetching and parsing for multiple vendors
- Added specialized processing for forgastro feed HTML content extraction
- Implemented gastromarket feed text processing for bullet points and categories
- Modified merge operation to use outer join to include all products
- Added automatic "Viditelný" field setting to "1" for all feed products
- Enhanced HTML parsing with BeautifulSoup to extract tab content
- Improved special character handling and text formatting
- Introduced AI-based SEO metadata generation (SEO titulka, SEO popis, SEO kľúčové slová) with web search grounding to enrich missing context

## Completed Migration (November 2025)
✅ **All 8 Phases Complete - TDD Approach Success**
1. ✅ **Phase 0-1**: Test infrastructure + current implementation tests (110 tests)
2. ✅ **Phase 2**: OutputTransformer module (19 tests)
3. ✅ **Phase 3**: XLSX/CSV loading with DataLoaderFactory (15 tests)
4. ✅ **Phase 4**: XML parser for new format (18 tests)
5. ✅ **Phase 5**: Data merging with image priority (11 tests)
6. ✅ **Phase 6**: AI enhancement for new format (15 tests)
7. ✅ **Phase 7**: Category mapper with transformation (18 tests)
8. ✅ **Phase 8**: Pipeline integration (15 tests)
**Total: 158 tests passing, 0 failures**

## Next Steps
1. Manual testing with real XML feeds
2. Configure production XML URLs
3. Test AI enhancement with real API
4. Validate output with e-shop import
5. Deploy to production

## Active Decisions
- **Migration Strategy**: TDD approach - write tests first, then implement
- **Format Support**: New 147-column format only (no backward compatibility)
- **File Format**: XLSX as primary, CSV as fallback
- **Image Merging**: Use source with most images available
- **Default Values**: Apply at end of pipeline if cells are empty
- **Breaking Changes**: Acceptable - clean migration
- **Variant Matcher**: Skip updates (feature not used)
- **Code Uppercase**: Apply on load and merge for consistency
- **Category Transformation**: Add "Tovary a kategórie > " prefix and change "/" to " > "
- Using Pandas DataFrames as the core data structure for manipulation
- Providing detailed statistics on data source contributions in export summary

## Current Challenges
- **Production Configuration**: Setting up real XML feed URLs
- **AI API Integration**: Configuring and testing AI enhancement with production API
- **Manual Testing**: Validating all features with real data
- **E-shop Import**: Ensuring output format is compatible with e-shop system

## User Experience Considerations
- Providing clear feedback during data processing operations
- Ensuring error messages are helpful and actionable
- Maintaining consistent UI response during potentially lengthy operations

