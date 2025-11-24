# AI Enhancement Grouping Logic Implementation

**Date**: 2025-11-24  
**Focus**: Differentiated AI processing for product variants vs standard products

## Objective
Implement a dual-prompt system in the AI enhancement pipeline to handle product variants differently from standard products. Variants should NOT have dimension-related text in their AI-generated descriptions to avoid duplicate content.

## Problem Statement
Product variants (e.g., "BEA BIG BAR", "BEA BIG DINING", "BEA BIG COFFEE") share the same base product but differ only in dimensions and intended use (bar height, dining height, coffee table height). When AI generates descriptions for these variants, it was including dimension information, resulting in nearly identical text that differed only in measurements. This created duplicate content issues for SEO and poor user experience.

## Solution Implemented

### 1. Created Dimension-Free Prompt (`create_system_prompt_no_dimensions()`)
- **File**: `src/ai/ai_prompts_new_format.py`
- **Approach**: Extended the base prompt with negative constraints
- **Constraints**: Explicitly forbids AI from generating:
  - Slovak dimension keywords: "výška", "šírka", "dĺžka", "hĺbka", "rozmery"
  - Measurement units: "mm", "cm", "m" (when referring to dimensions)
  - Specific numeric dimensions (e.g., "1000x500x800 mm")
- **Allows**: Other technical parameters (power, voltage, volume, capacity)

### 2. Modified AI Enhancer for Dual-Config Processing
- **File**: `src/ai/ai_enhancer_new_format.py`
- **Changes**:
  - `__init__`: Initialize two `GenerateContentConfig` objects:
    - `api_config_standard`: Uses `create_system_prompt()`
    - `api_config_no_dimensions`: Uses `create_system_prompt_no_dimensions()`
  - `process_batch_with_retry`: Accept optional `config` parameter
  - `_process_single_batch`: Pass `config` to batch processor
  - `process_dataframe`: Implement product grouping logic:
    - **Group 1 (Variants)**: Products with `pairCode` OR whose `code` is used as another product's `pairCode`
    - **Group 2 (Standard)**: All other products
    - Create separate batches for each group with appropriate config
    - Process batches in parallel with correct prompt assignment

### 3. Updated Data Merger to Preserve `pairCode`
- **File**: `src/mergers/data_merger_new_format.py`
- **Change**: Added logic to update `pairCode` from feed data if present
- **Reason**: Ensures `pairCode` survives the merge process so AI enhancer can use it for grouping

### 4. Fixed Test Failures
- **File**: `tests/test_ai_enhancer_new_format.py`
- **Issues**: Tests failing due to missing `api_config_standard` and `api_config_no_dimensions` attributes
- **Fix**: Mock `client` and `api_key` before calling `process_dataframe` in tests
- **Result**: All tests passing

### 5. Created Verification Script
- **File**: `verify_ai_grouping.py`
- **Purpose**: Confirms correct prompt assignment based on product groups
- **Method**: 
  - Creates 10 test products (5 with `pairCode`, 5 without)
  - Intercepts `process_batch_with_retry` to capture which config is used
  - Prints results showing Group 1 uses "NO DIMENSIONS" and Group 2 uses "STANDARD"
- **Result**: Verified grouping logic works correctly

## Technical Details

### Grouping Logic
```python
# In process_dataframe()
if "pairCode" in df.columns:
    pair_codes_set = set(df[df["pairCode"].notna()]["pairCode"])
    for index, row in needs_processing.iterrows():
        has_pair_code = pd.notna(row.get("pairCode")) and row.get("pairCode") != ""
        code_is_pair_code = row["code"] in pair_codes_set
        
        if has_pair_code or code_is_pair_code:
            group1_indices.append(index)  # Variants
        else:
            group2_indices.append(index)  # Standard
```

### Config Assignment
- Group 1 batches → `self.api_config_no_dimensions`
- Group 2 batches → `self.api_config_standard`

## Benefits
1. **SEO Improvement**: Variants no longer have duplicate descriptions
2. **Content Quality**: Each variant's description focuses on use case, not dimensions
3. **Maintainability**: Clear separation between variant and standard product handling
4. **Flexibility**: Easy to add more grouping rules or prompt variations in future

## Files Modified
- `src/ai/ai_prompts_new_format.py` (+35 lines)
- `src/ai/ai_enhancer_new_format.py` (~30 lines modified)
- `src/mergers/data_merger_new_format.py` (+4 lines)
- `tests/test_ai_enhancer_new_format.py` (+2 lines)
- `verify_ai_grouping.py` (new file, 127 lines)

## Validation
- ✅ All existing tests passing
- ✅ Verification script confirms correct config assignment
- ✅ Manual testing with real products successful

## Next Steps
- Monitor AI-generated content quality for variants
- Consider expanding grouping logic for other product types if needed
- Potentially add more granular negative constraints for specific categories
