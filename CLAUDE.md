# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GastroPro Product Manager is a Python desktop application for merging product data from multiple sources (local XLSX/CSV, XML feeds, web scraping) and enhancing it with AI-generated B2B descriptions and SEO metadata. Output is a standardized 138-column e-shop CSV format.

## Commands

```bash
# Run the application
python main.py

# Run all tests
pytest

# Run tests by marker
pytest -m ai_enhancement
pytest -m scraper
pytest -m category_filter

# Run specific test file
pytest tests/test_ai_enhancer.py -v
```

## Architecture

### Data Flow Pipeline
```
Load (XLSX/CSV) → Parse XML Feeds → Merge Data → Map Categories → AI Enhance → Filter → Transform → Export CSV
```

### Key Directories (layered architecture)
- `src/pipeline/` - Orchestration: `pipeline.py` (linear coordinator), `scraping.py` (ScrapingOrchestrator)
- `src/data/` - I/O layer: `loaders/` (XLSX/CSV), `parsers/` (XML with namespace support for Gastromarket RSS+g: prefix and ForGastro, via XMLParserFactory), `writers/`, `database/`
- `src/domain/` - Business logic: `products/` (merger, variant service), `categories/` (CategoryService, filter), `pricing/`, `transform/` (OutputTransformer, 138 columns), `models.py`
- `src/ai/` - Gemini integration: `api_client.py` (GeminiClient with quota management), `batch_orchestrator.py`, `product_enricher.py`, `prompts.py`, `result_parser.py`
- `src/scrapers/` - Web scrapers (BaseScraper with configurable threading; Topchladenie multi-threaded, Mebella Playwright-based)
- `src/gui/` - PyQt5 interface: `main_window.py`, `worker.py` (thin PipelineWorker), `widgets.py`
- `src/config/` - Config loading and schema

### Entry Points
- `main.py` - GUI application (138-column format)
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
Project knowledge base in `memory-bank/` (rules: `memory-bank/memory-bank-integration.md`, workflow: `memory-bank` skill):
- Before non-trivial work, read `activeContext.md` (current state); other files only on demand
- After significant changes, update `activeContext.md` + add a `journal/YYYY_MM_DD_topic.md` entry
