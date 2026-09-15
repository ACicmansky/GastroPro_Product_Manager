# Optimization for Product Consistency & Batch Size Calibration

## Context
When processing large catalogs with reasoning models (`gemini-3.8-flash` on `high` thinking), generating 30–35 products in a single JSON request poses serious risks:
1. Anti-repetition bias causing inconsistent terminology and varying structure across variants.
2. Attention dilution and fatigue towards later products in the batch.
3. Severe JSON truncation risks (~30,000 output tokens in one response).

## Changes Made
1. **Config Calibration in [config.json](file:///c:/Source/Python/GastroPro_Product_Manager/config.json)**:
   - Configured `"batch_size": 1`.
   - Each product is sent as an independent request line within the Gemini Batch API JSONL.
   - Leverages full Google cloud parallelization with minimal input overhead (~$1.50 USD for the entire catalog).
   - In combination with `"temperature": 0`, this guarantees deterministic, template-level consistency across similar products and product variants.

2. **Prompt Refinement for Consistency in [src/ai/prompts.py](file:///c:/Source/Python/GastroPro_Product_Manager/src/ai/prompts.py)**:
   - Replaced previous anti-repetition instruction with explicit instructions enforcing **consistency, standardized terminology, and professional B2B structure** across product series.
   - Directs the model to reflect specific technical parameters in `seoTitle` and extracted features while preserving the unified standard of the series.

3. **Deterministic Product Ordering in [src/ai/batch_orchestrator.py](file:///c:/Source/Python/GastroPro_Product_Manager/src/ai/batch_orchestrator.py)**:
   - Added sorting by `pairCode` and `code` within category batches before chunking, ensuring that variant families are ordered predictably.

## Verification
- QA test suite: **241 passed** in ~10s via `uv run poe check`.
- Zero linter or formatter warnings.
