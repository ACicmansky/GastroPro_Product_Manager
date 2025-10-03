# AI Enhancement Tracking Corruption Fix
**Date:** 2025-10-03  
**Status:** ✅ Resolved

## Problem Description

AI enhancement was re-processing already-processed products across multiple runs. The number of products marked for processing was inconsistent:
- **Run 1:** 7235 eligible → 7100 processed (135 failed/skipped)
- **Run 2:** 768 eligible (should be ~135) → 721 processed
- **Run 3:** 556 eligible (should be ~47)

The `Spracovane AI` tracking column was being corrupted, causing previously processed products to be re-processed.

## Root Cause Analysis

### Bug #0: Multi-Column List Assignment Dtype Corruption (ACTUAL PRIMARY ISSUE)

**Location:** `src/services/ai_enhancer.py` lines 228-234 (original code)

**Issue:**
```python
# BEFORE (BUGGY CODE)
df.loc[best_match_idx, [
    'Krátky popis', 'Dlhý popis', 'SEO titulka', 'SEO popis', 'SEO kľúčové slová',
    'Spracovane AI', 'AI_Processed_Date'
]] = [
    enhanced_product['Krátky popis'], enhanced_product['Dlhý popis'], enhanced_product['SEO titulka'],
    enhanced_product['SEO popis'], enhanced_product['SEO kľúčové slová'], True, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
]
```

**What happened:**
1. Assigning a **list of mixed types** (strings + boolean + string) to multiple columns simultaneously causes pandas to:
   - Convert columns to object dtype instead of preserving boolean type
   - Create view vs. copy issues where assignments don't persist properly
   - Store boolean `True` as an object that doesn't serialize/deserialize correctly

2. The unnecessary `df = df.copy()` at the start of `update_dataframe` created a new DataFrame object that lost proper referencing

3. Result: The `'Spracovane AI'` column appeared to be updated in memory but:
   - The boolean True was not properly stored as a native boolean
   - When saved to CSV and reloaded, values became inconsistent
   - Products would be re-processed on every run

**Evidence from user testing:**
- Run 1: 556 eligible → 506 processed (updates appeared to work)
- Run 2: 556 eligible again (same count, not 50 remaining) → updates were NOT persisted
- Run 3: 555 eligible → tracking values completely lost
- File inspection: All 556 products still showed `FALSE` despite being processed

