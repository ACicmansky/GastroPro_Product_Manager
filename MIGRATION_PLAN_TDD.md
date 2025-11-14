# Migration Plan: TDD Approach - New Output Format

## Overview
Migrate application to use new 147-column format for both input and output, using Test-Driven Development approach.

## Key Decisions
- ✅ Support only new format (no backward compatibility)
- ✅ XLSX as primary format (CSV as fallback)
- ✅ Image merging: use source with most images
- ✅ Default values: apply at end if empty
- ✅ Breaking changes acceptable
- ✅ Variant matcher: SKIP (not used)

---

## **Phase 0: Test Infrastructure Setup** ⭐ START HERE

### 0.1 Create Test Structure
```
tests/
├── __init__.py
├── conftest.py                    # Pytest fixtures
├── test_data/                     # Sample data files
│   ├── sample_old_format.csv
│   ├── sample_new_format.xlsx
│   ├── sample_xml_gastromarket.xml
│   └── sample_xml_forgastro.xml
├── test_output_transformer.py    # Transformation tests
├── test_data_loader.py           # Loading tests
├── test_xml_parser.py            # XML parsing tests
├── test_data_merging.py          # Merge logic tests
├── test_ai_enhancer.py           # AI enhancement tests
├── test_category_mapper.py       # Category mapping tests
└── test_integration.py           # Full pipeline tests
```

**Action Items:**
- [ ] Create test directory structure
- [ ] Set up pytest configuration
- [ ] Create sample test data files
- [ ] Create conftest.py with fixtures

---

## **Phase 1: Test Current Implementation** ⭐ CRITICAL

### 1.1 Test Data Loading (Current)
**File:** `tests/test_data_loader.py`

```python
import pytest
import pandas as pd
from src.utils.config_loader import load_config

class TestCurrentDataLoading:
    """Test current CSV loading functionality."""
    
    def test_load_csv_old_format_cp1250(self):
        """Test loading old format CSV with cp1250 encoding."""
        # Test current implementation
        pass
    
    def test_load_csv_old_format_utf8(self):
        """Test loading old format CSV with UTF-8 fallback."""
        pass
    
    def test_csv_columns_present(self):
        """Verify all expected columns are present."""
        pass
    
    def test_empty_catalog_number_filtering(self):
        """Test that products with empty Kat. číslo are filtered."""
        pass
```

**Action Items:**
- [ ] Write tests for current CSV loading
- [ ] Test encoding fallback (cp1250 → UTF-8)
- [ ] Test column validation
- [ ] Test empty catalog filtering
- [ ] **RUN TESTS - ALL MUST PASS**

---

### 1.2 Test XML Parsing (Current)
**File:** `tests/test_xml_parser.py`

```python
class TestCurrentXMLParsing:
    """Test current XML feed parsing."""
    
    def test_parse_gastromarket_feed(self):
        """Test parsing GastroMarket XML feed."""
        pass
    
    def test_parse_forgastro_feed(self):
        """Test parsing ForGastro XML feed."""
        pass
    
    def test_xml_column_mapping(self):
        """Test XML to internal column mapping."""
        pass
    
    def test_xml_special_characters(self):
        """Test handling of special characters in XML."""
        pass
    
    def test_xml_empty_fields(self):
        """Test handling of missing/empty XML fields."""
        pass
```

**Action Items:**
- [ ] Create sample XML files for testing
- [ ] Write tests for gastromarket feed
- [ ] Write tests for forgastro feed
- [ ] Test column mapping
- [ ] Test edge cases
- [ ] **RUN TESTS - ALL MUST PASS**

---

### 1.3 Test Data Merging (Current)
**File:** `tests/test_data_merging.py`

```python
class TestCurrentDataMerging:
    """Test current data merging logic."""
    
    def test_merge_main_with_feed(self):
        """Test merging main CSV with feed data."""
        pass
    
    def test_price_update_from_feed(self):
        """Test that feed prices update main prices."""
        pass
    
    def test_add_new_products_from_feed(self):
        """Test adding new products from feed."""
        pass
    
    def test_preserve_main_data(self):
        """Test that main data is preserved during merge."""
        pass
    
    def test_merge_multiple_feeds(self):
        """Test merging data from multiple feeds."""
        pass
```

**Action Items:**
- [ ] Write tests for merge_dataframes()
- [ ] Test price updates
- [ ] Test new product addition
- [ ] Test data preservation
- [ ] Test multiple feed merging
- [ ] **RUN TESTS - ALL MUST PASS**

