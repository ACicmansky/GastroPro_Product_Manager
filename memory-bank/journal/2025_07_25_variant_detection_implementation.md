# 2025-07-25: Product Variant Detection and Difference Extraction

## Overview
Implemented a comprehensive product variant detection and difference extraction system that automatically identifies related product variants and extracts their differences based on configurable rules.

## Key Features Added

### 1. Product Variant Detection
- Implemented `ProductVariantMatcher` class for identifying product variants based on name similarity
- Used natural sorting to determine parent catalog numbers (lowest number in group)
- Added configurable similarity threshold (default: 0.98)
- Implemented base name extraction to handle dimensional variations
- Added support for skipping products from specific manufacturers (e.g., 'Liebherr')

### 2. Difference Extraction
- Created configuration-driven difference extraction system in `variant_extractions.json`
- Implemented extraction of:
  - Dimensions (width, length, height)
  - Power specifications
  - Volume measurements
  - Variant characteristics
- Added support for unit normalization (mm, cm, W, kW, L, etc.)

### 3. Reporting
- Generated human-readable reports of variant groups
- Created detailed difference reports showing extracted values
- Implemented timestamped report generation in `reports/` directory
- Added progress reporting for long-running operations

## Technical Implementation

### Configuration
```json
[
    {
        "category": "Nerezový nábytok/Pracovné stoly",
        "result_columns": ["Šírka", "Dĺžka", "Výška"]
    }
]
```

### Key Methods
- `extract_product_differences()`: Main method for difference extraction
- `_get_columns_to_show()`: Gets columns to extract for a category
- `_load_extraction_config()`: Loads and parses the configuration
- `generate_differences_report()`: Creates human-readable reports

## Challenges and Solutions
1. **Name Similarity**
   - Challenge: Accurately identifying variants while avoiding false positives
   - Solution: Implemented configurable similarity threshold and base name extraction

2. **Difference Extraction**
   - Challenge: Handling various unit formats and representations
   - Solution: Created robust regex patterns and unit normalization

3. **Performance**
   - Challenge: Processing large datasets efficiently
   - Solution: Optimized pandas operations and added progress reporting

## Future Improvements
- Add UI for managing extraction rules
- Implement more sophisticated variant detection algorithms
- Add support for custom extraction patterns
- Enhance reporting with visualizations

## Testing
- Tested with multiple product categories
- Verified extraction accuracy across different unit formats
- Validated report generation and formatting
