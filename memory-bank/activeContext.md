# GastroPro Product Manager - Active Context

## Current Focus
- **Migration to New 147-Column E-shop Format**: Implementing TDD approach to migrate entire application to use new format for both input and output
- Writing comprehensive unit tests for current implementation before making changes
- Refactoring all components to work with new English column names
- Implementing XLSX as primary file format
- Removing variant matcher functionality (not used)

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

## Next Steps - Migration to New Format (TDD Approach)
1. **Phase 0-1**: Set up test infrastructure and write tests for current implementation
2. **Phase 2**: Create OutputTransformer module with tests
3. **Phase 3**: Update data loading with XLSX support (tests first)
4. **Phase 4**: Update XML parser to output new format (tests first)
5. **Phase 5**: Update data merging with image priority logic (tests first)
6. **Phase 6**: Update AI enhancement for new columns (tests first)
7. **Phase 7**: Update category mapper with transformation (tests first)
8. **Phase 8**: Update data pipeline integration (tests first)
9. **Phase 9**: Final validation and testing
10. **Phase 10**: Documentation and cleanup

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
- **Migration Complexity**: Updating all components to work with new 147-column format
- **Test Coverage**: Writing comprehensive tests for existing functionality before refactoring
- **Image Merging Logic**: Implementing priority-based image merging across data sources
- **Column Name Consistency**: Updating all references from Slovak to English column names
- **XLSX Integration**: Adding Excel file support throughout the application

## User Experience Considerations
- Providing clear feedback during data processing operations
- Ensuring error messages are helpful and actionable
- Maintaining consistent UI response during potentially lengthy operations