---

### 1.4 Test AI Enhancement (Current)
**File:** `tests/test_ai_enhancer.py`

```python
class TestCurrentAIEnhancement:
    """Test current AI enhancement functionality."""
    
    @pytest.mark.skipif(not os.getenv('GOOGLE_API_KEY'), 
                       reason="API key not available")
    def test_ai_enhancement_single_product(self):
        """Test AI enhancement for single product."""
        pass
    
    def test_ai_tracking_columns(self):
        """Test that Spracovane AI and AI_Processed_Date are updated."""
        pass
    
    def test_fuzzy_matching_product_update(self):
        """Test fuzzy matching to update correct product."""
        pass
    
    def test_skip_already_processed(self):
        """Test that already processed products are skipped."""
        pass
    
    def test_incremental_saving(self):
        """Test incremental progress saving."""
        pass
```

**Action Items:**
- [ ] Write tests for AI enhancement (mock API calls)
- [ ] Test tracking column updates
- [ ] Test fuzzy matching logic
- [ ] Test skip logic
- [ ] Test incremental saving
- [ ] **RUN TESTS - ALL MUST PASS**

---

### 1.5 Test Category Mapping (Current)
**File:** `tests/test_category_mapper.py`

```python
class TestCurrentCategoryMapping:
    """Test current category mapping functionality."""
    
    def test_map_single_category(self):
        """Test mapping a single category."""
        pass
    
    def test_map_dataframe_categories(self):
        """Test mapping categories in DataFrame."""
        pass
    
    def test_category_normalization(self):
        """Test category string normalization."""
        pass
    
    def test_unmapped_category_callback(self):
        """Test interactive callback for unmapped categories."""
        pass
    
    def test_category_mapping_manager(self):
        """Test CategoryMappingManager functionality."""
        pass
```

**Action Items:**
- [ ] Write tests for map_category()
- [ ] Write tests for map_dataframe_categories()
- [ ] Test normalization logic
- [ ] Test interactive callback
- [ ] Test CategoryMappingManager
- [ ] **RUN TESTS - ALL MUST PASS**

---

### 1.6 Test Data Pipeline (Current)
**File:** `tests/test_integration.py`

```python
class TestCurrentDataPipeline:
    """Test current end-to-end data pipeline."""
    
    def test_full_pipeline_without_ai(self):
        """Test complete pipeline without AI enhancement."""
        pass
    
    def test_pipeline_with_category_filtering(self):
        """Test pipeline with category filtering."""
        pass
    
    def test_pipeline_with_feeds(self):
        """Test pipeline with XML feed processing."""
        pass
    
    def test_output_column_order(self):
        """Test that output has correct column order."""
        pass
    
    def test_output_encoding(self):
        """Test output file encoding."""
        pass
```

**Action Items:**
- [ ] Write integration tests for full pipeline
- [ ] Test with different option combinations
- [ ] Test output validation
- [ ] **RUN TESTS - ALL MUST PASS**

---

## **Phase 2: Create OutputTransformer Module with Tests**

### 2.1 Write Tests FIRST
**File:** `tests/test_output_transformer.py`

```python
class TestOutputTransformer:
    """Test OutputTransformer functionality."""
    
    def test_transform_old_to_new_format(self):
        """Test complete transformation from old to new format."""
        # Load old format data
        # Transform to new format
        # Assert 147 columns present
        # Assert correct column order
        pass
    
    def test_direct_mappings(self):
        """Test direct column mappings."""
        # Test each mapping from config
        pass
    
    def test_image_splitting(self):
        """Test splitting comma-separated images."""
        # Test: "img1.jpg,img2.jpg,img3.jpg" → 8 columns
        # Test: single image
        # Test: empty images
        # Test: more than 8 images (should truncate)
        pass
    
    def test_category_transformation(self):
        """Test category transformation."""
        # Test: "Vitríny/Chladiace vitríny" → 
        #       "Tovary a kategórie > Vitríny > Chladiace vitríny"
        # Test: both defaultCategory and categoryText
        pass
    
    def test_code_uppercase(self):
        """Test catalog code uppercase transformation."""
        # Test: "roller grill_rd60f" → "ROLLER GRILL_RD60F"
        pass
    
    def test_apply_defaults(self):
        """Test applying default values."""
        # Test: defaults applied only to empty cells
        # Test: existing values not overwritten
        pass
    
    def test_ensure_all_columns(self):
        """Test that all 147 columns are present."""
        # Test: missing columns added as empty
        # Test: correct column order
        pass
    
    def test_merge_images_priority(self):
        """Test image merging with priority logic."""
        # Test: use source with most images
        pass
```

