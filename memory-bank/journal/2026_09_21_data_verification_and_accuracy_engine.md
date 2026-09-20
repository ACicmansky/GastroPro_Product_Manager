# Journal Entry: Multi-Tiered Product Data Verification Engine & Catalog Accuracy

**Date**: 2026-09-21  
**Author**: Antigravity  
**Goal**: Build a multi-tiered, free / ultra-low-cost product data verification engine, diagnose upstream feed discrepancies (e.g. F840130 insulation 70mm vs true 60mm), restore missing filter properties from pre-incident backup, and implement automated OEM spec patching.

---

## 1. Problem Investigation: F840130 Generation Trace
- Traced the batch generation of `F840130` (`Forcold chladnička 1300l`) to Google Gemini Batch Job `batches/63q6xv7d7j8p1mg0ta017p93lb78bonkhpcx` in request payload `out/batch_requests/batch_requests_20260917_080055_651002.jsonl`.
- **Finding on Grounding**: Grounding was **not used** during batch generation because Google Gemini Batch API runs with strict JSON schema enforcement (`responseMimeType: application/json`), which does not attach Google Search tool.
- **Root Cause of "70 mm"**: The input text sent to Gemini in the batch request already contained `"hrúbka steny 70 mm"` (inherited all the way from the August 2025 e-shop export in `ALLexport-products.csv`). Following its prompt rules (`Pravdivosť: nič si nedomýšľaj`), Gemini faithfully copied 70 mm into its outputs.
- **Manufacturer Ground Truth**: Official Forcold portal (`forcold.it/en/product/refrigerated-cabinets-gn2-1-ventilated-g-gn1410tn-fc/`) specifies model `G-GN1410TN-FC` (SKU `F840130`) with **`INSULATION (mm): 60`**, confirming that the distributor's 70 mm was an upstream copy-paste typo.

---

## 2. Parameter Restoration (Pre-Incident Backup Recovery)
- Discovered that an earlier image restoration script had accidentally dropped `filteringProperty:*` columns from active `data/products.db` when merging from an older DB backup.
- Implemented `scripts/restore_ai_parameters.py` and restored **34,108 AI filter parameters** across **9,119 products** from `data/backups/products_backup_20260917_205246.db`, with 100% image preservation.

---

## 3. Multi-Tiered Verification & Patching Implementation
1. **CatalogAuditor (`src/domain/specs/auditor.py`)**:
   - Deterministic offline scanner checking for text vs parameter mismatches (insulation, power, voltage, dimensions) and geometric impossibilities ($V_{\text{inner}} > V_{\text{outer}}$).
   - CLI: `scripts/audit_catalog.py` generating `reports/data_quality_audit.csv` and `reports/data_quality_summary.json`.
   - Identified 362 issues across 358 products in seconds for **$0.00**.
2. **OEM Spec Adapters (`src/scrapers/oem/`)**:
   - Created `BaseOEMAdapter`, `ForcoldAdapter`, and `StalgastAdapter` covering over 70% of the catalog's manufacturers.
3. **SpecPatcher (`src/domain/specs/patcher.py`)**:
   - Synchronizes verified specs into both `filteringProperty:*` and customer-facing HTML text (`shortDescription`, `description`, `FAQ`, `metaDescription`).
   - Automatically creates timestamped SQLite backups.
   - CLI: `scripts/patch_product_specs.py`.
4. **Targeted Grounded Fact-Checking (`scripts/fact_check_products.py`)**:
   - Micro-verification subagent using `gemini-2.5-flash-lite` with Google Search grounding tool for unresolved flagged items (<$0.50).

---

## 4. Verification & Results
- Successfully patched `F840130` and sister models (`F840131`, `F840650`, `F840651`) in `data/products.db` to verified 60 mm insulation across all text descriptions and filter parameters.
- Test suite: **267 passed tests** in 10.23s via `uv run poe check` (10 new unit tests added).
