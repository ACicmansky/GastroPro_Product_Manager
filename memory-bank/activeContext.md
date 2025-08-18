# GastroPro Product Manager - Active Context

## Current Focus
- Standardizing category mapping across all data sources
- Optimizing product data processing from multiple feed sources
- Fine-tuning specialized data extraction and formatting
- Ensuring proper data merging and export functionality
- Implementing user-controlled features for flexible workflow
- Enhancing data quality with an LLM agent to generate B2B short/long descriptions and SEO metadata using web search; iterating on prompt engineering and parallel batch execution

## Recent Changes
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

## Next Steps
1. Implement category selection functionality from local CSV
2. Add support for additional feed sources if needed
3. Improve error handling and user feedback
4. Implement data preview functionality
5. Optimize performance for large datasets

## Active Decisions
- Filtering out products with empty catalog numbers before merging to ensure data integrity
- Implementing mutual exclusivity between live scraping and CSV loading for Topchladenie data
- Using semicolon (;) as the default CSV delimiter based on common European CSV format
- Maintaining UTF-8 as the default encoding for all file operations with cp1250 fallback for export
- Using feed name to trigger specialized content processing routines
- Using outer join to ensure all products are included in the final output
- Setting "Viditelný" field to "1" for all imported products
- Using Pandas DataFrames as the core data structure for manipulation
- Providing detailed statistics on data source contributions in export summary

## Current Challenges
- Handling complex HTML in product descriptions from various feeds
- Managing special characters and formatting across different feeds
- Optimizing performance for large datasets
- Ensuring consistent behavior across multiple feed formats
- Implementing robust data validation to prevent errors in data processing

## User Experience Considerations
- Providing clear feedback during data processing operations
- Ensuring error messages are helpful and actionable
- Maintaining consistent UI response during potentially lengthy operations