**Action Items:**
- [ ] Write all transformer tests FIRST
- [ ] **TESTS WILL FAIL** (no implementation yet)
- [ ] Document expected behavior in tests

---

### 2.2 Implement OutputTransformer
**File:** `src/utils/output_transformer.py`

```python
class OutputTransformer:
    """Transforms data to new 147-column format."""
    
    def __init__(self, config: dict):
        self.config = config
        self.output_mapping = config.get('output_mapping', {})
        self.mappings = self.output_mapping.get('mappings', {})
        self.special_mappings = self.output_mapping.get('special_mappings', {})
        self.default_values = self.output_mapping.get('default_values', {})
        self.new_columns = config.get('new_output_columns', [])
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform DataFrame to new format."""
        # Implementation based on script
        pass
    
    def apply_direct_mappings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply direct column mappings."""
        pass
    
    def split_images(self, df: pd.DataFrame) -> pd.DataFrame:
        """Split comma-separated images into 8 columns."""
        pass
    
    def transform_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform category paths."""
        pass
    
    def uppercase_codes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert codes to uppercase."""
        pass
    
    def apply_defaults(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply default values to empty cells."""
        pass
    
    def ensure_all_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure all 147 columns present in correct order."""
        pass
    
    @staticmethod
    def merge_images_by_priority(main_images: dict, 
                                 feed_images: dict) -> dict:
        """Merge images using priority logic (most images wins)."""
        pass
```

**Action Items:**
- [ ] Extract logic from transform_to_new_format.py script
- [ ] Implement each method
- [ ] Add comprehensive docstrings
- [ ] **RUN TESTS - ALL MUST PASS**

---

## **Phase 3: Update Data Loading with Tests**

### 3.1 Write Tests FIRST
**File:** `tests/test_data_loader.py` (add new tests)

```python
class TestNewFormatDataLoading:
    """Test new format data loading."""
    
    def test_load_xlsx_new_format(self):
        """Test loading XLSX in new format."""
        pass
    
    def test_load_csv_new_format(self):
        """Test loading CSV in new format."""
        pass
    
    def test_validate_new_format(self):
        """Test format validation (must have 'code' column)."""
        pass
    
    def test_ensure_all_columns_on_load(self):
        """Test that missing columns are added on load."""
        pass
    
    def test_uppercase_codes_on_load(self):
        """Test that codes are uppercased on load."""
        pass
    
    def test_reject_old_format(self):
        """Test that old format is rejected."""
        pass
```

**Action Items:**
- [ ] Write tests for new loader FIRST
- [ ] **TESTS WILL FAIL** (no implementation yet)

---

### 3.2 Implement New Data Loader
**File:** `src/utils/data_loader.py` (create new)

```python
def load_product_data(filepath: str, config: dict) -> pd.DataFrame:
    """Load product data in new 147-column format."""
    pass

def detect_file_format(df: pd.DataFrame) -> str:
    """Detect if DataFrame is old or new format."""
    pass
```

**Action Items:**
- [ ] Implement load_product_data()
- [ ] Add XLSX support (openpyxl)
- [ ] Add format validation
- [ ] Uppercase codes on load
- [ ] **RUN TESTS - ALL MUST PASS**

---

### 3.3 Update Main Window Loading
**File:** `src/gui/main_window.py`

**Action Items:**
- [ ] Update load_csv_file() to use new loader
- [ ] Update file dialog for XLSX
- [ ] Update drag & drop for XLSX
- [ ] **RUN INTEGRATION TESTS**

---

## **Phase 4: Update XML Parser with Tests**

### 4.1 Write Tests FIRST
**File:** `tests/test_xml_parser.py` (add new tests)

```python
class TestNewFormatXMLParsing:
    """Test XML parsing to new format."""
    
    def test_parse_to_new_format_gastromarket(self):
        """Test parsing GastroMarket to new format."""
        # Assert output has 'code', 'name', etc.
        # Assert codes are uppercase
        # Assert categories transformed
        pass
    
    def test_parse_to_new_format_forgastro(self):
        """Test parsing ForGastro to new format."""
        pass
    
    def test_image_splitting_from_xml(self):
        """Test image URL splitting from XML."""
        pass
    
    def test_apply_defaults_to_feed(self):
        """Test defaults applied to feed data."""
        pass
    
    def test_all_147_columns_in_feed(self):
        """Test that feed output has all 147 columns."""
        pass
```

