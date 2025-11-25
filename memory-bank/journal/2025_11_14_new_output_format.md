# New Output Format Implementation - November 14, 2025

## Overview
Implemented comprehensive configuration and transformation script for new 138-column e-shop output format.

## Changes Made

### 1. Configuration Updates (`config.json`)

#### Output Mapping Section (NEW)
Added complete `output_mapping` configuration with four subsections:

**a) Direct Mappings (17 mappings)**
- Maps internal Slovak column names to English e-shop format
- Examples:
  - `Kat. číslo` → `code`
  - `Názov tovaru` → `name`
  - `Bežná cena` → `price`
  - `Spracovane AI` → `aiProcessed`
  - `AI_Processed_Date` → `aiProcessedDate`

**b) Special Mappings (3 transformations)**
1. **Category Transformation**:
   - Source: `Hlavna kategória`
   - Targets: `defaultCategory`, `categoryText`
   - Transform: Add prefix "Tovary a kategórie > " and replace "/" with " > "
   - Example: `"Vitríny/Chladiace vitríny"` → `"Tovary a kategórie > Vitríny > Chladiace vitríny"`

2. **Code Uppercase**:
   - Source: `Kat. číslo`
   - Target: `code`
   - Transform: Convert to uppercase
   - Example: `"Roller Grill_RD60F"` → `"ROLLER GRILL_RD60F"`

3. **Image Splitting**:
   - Source: `Obrázky` (comma-separated URLs)
   - Targets: `image`, `image2`, `image3`, `image4`, `image5`, `image6`, `image7`
   - Transform: Split by comma into 8 separate columns
   - Example: `"img1.jpg,img2.jpg,img3.jpg"` → separate columns

**c) Default Values (32 values)**
Applied only when column is empty or missing:
- `currency`: "EUR"
- `includingVat`: "0"
- `percentVat`: "23"
- `itemType`: "product"
- `productVisibility`: "visible"
- `firmyCz`: "1" (B2B flag)
- Various discount/payment flags
- Marketplace visibility settings

**d) Drop Columns**
- `SEO kľúčové slová` - not needed in new format

#### New Output Columns (138 total)
- Added complete list of all required e-shop columns
- Includes AI tracking: `aiProcessed`, `aiProcessedDate`
- Multiple image columns: `image`, `image2-7`
- Variant dimensions: `variant:Šírka (mm)`, `variant:Dĺžka (mm)`, `variant:Hĺbka (mm)`

### 2. Transformation Script

**File**: `scripts/transform_to_new_format.py`

**Purpose**: Convert old CSV format to new 138-column XLSX format

**Key Features**:
1. **Configuration-Driven**: Reads all mappings from `config.json`
2. **Direct Mappings**: Applies 1:1 column mappings
3. **Image Splitting**: Splits comma-separated image URLs into 8 columns
4. **Category Transformation**: Adds prefix and changes separators
5. **Code Uppercase**: Converts catalog codes to uppercase
6. **Default Values**: Applies defaults only to empty cells
7. **Column Completeness**: Ensures all 138 columns present
8. **Progress Logging**: Detailed console output of transformation steps

**Input**: CSV file (semicolon-separated, cp1250/UTF-8 encoding)
**Output**: XLSX file with same name

**Usage**:
```python
# Update INPUT_FILE variable in script
INPUT_FILE = r"c:\Source\Python\GastroPro_Product_Manager\data\sample_old_format.csv"

# Run script
python scripts/transform_to_new_format.py
```

### 3. Sample Data

**File**: `data/sample_old_format.csv`

Created test data with 3 products demonstrating:
- Multiple images (3 URLs in one product)
- Single image
- Variant dimensions
- AI tracking data
- Various product types

### 4. Documentation

**File**: `scripts/README.md`
- Usage instructions
- Example transformations
- Requirements and notes

## Key Design Decisions

### 1. No Formatting
- **Decision**: Save raw data without formatting
- **Rationale**: E-shop system handles display formatting
- **Example**: Save `2801.94` not `"2 801,94"`

### 2. Default Values Philosophy
- **Decision**: Apply only when empty/missing
- **Rationale**: Future-proof - allows data to be overwritten
- **Implementation**: Check for NaN, empty string, or "nan" before applying

### 3. Image Handling
- **Decision**: Split comma-separated URLs into 8 columns
- **Rationale**: E-shop requires separate columns for each image
- **Limit**: Maximum 8 images per product

### 4. Category Transformation
- **Decision**: Add prefix and change separator
- **Rationale**: E-shop requires specific category format
- **Applied to**: Both `defaultCategory` and `categoryText`

### 5. Visibility Handling
- **Decision**: Don't map `Viditeľný` to `variantVisibility`
- **Rationale**: `variantVisibility` is for e-shop variant display settings, not product visibility
- **Alternative**: Use `productVisibility` static value

### 6. SEO Keywords
- **Decision**: Drop `SEO kľúčové slová` column
- **Rationale**: New e-shop format doesn't require it

### 7. Catalog Code Transformation
- **Decision**: Convert to uppercase
- **Rationale**: E-shop standard format
- **Example**: `"roller grill_rd60f"` → `"ROLLER GRILL_RD60F"`

## Technical Implementation

### OutputTransformer Class Structure
```python
class OutputTransformer:
    def __init__(self, config)
    def transform(self, df) -> pd.DataFrame
    def _apply_special_mappings(self, input_df, output_df)
    def _apply_default_values(self, df)
```

### Transformation Pipeline
1. Load configuration from `config.json`
2. Load old format CSV
3. Apply direct mappings
4. Split images into multiple columns
5. Apply category transformation
6. Apply code uppercase
7. Ensure all 138 columns exist
8. Apply default values to empty cells
9. Reorder columns to match `new_output_columns`
10. Save to XLSX

### Image Splitting Logic
```python
def split_images(image_string):
    # Split by comma, strip whitespace
    images = [img.strip() for img in str(image_string).split(',') if img.strip()]
    # Limit to 8 images
    return images[:8]
```

## Testing Results

✅ Script successfully transforms sample data
✅ All 138 columns present in output
✅ Image splitting works correctly (3 images → 3 columns)
✅ Category transformation applied correctly
✅ Catalog codes uppercased
✅ Default values applied only to empty cells
✅ AI tracking columns preserved

## Configuration Philosophy

**Keep it Simple**:
- No complex formatting rules
- Save raw data
- Let e-shop handle display
- Defaults only when empty
- All columns present (even if empty)
- Future-proof design

**Flexibility**:
- New format can be used as input later
- Default values can be overwritten
- Any column can have data in future
- Configuration-driven transformations

## Files Created/Modified

**Created**:
- `scripts/transform_to_new_format.py` - Main transformation script
- `scripts/README.md` - Documentation
- `data/sample_old_format.csv` - Test data

**Modified**:
- `config.json` - Added `output_mapping` section with all mappings

**Temporary (deleted after extracting to memory bank)**:
- `CONFIG_SUMMARY.md`
- `IMPLEMENTATION_GUIDE.md`
- `MAPPING_ANALYSIS.md`

## Next Steps

### Future Implementation (Not Yet Done)
1. Create `src/utils/output_transformer.py` module
2. Integrate transformation into `src/core/data_pipeline.py`
3. Update `src/gui/main_window.py` export logic
4. Add UI option to toggle between old/new format
5. Comprehensive testing with real data

### Pending Decisions
- None - all questions resolved with user

## Notes

- Script is standalone and can be used independently
- Configuration is complete and ready for integration
- Sample data validates all transformation rules
- Documentation is comprehensive
- Memory bank updated with key information
