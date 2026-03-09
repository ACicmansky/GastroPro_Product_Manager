# Gastromarket Stalgast Feed Integration and GUI Adjustments

## Date: 2026-03-09

## Overview
Integrated a new XML feed for Stalgast products from Gastromarket and incorporated user-made adjustments to the configuration and GUI.

## Changes Made
1. **Gastromarket Stalgast Feed Integration**:
   - Added configuration mapping for `gastromarket_stalgast` feed URL (`https://www.gastromarket.sk/product_data/B2B_Product_Feed_Stalgast.xml`) to `config.json`.
   - Updated `src/parsers/xml_parser_new_format.py` with a new `parse_gastromarket_stalgast` method handling identical namespace and mapping configurations as the parent gastromarket feed.
   - Updated `src/parsers/xml_parser_factory.py` and `src/pipeline/pipeline_new_format.py` to route the new feed to the appropriate parser.
   - Added a new `QCheckBox` "Načítať z GastroMarket STALGAST XML" to `src/gui/main_window_new_format.py`, and updated conditional checks for when products are ready to export.
   - Updated `src/gui/worker_new_format.py` to optionally download and process the new Stalgast XML feed alongside other configured feeds.

2. **User Adjustments Post-Integration**:
   - Added `Unnamed: 386` column to `final_csv_columns` in `config.json`.
   - Defaulted AI enhancement (`is_ai_enhancement_enabled`) to `False` instead of `True` in `src/gui/main_window_new_format.py`.
   - Re-applied syntax formatting via `black/ruff` to `src/gui/main_window_new_format.py`.

## Next Steps
- Verify feed processes correctly with full application runs.
- Monitor execution parameters.