**Action Items:**
- [ ] Write tests for new XML parsing FIRST
- [ ] **TESTS WILL FAIL** (no implementation yet)

---

### 4.2 Update XML Parser Implementation
**File:** `src/services/xml_parser.py`

**Action Items:**
- [ ] Add _map_to_new_format() method
- [ ] Add _apply_feed_transformations() method
- [ ] Update parse_feed() to use new methods
- [ ] **RUN TESTS - ALL MUST PASS**

---

## **Phase 5: Update Data Merging with Tests**

### 5.1 Write Tests FIRST
**File:** `tests/test_data_merging.py` (add new tests)

```python
class TestNewFormatDataMerging:
    """Test merging in new format."""
    
    def test_merge_on_code_column(self):
        """Test merging on 'code' column (uppercase)."""
        pass
    
    def test_image_merge_priority(self):
        """Test image merging with priority logic."""
        # Main has 2 images, feed has 5 → use feed
        # Main has 5 images, feed has 2 → use main
        pass
    
    def test_preserve_ai_tracking(self):
        """Test that AI tracking is preserved from main."""
        pass
    
    def test_update_prices_from_feed(self):
        """Test price updates in new format."""
        pass
    
    def test_add_new_products_new_format(self):
        """Test adding new products in new format."""
        pass
```

**Action Items:**
- [ ] Write tests for new merge logic FIRST
- [ ] **TESTS WILL FAIL** (no implementation yet)

---

### 5.2 Implement New Merge Logic
**File:** `src/utils/helpers.py`

**Action Items:**
- [ ] Create merge_dataframes_new_format()
- [ ] Implement _merge_images_for_product()
- [ ] Handle uppercase code matching
- [ ] **RUN TESTS - ALL MUST PASS**

---

## **Phase 6: Update AI Enhancement with Tests**

### 6.1 Write Tests FIRST
**File:** `tests/test_ai_enhancer.py` (add new tests)

```python
class TestNewFormatAIEnhancement:
    """Test AI enhancement with new format."""
    
    def test_ai_enhancement_new_columns(self):
        """Test AI updates correct new format columns."""
        # shortDescription, description, seoTitle, metaDescription
        pass
    
    def test_fuzzy_matching_on_code(self):
        """Test fuzzy matching uses 'code' column."""
        pass
    
    def test_ai_tracking_new_format(self):
        """Test aiProcessed and aiProcessedDate updates."""
        pass
```

**Action Items:**
- [ ] Write tests for new AI enhancement FIRST
- [ ] **TESTS WILL FAIL** (no implementation yet)

---

### 6.2 Update AI Enhancer Implementation
**File:** `src/services/ai_enhancer.py`

**Action Items:**
- [ ] Update column references to new names
- [ ] Update fuzzy matching to use 'code'
- [ ] Update tracking columns
- [ ] **RUN TESTS - ALL MUST PASS**

---

## **Phase 7: Update Category Mapper with Tests**

### 7.1 Write Tests FIRST
**File:** `tests/test_category_mapper.py` (add new tests)

```python
class TestNewFormatCategoryMapping:
    """Test category mapping with new format."""
    
    def test_map_with_transformation(self):
        """Test mapping applies transformation."""
        # Input: "Vitríny/Chladiace vitríny"
        # Output: "Tovary a kategórie > Vitríny > Chladiace vitríny"
        pass
    
    def test_update_both_category_columns(self):
        """Test both defaultCategory and categoryText updated."""
        pass
    
    def test_category_mapper_new_columns(self):
        """Test map_dataframe_categories with new columns."""
        pass
```

**Action Items:**
- [ ] Write tests for new category mapping FIRST
- [ ] **TESTS WILL FAIL** (no implementation yet)

---

### 7.2 Update Category Mapper Implementation
**File:** `src/utils/category_mapper.py`

**Action Items:**
- [ ] Add transform_category_path() function
- [ ] Update map_dataframe_categories() for new columns
- [ ] Apply transformation after mapping
- [ ] **RUN TESTS - ALL MUST PASS**

---

## **Phase 8: Update Data Pipeline with Tests**

