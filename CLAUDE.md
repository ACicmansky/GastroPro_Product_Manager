# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GastroPro Product Manager is a Python desktop application for merging product data from multiple sources (local XLSX/CSV, XML feeds, web scraping) and enhancing it with AI-generated B2B descriptions and SEO metadata. Output is a standardized 138-column e-shop CSV format.

## Commands

```bash
# Run the application (new format - primary)
python main_new_format.py

# Run the application (legacy format)
python main.py

# Run all tests
pytest

# Run tests by marker
pytest -m ai_enhancement
pytest -m scraper
pytest -m category_filter

# Run specific test file
pytest tests/test_ai_enhancer_new_format.py -v
```

## Architecture

### Data Flow Pipeline
```
Load (XLSX/CSV) → Parse XML Feeds → Merge Data → Map Categories → AI Enhance → Filter → Transform → Export CSV
```

### Key Directories
- `src/pipeline/` - Pipeline orchestration (`pipeline_new_format.py` is the primary entry point)
- `src/parsers/` - XML parsing with namespace support for Gastromarket (RSS+g: prefix) and ForGastro
- `src/mergers/` - Data merging with image priority and source tracking
- `src/ai/` - Gemini API integration with quota management and web search grounding
- `src/scrapers/` - Web scrapers (Topchladenie multi-threaded, Mebella Playwright-based)
- `src/gui/` - PyQt5 interface (`main_window_new_format.py` is primary)
- `src/filters/` - Category selection and filtering
- `src/transformers/` - Output format conversion (138 columns)

### Entry Points
- `main_new_format.py` - Primary GUI (138-column format)
- `main.py` - Legacy GUI
- `scripts/scraping_cli.py` - CLI for web scraping

## Configuration

### Key Files
- `config.json` - Master config: XML feed URLs, output mappings (139 columns), AI settings, field transformations
- `categories.json` - Category mapping database (`[{"oldCategory": "...", "newCategory": "..."}]`)
- `.env` - Must contain `GOOGLE_API_KEY` for Gemini API

### AI Enhancement Settings (in config.json)
- Model: `gemini-2.5-flash-lite`
- Batch size: 45 products
- Rate limits: 15 calls/min, 250K tokens/min
- Dual prompt system: variants (no dimensions) vs standard products

## Critical Implementation Details

### XML Parsing
- **Gastromarket Feed**: Uses prefixed namespace (`xmlns:g=`). Elements use `g:` prefix (e.g., `<g:KATALOG_CISLO>`). Must use ElementTree with namespace dictionary.
- **ForGastro Feed**: Standard XML without namespace.

### File Encoding
- Primary: UTF-8
- Fallback: cp1250 (Central European for legacy data)

### Merging Logic
- Feed products always included and update existing data
- Source tracking: `gastromarket`, `forgastro`, `web_scraping`, `core`
- Image merge prioritizes source with most images

### AI Enhancement
- Products with `pairCode` (variants) use dimension-free prompts
- 3-strategy fuzzy matching: exact code → fuzzy code → fuzzy name
- Incremental saving after each batch
- Thread-safe quota management with automatic backoff

### Web Scraping
- Mebella: Playwright with infinite scroll, caches URLs for 7 days in `cache/`
- Topchladenie: Multi-threaded (8 workers)

## Test Markers
```python
@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.ai_enhancement
@pytest.mark.scraper
@pytest.mark.category_filter
@pytest.mark.requires_api      # Tests requiring API access
@pytest.mark.requires_network  # Tests requiring network
```

## Memory Bank
Project knowledge base in `memory-bank/`:
- `activeContext.md` - Current status and recent changes
- `progress.md` - Feature completion tracking
- `techContext.md` - Technology stack details
- `systemPatterns.md` - Design patterns
