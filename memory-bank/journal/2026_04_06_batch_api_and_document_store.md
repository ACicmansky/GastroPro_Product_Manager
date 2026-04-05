# Journal Entry: Batch API & SQLite Document Store Architecture
**Date**: April 6, 2026

## Overview
This session focused on profoundly changing two core pillars: 
1. Shifting AI enhancements from parallel synchronous API calls to Google Gemini's **asynchronous Batch API**.
2. Restructuring the SQLite persistence layer to act as a **NoSQL JSON Document Store**.

## Why the Change?
Our client requested a specific strategy for generated product attributes (e.g. Dimensions, Features, Type) tied to categories (from `categories_with_parameters.json`), requiring a large volume of attributes that simply cannot be mapped explicitly in rigid database columns beforehand (as there can literally be hundreds of combinations of "filteringProperty:*").

Parallel REST processing wasn't cost-effective or quick enough. Instead, the Gemini Batch API solves our scaling problem while the SQLite schema handles the unpredictable parameter columns trivially by converting unknown data columns horizontally into JSON objects inside a single text field (`product_data`).

## Implementation Details

### The Document Store
- The database schema shifted from defining 138 rigid columns to defining 6 columns: `code`, `product_data`, `source`, `last_updated`, `aiProcessed`, and `aiProcessedDate`.
- Upon `upsert_final()`, Pandas dynamically iterates rows, maps statically designated internal columns (`last_updated`, etc.), then squashes all remaining keys (including all unpredictable category filtering properties) into the `product_data` string.
- Upon retrieval via `get_all_products_df()`, `product_data` uses `json.loads(row[1])` to instantly re-expand back into a completely flattened Pandas DataFrame to hydrate GUI and Transformer modules naturally.

### Google Gemini Batch API
- Overhauled `ai_enhancer_new_format.py` removing threading quota structures entirely in flavor of grouped processing.
- The pipeline collects all eligible products, packages them by unique category strings, attaches unique prompts requesting properties identified in `categories_with_parameters.json`, forms JSON payloads, and initiates the Google Cloud bucket job via `google-generativeai`.
- The GUI disables overlapping operations smoothly based on active jobs in the `batch_jobs` DB and updates when jobs complete across restarts via a passive polling thread natively fetching results, breaking `.jsonl` lines correctly into discrete updates over the exact row.

## Next Steps
- Verify the end-to-end extraction capability mapping AI output filtering properties explicitly over the flattened export pipeline via the `OutputTransformer`.
- Address any `jsonl` malformed JSON issues robustly on partial success outputs internally provided by Gemini Cloud servers.