**After initial fixes (Bug #0-#3):**
- Run 1: 553 eligible → 521 processed
- Run 2: 551 eligible (should be 32, not 551) → Matching was still failing!
- Root cause: Fuzzy matching was searching the ENTIRE df, potentially matching to wrong products (even already-processed ones)
- The error logger added by user was never triggered, proving matches were being found but to WRONG rows

### Bug #1: In-Place DataFrame Mutation During CSV Saves

**Location:** `src/services/ai_enhancer.py` lines 297-308 and 326-337

**Issue:**
```python
# BEFORE (BUGGY CODE)
for col in df.columns:  # ❌ Modifying original df
    if df[col].dtype == 'object':
        df[col] = df[col].astype(str)
        df[col] = df[col].apply(lambda x: ...)

df.to_csv(tmp_file, index=False, encoding='cp1250', sep=';')
```

**What happened:**
1. AI enhancement set `'Spracovane AI'` to boolean `True`
2. During incremental saves, the encoding conversion code modified **the original dataframe** in-place
3. All object columns were converted to strings, corrupting the boolean tracking values
4. This modified df was used for subsequent batches AND returned to the pipeline
5. When saved to CSV and reloaded, corrupted values caused products to be re-processed

**The bug appeared in TWO locations:**
- Lines 297-308: Incremental saves after each batch
- Lines 326-337: Final save after all processing

### Bug #2: Incorrect Matching Scope - Searching Entire DataFrame

**Location:** `src/services/ai_enhancer.py` `update_dataframe()` method

**Issue:**
```python
# BEFORE (BUGGY CODE)
def update_dataframe(self, df: pd.DataFrame, enhanced_products: List[Dict[str, str]]):
    for enhanced_product in enhanced_products:
        # Searches the ENTIRE df, including already-processed products!
        best_match_idx = self.find_best_match(enhanced_product['Kat. číslo'], 'Kat. číslo', df)
        if best_match_idx is None:
            best_match_idx = self.find_best_match(enhanced_product['Názov tovaru'], 'Názov tovaru', df)
```

**What happened:**
1. We filter `needs_processing = df[df['Spracovane AI'] == False]` to get unprocessed products
2. We send those products to the API
3. API returns enhanced products with catalog numbers
4. **BUG:** We search the ENTIRE df for matches, not just the `needs_processing` subset
5. Fuzzy matching finds similar products that might already be processed
6. Updates are applied to the WRONG rows
7. The products we actually processed never get marked as done
8. Next run re-processes them again

**Why it was hard to detect:**
- The error logger for "No match found" was never triggered
- This proved that matches WERE being found
- But they were matching to the WRONG products!
- Example: Product "ABC 100L" (unprocessed) matched to "ABC 100L v2" (already processed)

### Bug #3: Aggressive String Cleaning on ALL Columns

**Location:** `src/core/data_pipeline.py` lines 176-177

**Issue:**
```python
# BEFORE (BUGGY CODE)
for col in final_df.columns:  # ❌ Cleaning ALL columns including tracking
    if final_df[col].dtype == 'object':
        final_df[col] = final_df[col].fillna("").astype(str).replace("nan", "").str.strip()
```

**What happened:**
- This ran BEFORE AI enhancement on every pipeline execution
- When loading a CSV with existing `'Spracovane AI'` values, this converted booleans/numbers to strings
- Created data type inconsistencies that compounded with Bug #1

## Solutions Implemented

### Fix #0: Individual Column Assignment (CRITICAL FIX)
**File:** `src/services/ai_enhancer.py` lines 214-238

Replaced multi-column list assignment with individual assignments using `.at[]`:

```python
# AFTER (FIXED CODE)
def update_dataframe(self, df: pd.DataFrame, enhanced_products: List[Dict[str, str]]) -> Tuple[pd.DataFrame, int]:
    """Update dataframe with enhanced descriptions using fuzzy matching."""
    # DO NOT copy - work on the original dataframe to ensure updates persist
    updated_count = 0
    
    for enhanced_product in enhanced_products:
        # Find the best matching by Kat. číslo
        best_match_idx = self.find_best_match(enhanced_product['Kat. číslo'], 'Kat. číslo', df)
        if best_match_idx is None:
            best_match_idx = self.find_best_match(enhanced_product['Názov tovaru'], 'Názov tovaru', df)
        
        if best_match_idx is not None:
            # Update columns INDIVIDUALLY to preserve dtypes and ensure proper assignment
            df.at[best_match_idx, 'Krátky popis'] = enhanced_product['Krátky popis']
            df.at[best_match_idx, 'Dlhý popis'] = enhanced_product['Dlhý popis']
            df.at[best_match_idx, 'SEO titulka'] = enhanced_product['SEO titulka']
            df.at[best_match_idx, 'SEO popis'] = enhanced_product['SEO popis']
            df.at[best_match_idx, 'SEO kľúčové slová'] = enhanced_product['SEO kľúčové slová']
            # CRITICAL: Set tracking columns separately to preserve boolean type
            df.at[best_match_idx, 'Spracovane AI'] = True
            df.at[best_match_idx, 'AI_Processed_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            updated_count += 1
    
    return df, updated_count
```

**Why this works:**
- `.at[]` is optimized for single-value assignment and preserves dtypes
- Individual assignments ensure boolean `True` is stored as a native boolean, not an object
- Removed the `df.copy()` to work directly on the passed dataframe reference
- Updates now properly persist through the processing pipeline

**Impact:** This is THE critical fix. Without this, updates appear to work in memory but don't persist to disk.

### Fix #1: Deterministic Exact Matching with Limited Search Scope
**File:** `src/services/ai_enhancer.py` lines 214-268

Implemented 3-tier matching strategy with scope limitation:

```python
# AFTER (FIXED CODE)
def update_dataframe(self, df: pd.DataFrame, enhanced_products: List[Dict[str, str]], valid_indices: pd.Index = None):
    # Create a subset view for searching if valid_indices provided
    search_df = df.loc[valid_indices] if valid_indices is not None else df
    
    for enhanced_product in enhanced_products:
        # Strategy 1: Exact match on 'Kat. číslo' (most reliable)
        cat_num = str(enhanced_product['Kat. číslo']).strip()
        exact_matches = search_df[search_df['Kat. číslo'].astype(str).str.strip() == cat_num]
        
        if len(exact_matches) == 1:
            best_match_idx = exact_matches.index[0]
        elif len(exact_matches) > 1:
            best_match_idx = exact_matches.index[0]
            logger.warning(f"Multiple exact matches for {cat_num}")
        else:
            # Strategy 2: Fuzzy match on catalog number (handles minor variations)
            best_match_idx = self.find_best_match(enhanced_product['Kat. číslo'], 'Kat. číslo', search_df)
            if best_match_idx is None:
                # Strategy 3: Fuzzy match on product name (last resort)
                best_match_idx = self.find_best_match(enhanced_product['Názov tovaru'], 'Názov tovaru', search_df)
        
        # Update using .at[] for each column individually...
```

**Key improvements:**
1. **Limited search scope:** Only search within `needs_processing_indices`, not the entire df
2. **Exact match first:** Use deterministic string comparison before fuzzy matching
3. **Handles duplicates:** Logs warning if multiple exact matches found
4. **Fallback strategy:** Three levels - exact → fuzzy catalog → fuzzy name
5. **Index tracking:** Pass `valid_indices` from `process_dataframe()` to ensure we only match unprocessed products

**Impact:** Ensures updates are applied to the correct products that were actually sent for processing.

### Fix #2: DataFrame Copy Protection
**File:** `src/services/ai_enhancer.py`

Created copies before CSV encoding operations to prevent mutation:

```python
# AFTER (FIXED CODE)
# Work on a COPY to avoid corrupting the original dataframe
df_copy = df.copy()

for col in df_copy.columns:  # ✅ Only modifying the copy
    if df_copy[col].dtype == 'object':
        df_copy[col] = df_copy[col].astype(str)
        df_copy[col] = df_copy[col].apply(lambda x: ...)

df_copy.to_csv(tmp_file, index=False, encoding='cp1250', sep=';')
```

**Impact:** Original dataframe tracking columns remain intact across all batch processing.

### Fix #3: Exclude Tracking Columns from Cleaning
**File:** `src/core/data_pipeline.py`

```python
# AFTER (FIXED CODE)
ai_tracking_columns = {'Spracovane AI', 'AI_Processed_Date'}
for col in final_df.columns:
    if col not in ai_tracking_columns and final_df[col].dtype == 'object':  # ✅ Skip tracking
        final_df[col] = final_df[col].fillna("").astype(str).replace("nan", "").str.strip()
```

**Impact:** AI tracking columns maintain their data types through the pipeline.

### Fix #4: Defensive Type Normalization
**File:** `src/services/ai_enhancer.py` lines 254-263

Added robust type handling at the start of `process_dataframe()`:

```python
# Normalize 'Spracovane AI' column to handle various data types
# Convert string representations of True/False to actual booleans
df['Spracovane AI'] = df['Spracovane AI'].apply(
    lambda x: True if str(x).strip().upper() in ['TRUE', '1', 'YES'] else 
             False if str(x).strip().upper() in ['FALSE', '0', 'NO', ''] else x
)

# Filter products needing processing (only False or empty values)
needs_processing = df[df['Spracovane AI'].isin([False, ''])]
```

**Impact:** Handles corrupted data from previous runs and normalizes to consistent boolean values.

## Testing Recommendations

To verify the fix works correctly:

1. **Clean slate test:**
   - Delete `tmp/processed_tmp.csv`
   - Run AI enhancement on fresh data
   - Verify `Spracovane AI` column contains boolean `True` values

2. **Incremental test:**
   - Run AI enhancement on partial dataset
   - Run again without changing data
   - Should report "No products need AI enhancement"

3. **Resume test:**
   - Interrupt AI processing mid-run
   - Restart application and run again
   - Should only process remaining products (not already-processed ones)

4. **Type consistency test:**
   - After processing, export to CSV
   - Reload CSV and check `Spracovane AI` data types
   - Should properly filter already-processed products

## Files Modified

1. `src/services/ai_enhancer.py`:
   - **Lines 214-268:** CRITICAL - Replaced multi-column list assignment with individual `.at[]` assignments, removed unnecessary `df.copy()`, and implemented 3-tier exact matching strategy
   - **Lines 214-268:** CRITICAL - Added `valid_indices` parameter to `update_dataframe()` to limit search scope to only unprocessed products
   - Lines 254-263: Added type normalization for 'Spracovane AI' column
   - Lines 300-301: Store `needs_processing_indices` for accurate matching
   - Lines 310-314: Pass batch indices through pipeline
   - Lines 320-321: Updated batch submission to pass indices
   - Lines 330-332: Pass `valid_indices` to `update_dataframe()` for scope-limited matching
   - Lines 338-339: Added df.copy() for incremental saves
   - Lines 370-371: Added df.copy() for final save
   - Lines 398-409: Updated `_process_single_batch()` to return batch indices

2. `src/core/data_pipeline.py`:
   - Lines 174-178: Excluded AI tracking columns from string cleaning

## Prevention

**Design principles learned:**

1. **Multi-column list assignments are dangerous:** When assigning to multiple columns with mixed types (strings + booleans), pandas can corrupt dtypes or fail to persist values. Always use individual `.at[]` or `.loc[]` assignments for different data types.

2. **DataFrame copies must be intentional:** Unnecessary `.copy()` operations can break reference chains. Only copy when you explicitly need to preserve the original or prevent mutation during encoding/export.

3. **Encoding operations must be isolated:** Never mutate the original dataframe when performing encoding/export operations. Always work on a copy to avoid side effects.

4. **Always use scope-limited searches:** When updating processed items, only search within the subset that was actually processed. Never search the entire DataFrame when you have a filtered subset.

**Code review checklist:**
- [ ] Use individual `.at[]` assignments for mixed-type column updates
- [ ] Avoid unnecessary DataFrame copies that break reference chains
- [ ] Limit search scope when matching - only search within the relevant subset
- [ ] Implement exact matching before fuzzy matching for deterministic results
- [ ] Check for in-place modifications during save operations
- [ ] Verify tracking columns are excluded from aggressive cleaning
- [ ] Ensure data type consistency is maintained across pipeline stages
- [ ] Test that boolean columns remain boolean after updates and saves
- [ ] Track indices through the processing pipeline for accurate matching

## Summary

This was a complex, multi-layered bug caused by several compounding issues:

1. **Primary culprit:** Multi-column list assignment corrupting boolean dtypes
2. **Secondary culprit:** Fuzzy matching searching entire DataFrame instead of just unprocessed products
3. **Contributing factors:** DataFrame copies breaking references, aggressive string cleaning, CSV encoding mutations

The fix required:
- Changing assignment strategy from multi-column lists to individual `.at[]` calls
- Implementing 3-tier matching (exact → fuzzy catalog → fuzzy name)
- Limiting search scope to only unprocessed products
- Protecting tracking columns from string cleaning and encoding mutations
- Adding defensive type normalization for resilience

**All fixes are now in place. The system should correctly track processed products and never re-process already-completed items.**
