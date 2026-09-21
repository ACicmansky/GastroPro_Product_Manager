# Catalog Product Variant Pairing (`pairCode` & Variant Parameters) - 2026-09-21

## Overview
Resolved missing and corrupted `pairCode` data across the catalog to establish full compliance with the Shoptet e-shop import standard. Cleaned legacy float formatting artifacts (`1.0` - `21.0`), populated missing `pairCode` for Mebella table bases, and automatically detected and paired dimension-based variant families across commercial equipment.

## Context & Root Cause Analysis
1. **Shoptet Variant Model**:
   - `pairCode` (Kat. číslo rodiča / Kód párového produktu) links multiple SKUs into a single product with selectable dropdown variants.
   - For standalone products (solitéry), `pairCode` must remain empty.
   - For variant products, `pairCode` must be identical across the family, and each variant must possess distinguishing values in variant parameter columns (e.g. `variant:Rozmer`, `variant:Prevedenie`).
2. **Prior State in Database**:
   - 9,108 products (93.8%) had `pairCode = ""` from inception.
   - 604 products (6.2%) had legacy float string values (`1.0` to `21.0`) due to pandas loading integer columns with missing cells as float64 from the initial legacy import.
   - 558 Mebella table base products (156 multi-height families) were stored with empty `pairCode` because they were never re-scraped through `ScrapingOrchestrator`.
   - `OutputTransformer._ensure_all_columns()` sliced out dynamic `variant:*` columns because it only retained `filteringProperty:*` and `required_cols`.

## Changes Implemented

### 1. Domain Service: `CatalogVariantService`
- **File**: `src/domain/products/variant_service.py`
- Implemented 3 sequential stages:
  1. **Stage 1 (Legacy Normalization)**:
     - Mapped legacy float groups to canonical model codes: `13.0` -> `BT100`, `11.0` -> `TN70`, `21.0` -> `GAUS10`, etc.
     - Extracted dimensions for box and furniture families into `variant:Rozmer`.
     - Cleared singletons (`2.0`, `4.0`, `6.0` with count=1) to empty string.
  2. **Stage 2 (Mebella Table Base Pairing)**:
     - Parsed height types (`BAR`, `DINING`, `COFFEE`, `LOUNGE`) and finishes (`-POL-`, `(POL)`, `-SAT-`, `(SAT)`).
     - Formed 156 multi-variant families (426 products) with `pairCode` = base model, `variant:Prevedenie` = height description, and `variantVisibility = "1"`.
  3. **Stage 3 (General Dimension Variant Clustering)**:
     - Grouped products sharing identical category, manufacturer, and base name differing strictly by dimension.
     - Enforced strict dimension uniqueness per family.
     - Created 155 variant families (1,103 products) with `pairCode` = common prefix / parent SKU, `variant:Rozmer` = dimension, and `variantVisibility = "1"`.

### 2. Output Transformation Updates
- **File**: `src/domain/transform/output_transformer.py`
- Added forwarding of all `variant:*` dynamic columns in `apply_direct_mappings()` and `_ensure_all_columns()`.
- Activated `_update_variantVisibility()` in `transform()` to ensure `variantVisibility = "1"` for all paired items.

### 3. Merger Helper Enhancement
- **File**: `src/domain/products/merger.py`
- Updated `get_pair_code()` to handle embedded variant keywords and finish tokens.

### 4. Migration CLI Script
- **File**: `scripts/populate_catalog_variants.py`
- Provided `--dry-run` and `--apply` with automatic safety backup to `data/backups/products_backup_before_variants_{timestamp}.db`.

## Results
- **2,130 products (21.93% of catalog)** are now properly paired under 482 distinct variant families with full parameter support (`variant:Rozmer`, `variant:Prevedenie`).
- **7,582 standalone products (78.07%)** keep `pairCode = ""` in accordance with Shoptet rules.
- **Zero `.0` float artifacts remaining**.
- **Full Test Suite Passing**: 283 tests passing in ~28s via `uv run poe check`.
- Verified export: `out/test_variants_export.xlsx` (9,712 rows × 599 cols, 2,130 paired, 1,608 `variant:Rozmer`, 426 `variant:Prevedenie`, 2,140 `variantVisibility = 1`).
