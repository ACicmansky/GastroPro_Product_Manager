# Integration of 4-5 Product FAQs into AI Generation Prompts

## Context
When enhancing product listings with `gemini-3.8-flash` on `thinking_level: "high"`, the user requested generating 4–5 FAQs per product to improve conversion rates and capture Google FAQ Rich Snippets in search results.

## Changes Made
1. **Prompt Engineering in [src/ai/prompts.py](file:///c:/Source/Python/GastroPro_Product_Manager/src/ai/prompts.py)**:
   - Updated `create_system_prompt()`:
     - Expanded `description` (Dlhý popis) target range from 200–600 words to **300–800 words**.
     - Added explicit instructions for generating 4–5 practical B2B questions and answers directly grounded in the product's technical attributes (electrical connection, maintenance/cleaning, gastro operations, accessory compatibility).
     - Instructed HTML formatting for the FAQ block at the end of the description:
       ```html
       <h3>Často kladené otázky (FAQ)</h3>
       <p><strong>Otázka: ...?</strong><br>Odpoveď: ...</p>
       ```
     - Updated checklist to verify 4–5 FAQs are present in `description`.
   - Updated `create_system_prompt_no_dimensions()`:
     - Extended negative dimension constraints to explicitly apply to the FAQ questions and answers as well, ensuring variant listings don't re-introduce forbidden dimension strings.

2. **Test Coverage in [tests/test_ai_enhancer.py](file:///c:/Source/Python/GastroPro_Product_Manager/tests/test_ai_enhancer.py)**:
   - Added `test_system_prompts_include_faq_generation` to assert standard prompt includes FAQ instructions and HTML tags, and variant prompt extends negative constraints to the FAQ block.

3. **Restored Prefix Consistency**:
   - Re-aligned `categories_with_parameters.json` with the canonical `"Tovary a kategórie > "` prefix required by `_category_of`.

## Verification
- Total tests: **241 passed** in ~9s via `uv run poe check`.
- Ruff linting and formatting clean.
