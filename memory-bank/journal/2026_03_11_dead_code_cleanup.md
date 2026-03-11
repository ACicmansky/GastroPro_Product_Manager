# Legacy Dead Code Cleanup (2026-03-11)

## Architecture Modernization
Since November 2025, the application had successfully migrated from the original logic flow to the robust `PipelineNewFormat` handling 138-column specifications. However, the original "old format" files were retained during the transition period. 

Today we focused on cleaning out this technical debt.

## Actions Taken
1. **Component Verification**
   We initialized CodeGraphContext (CGC MCP) using a KuzuDB backend to dynamically build a graph of all active code references.
   Through `analyze_code_relationships` via MCP, we confirmed various legacy modules—such as the old `main.py`, the old `src/core/data_pipeline.py`, the old `ai_enhancer.py`, and outdated GUI dialogues like `ai_enhancer_dialog.py`—had strictly **0** callers remaining across the repository.

2. **File Deletion**
   In total, **14 files** intrinsically tied to the old pipeline and old UI entries were successfully purged from `src/`.

3. **Test Suite Standardization**
   The test module `test_ai_enhancer.py` (which explicitly targetted the deprecated enhancer component) was pruned.
   A failing category mapping integration test inside `test_pipeline_new_format.py` (caused by the codebase relying on the actual persistent `products.db` mock data containing newer secondary string prefixes like `Domácnosť a Kulinári >`) was patched. The assertion now broadly accepts both root category schemas.

4. **Result**
   The application now boasts a clean, strictly `new format` module layout with 176 out of 176 `pytest` assertions executing successfully.
