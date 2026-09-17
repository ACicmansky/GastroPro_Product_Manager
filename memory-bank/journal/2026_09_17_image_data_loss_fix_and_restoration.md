# 2026-09-17: Image Data Loss Fix and Restoration (9,192 Products Restored)

## Context & Problem
An audit of `data/products.db` revealed that only 364 of 9,712 products had images (96.25% missing), despite the original client file (`products (2).xlsx`) having 5,391 products with images and a previous DB backup having 9,136 products with images.

## Root Cause Analysis
1. **`OutputTransformer.split_images()` blanked images**: When exporting DataFrames that were already in the modern format (where images live in `image`, `image2`, ... rather than a single comma-separated `"Obrázky"` column), `split_images()` did not find `"Obrázky"` and actively wiped `image` through `image8` to `""` in `output_df`.
2. **Re-upload overwrote SQLite**: When `AI 2026_09_16_GastroPro.xlsx` was subsequently loaded into the pipeline as the main data file, `ProductDB.upsert()` replaced `product_data` with the file's blank image columns.
3. **Feed merger vulnerability**: `ProductMerger._update_from_feed` lacked defensive checks preventing empty strings in feed image columns from blanking existing target image values.

## Implementation Details
1. **`OutputTransformer.split_images()` (`src/domain/transform/output_transformer.py`)**:
   - Preserves existing `image`, `image2`, ..., `image8` columns from `df` when `"Obrázky"` is absent.
   - When `"Obrázky"` is present, merges and overrides only non-empty values.
2. **`ProductMerger._update_from_feed()` (`src/domain/products/merger.py`)**:
   - Expanded `IMAGE_COLUMNS` to include `defaultImage` and up to `image20`.
   - Explicitly forbids empty feed image values (`""`, `"none"`, `"nan"`) from overwriting valid existing images in target.
3. **Automated Testing**:
   - Added `test_split_images_preserves_existing_images_when_obrazky_missing` in `tests/test_output_transformer.py`.
   - Added `test_feed_does_not_overwrite_main_image_with_empty` in `tests/test_data_merging_new_format.py`.
   - Full test suite: **250 tests passing** via `uv run poe check`.

## Image Restoration
- Implemented `scripts/restore_product_images.py`.
- Created safety backup `data/backups/products_backup_before_image_restore_20260917_220841.db`.
- Combined image sources with priority to client file `products (2).xlsx` (5,391 products) followed by DB backup `products_backup_20260916_104351.db` (9,136 products).
- Restored images for **9,192 products** into `data/products.db`.
- **Result: 9,203 / 9,712 products (94.76%) now have images, while 100% of AI copy, FAQs, SEO metadata, and category parameters (9,701 products) remain fully intact.**