### 8.1 Write Tests FIRST
**File:** `tests/test_integration.py` (add new tests)

```python
class TestNewFormatDataPipeline:
    """Test full pipeline with new format."""
    
    def test_full_pipeline_new_format(self):
        """Test complete pipeline with new format."""
        # Load new format → process → output new format
        pass
    
    def test_pipeline_output_147_columns(self):
        """Test output has all 147 columns."""
        pass
    
    def test_pipeline_column_order(self):
        """Test output column order matches config."""
        pass
    
    def test_pipeline_defaults_applied(self):
        """Test defaults applied at end."""
        pass
```

**Action Items:**
- [ ] Write integration tests FIRST
- [ ] **TESTS WILL FAIL** (no implementation yet)

---

### 8.2 Update Data Pipeline Implementation
**File:** `src/core/data_pipeline.py`

**Action Items:**
- [ ] Update all column references
- [ ] Use new merge function
- [ ] Apply defaults at end
- [ ] Ensure column order
- [ ] **RUN TESTS - ALL MUST PASS**

---

### 8.3 Update Main Window Export
**File:** `src/gui/main_window.py`

**Action Items:**
- [ ] Change default to XLSX
- [ ] Add XLSX export support
- [ ] Update statistics display
- [ ] **RUN INTEGRATION TESTS**

---

## **Phase 9: Final Validation**

### 9.1 Run All Tests
```bash
pytest tests/ -v --cov=src --cov-report=html
```

**Action Items:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Code coverage > 80%
- [ ] No regressions

---

### 9.2 Manual Testing
- [ ] Load transformed XLSX file
- [ ] Process with all options enabled
- [ ] Verify output has 147 columns
- [ ] Verify data integrity
- [ ] Verify image handling
- [ ] Verify category transformation
- [ ] Test with real production data

---

### 9.3 Performance Testing
- [ ] Test with large datasets (1000+ products)
- [ ] Measure memory usage
- [ ] Measure processing time
- [ ] Compare with old implementation

---

## **Phase 10: Documentation & Cleanup**

### 10.1 Update Documentation
- [ ] Update README
- [ ] Update memory bank
- [ ] Document migration process
- [ ] Update user guide

### 10.2 Update Dependencies
```
openpyxl>=3.1.0
pytest>=7.0.0
pytest-cov>=4.0.0
```

### 10.3 Clean Up
- [ ] Remove old format code
- [ ] Update comments
- [ ] Remove unused imports
- [ ] Update config.json comments

---

## **Test Execution Strategy**

### Daily Workflow
1. Write tests for next feature
2. Run tests (should fail)
3. Implement feature
4. Run tests (should pass)
5. Refactor if needed
6. Commit when all tests pass

### Continuous Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_output_transformer.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run only failed tests
pytest --lf

# Run in watch mode (with pytest-watch)
ptw
```

---

## **Success Criteria**

✅ All existing tests pass (Phase 1)
✅ All new tests pass (Phases 2-8)
✅ Code coverage > 80%
✅ No regressions in functionality
✅ Load XLSX with 147 columns
✅ Process feeds → new format
✅ Merge with image priority
✅ AI enhancement works
✅ Category mapping works
✅ Export XLSX successfully
✅ Data integrity maintained

---

## **Risk Mitigation**

1. **Test First:** Write tests before implementation
2. **Incremental:** One phase at a time
3. **Validation:** Run tests after each change
4. **Backup:** Git branches for rollback
5. **Documentation:** Update as we go

---

## **Timeline Estimate**

- **Phase 0-1:** 2-3 days (test infrastructure + current tests)
- **Phase 2:** 1-2 days (OutputTransformer)
- **Phase 3:** 1 day (Data loading)
- **Phase 4:** 1-2 days (XML parser)
- **Phase 5:** 1-2 days (Data merging)
- **Phase 6:** 1 day (AI enhancement)
- **Phase 7:** 1 day (Category mapper)
- **Phase 8:** 2-3 days (Pipeline integration)
- **Phase 9:** 2-3 days (Validation & testing)
- **Phase 10:** 1 day (Documentation)

**Total:** ~2-3 weeks

---

## **Next Immediate Steps**

1. ✅ Create test directory structure
2. ✅ Set up pytest configuration
3. ✅ Create sample test data
4. ✅ Write tests for current CSV loading
5. ✅ Run tests - ensure all pass
6. ✅ Proceed to Phase 2

**Start with Phase 0 and 1 - get all current tests passing first!**
