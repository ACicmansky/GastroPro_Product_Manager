# AI Product Image Generator Core Implementation & Real Product Testing

- **Date**: 2026-09-17
- **Author**: Antigravity Assistant

## Context & Motivation
Following the successful catalog-wide AI enhancement (9,701 products) and image restoration (9,192 products), exactly 509 catalog products in `data/products.db` lacked images (primarily stainless steel sinks, tables, and Mebella table bases).
The user requested building a commercial product image generation core and testing it on products without images to verify quality and feasibility.

## Key Technical Discoveries & Decisions
1. **Model Selection**:
   - Tested `client.models.generate_images` on `imagen-3.0-generate-002` -> returned 404 NOT_FOUND on current v1beta API endpoints.
   - Tested `client.models.generate_content(model="gemini-2.5-flash-image", config=types.GenerateContentConfig(response_modalities=["IMAGE"]))` -> fully supported, high reliability, returns inline PNG bytes (`part.inline_data.data`).
2. **Token Efficiency & Economics**:
   - Each generated image uses exactly **1,290 output candidate tokens** + ~310 prompt tokens.
   - Cost per image: **~$0.00055 USD** (~0.055 cents per product).
   - Entire batch of 509 missing images costs only **~$0.28 USD** (~28 cents).
   - Generation speed: **~5.1 - 5.5 seconds** per image.
3. **Prompt Architecture**:
   - Dynamic prompt builder extracts product title, category, dimensions (e.g. 620x360x320mm), manufacturer, and unescaped/cleaned description summaries.
   - Strict photography directives: commercial e-commerce studio photo, isolated on pure white background (`#FFFFFF`), subtle soft drop shadow underneath, softbox lighting, 3/4 front view, no watermarks, no people, no kitchen background clutter.

## Implementation Details
1. **Configuration**:
   - Added `image_generation` section in `config.json` specifying model (`gemini-2.5-flash-image`), default output directory (`out/generated_images`), and aspect ratio (`1:1`).
2. **Core Module (`src/ai/image_generator.py`)**:
   - `clean_text_from_html`: strips tags, unescapes entities, cleans whitespace.
   - `sanitize_filename`: ensures safe Windows/POSIX filenames.
   - `ProductImageGenerator`: handles Google GenAI client lifecycle, prompt generation, image content generation, token tracking, and PNG persistence.
   - `generate_batch`: handles multi-product sequential generation with progress callbacks.
3. **CLI Runner (`scripts/generate_product_image.py`)**:
   - CLI script with `--code`, `--prompt-only`, `--model`, and auto-discovery of products missing images from `data/products.db`.
   - Windows UTF-8 stdout reconfiguration to support Slovak diacritics.
4. **Unit Tests (`tests/test_image_generator.py`)**:
   - 8 new unit tests covering text cleaning, sanitization, prompt construction, client availability, mocked image generation, and batch generation.

## Test Generation Results
- **Product 1 (SKU `S436120`)**: Chafing Dish GN 1/1 Stalgast (stainless steel, 2 paste burners, roll lid). Generated in 5.48s, 1,608 total tokens ($0.000548 USD).
- **Product 2 (SKU `S376036`)**: Red milk frothing pitcher 0.35L Stalgast. Generated in 5.07s, 1,595 total tokens ($0.000547 USD).
- Both outputs were verified: photorealistic commercial catalog photos on pure white seamless backgrounds.

## Verification
- `uv run poe check` executed with 0 lint errors, 0 format issues, and all **263 tests passing** in parallel.
