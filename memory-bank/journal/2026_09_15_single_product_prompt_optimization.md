# Single-Product Prompt Optimization (Prompt Engineering Patterns)

## Context
Following the shift to `batch_size: 1` and the user's invocation of `/prompt-engineering`, the system prompt in `src/ai/prompts.py` was redesigned from scratch to be natively singular, token-efficient, and optimized for `gemini-3.8-flash` on `high` thinking.

## Techniques Applied from `prompt-engineering` Skill
1. **Instruction Hierarchy**:
   `[System Context & Role]` → `[Category & Parameters]` → `[Quality Principles]` → `[Field Specifications]` → `[Input Format]` → `[Output Specification]`.
2. **Elimination of Plural Confusion**:
   - Replaced all plural references (*"Tieto produkty"*, *"zo všetkých produktov"*, *"pre každý produkt"*, *"susedné produkty"*) with singular product context (*"zadaný gastro produkt"*, *"Kategória produktu"*).
3. **Bloat & Redundancy Removal**:
   - Removed the 15-line redundant checklist at the end of the prompt, as structured output constraints are already enforced via `responseSchema`.
   - Consolidated field rules (shortDescription, description with 4-5 FAQs, seoTitle, metaDescription, parameters) into a clear, single-source specification.
4. **Negative Constraints Compatibility**:
   - Maintained clean insertion point (`### 📤 **VÝSTUP**`) for `create_system_prompt_no_dimensions` variant handling.

## Verification
- `uv run poe check` passed with **241 passed tests** in ~10s.
- Formatted and linted cleanly with Ruff.
