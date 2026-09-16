# 2026-09-16: Thinking Budget Calibration (3072 tokens) & Chunk Size Reduction (100)

## Context & Motivation
During the initial production run of 9,707 uncategorized/unenhanced products with `thinking_level: "high"` and `chunk_size: 500`, Google Cloud Batch API experienced internal worker timeouts (`{'code': 13, 'message': 'Internal error encountered.'}`) on background preemptible nodes after running for 5.5 hours. While direct single-product calls take only ~12–15 seconds, unbound reasoning tokens (up to 8,000 per product) across 500 items caused worker node exhaustion.

## Implementation Details
1. **Config Tuning (`config.json`)**:
   - Set `"chunk_size": 100` (down from 500). Smaller chunks allow batches to finish in ~25–35 minutes instead of 5+ hours, committing enriched products to SQLite incrementally every half-hour.
   - Added `"thinking_budget": 3072` inside `"ai_enhancement"`. This provides ample reasoning (~2,300 words of internal chain-of-thought) for complex B2B kitchen equipment parameters and FAQ synthesis while bounding execution time and preventing batch worker preemption.

2. **Batch Orchestrator (`src/ai/batch_orchestrator.py`)**:
   - Added `self.thinking_budget = ai_config.get("thinking_budget")` in `__init__`.
   - Implemented `_get_thinking_config()` helper:
     ```python
     if self.thinking_budget is not None:
         try:
             budget = int(self.thinking_budget)
             if budget > 0:
                 return {"thinkingBudget": budget}
         except (ValueError, TypeError):
             pass
     if self.thinking_level:
         return {"thinkingLevel": self.thinking_level.upper()}
     return None
     ```
   - Google Gemini API strictly enforces mutual exclusivity between `thinkingBudget` and `thinkingLevel` (`ClientError: 400 You can only set only one of thinking budget and thinking level`). The helper ensures `thinkingBudget` takes precedence when provided without violating API constraints.

3. **Automated Testing (`tests/test_ai_enhancer.py`)**:
   - Added `test_batch_orchestrator_builds_thinking_budget_config` verifying that `thinkingBudget: 3072` is serialized into `generationConfig["thinkingConfig"]` and `thinkingLevel` is omitted when budget is specified.

## Verification
- `uv run poe check` passed with zero errors (all 245 tests passed in 9.06s).
