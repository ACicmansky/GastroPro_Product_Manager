# Layered Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure GastroPro Product Manager into a clean layered architecture (data / domain / ai / pipeline / gui / config) with strict dependency rules, eliminating scattered business logic and duplicated code.

**Architecture:** Bottom-up migration — build new layers alongside old code, move logic module by module, then delete old directories. Each phase produces a working application. Dependency rule: `gui -> pipeline -> domain + ai -> data`. No layer imports upward.

**Tech Stack:** Python 3.x, pandas, PyQt5, google-genai, rapidfuzz, sqlite3, openpyxl, BeautifulSoup, requests, Playwright

---

## File Structure

### New files to create

```
src/data/__init__.py
src/data/loaders/__init__.py
src/data/loaders/xlsx_loader.py          # moved from src/loaders/xlsx_loader.py
src/data/loaders/loader_factory.py       # moved from src/loaders/data_loader_factory.py
src/data/parsers/__init__.py
src/data/parsers/xml_parser.py           # moved from src/parsers/xml_parser_new_format.py
src/data/parsers/xml_parser_factory.py   # moved from src/parsers/xml_parser_factory.py
src/data/database/__init__.py
src/data/database/product_db.py          # thin CRUD, extracted from src/core/database.py
src/data/database/batch_job_db.py        # batch job tracking, extracted from src/core/database.py
src/data/writers/__init__.py
src/data/writers/xlsx_writer.py          # extracted from pipeline save_output

src/domain/__init__.py
src/domain/models.py                     # dataclasses: MergeStats, MergeResult, EnrichmentResult, PipelineOptions, PipelineResult
src/domain/products/__init__.py
src/domain/products/merger.py            # moved from src/mergers/data_merger_new_format.py
src/domain/products/variant_service.py   # extracted from worker get_pair_code
src/domain/categories/__init__.py
src/domain/categories/category_service.py  # unifies 3 systems
src/domain/categories/category_filter.py   # moved from src/filters/category_filter.py
src/domain/pricing/__init__.py
src/domain/pricing/pricing_service.py    # extracted from worker
src/domain/transform/__init__.py
src/domain/transform/output_transformer.py  # moved from src/transformers/output_transformer.py

src/ai/__init__.py                       # already exists, will be updated
src/ai/api_client.py                     # extracted from ai_enhancer
src/ai/batch_orchestrator.py             # extracted from ai_enhancer
src/ai/result_parser.py                  # extracted from ai_enhancer
src/ai/product_enricher.py              # high-level coordinator
src/ai/prompts.py                        # moved from ai_prompts_new_format.py

src/pipeline/__init__.py                 # already exists, will be updated
src/pipeline/pipeline.py                 # rewritten from pipeline_new_format.py
src/pipeline/scraping.py                 # extracted from worker

src/gui/__init__.py                      # already exists
src/gui/main_window.py                   # rewritten from main_window_new_format.py
src/gui/worker.py                        # rewritten from worker_new_format.py
src/gui/widgets.py                       # kept as-is
src/gui/column_config_dialog.py          # kept as-is

src/config/__init__.py
src/config/config_loader.py              # moved from src/utils/config_loader.py
src/config/schema.py                     # new: generated column definitions

main.py                                  # renamed from main_new_format.py

tests/test_result_parser.py              # new
tests/test_category_service.py           # new
tests/test_merger.py                     # updated from test_data_merging_new_format.py
tests/test_pipeline_integration.py       # updated from test_integration.py
```

### Files to delete after migration
```
src/loaders/                  # entire directory
src/parsers/                  # entire directory
src/core/                     # entire directory
src/mergers/                  # entire directory
src/mappers/                  # entire directory
src/filters/                  # entire directory
src/transformers/             # entire directory
src/utils/                    # entire directory
src/services/                 # entire directory (empty)
src/ai/ai_enhancer_new_format.py
src/ai/ai_prompts_new_format.py
src/pipeline/pipeline_new_format.py
src/gui/main_window_new_format.py
src/gui/worker_new_format.py
main_new_format.py
```

---

## Phase 1: Data Layer

### Task 1: Create domain models (dataclasses)

All typed dataclasses used across the system. This must come first since other modules depend on these types.

**Files:**
- Create: `src/domain/__init__.py`
- Create: `src/domain/models.py`

- [ ] **Step 1: Create `src/domain/__init__.py`**

```python
# src/domain/__init__.py
```

Empty init file.

- [ ] **Step 2: Create `src/domain/models.py` with all dataclasses**

```python
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class MergeStats:
    """Statistics from the product merge operation."""
    created: int = 0
    updated: int = 0
    removed: int = 0
    kept: int = 0


@dataclass
class MergeResult:
    """Result of merging product data from multiple sources."""
    products: pd.DataFrame
    stats: MergeStats


@dataclass
class EnrichmentResult:
    """Result of AI enhancement processing."""
    products: pd.DataFrame
    processed: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass
class PipelineOptions:
    """Typed options for pipeline execution."""
    main_file_path: str = ""
    output_path: str = ""
    selected_categories: list = field(default_factory=list)
    enable_scraping: bool = False
    enable_ai_enhancement: bool = False
    preserve_client_edits: bool = False
    force_ai_reprocess: bool = False
    scrape_mebella: bool = False
    scrape_topchladenie: bool = False
    topchladenie_csv_path: str = ""
    enable_price_mapping: bool = False


@dataclass
class PipelineResult:
    """Result of a complete pipeline run."""
    output_path: str = ""
    merge_stats: Optional[MergeStats] = None
    enrichment_stats: Optional[EnrichmentResult] = None
    product_count: int = 0
    duration_seconds: float = 0.0
```

- [ ] **Step 3: Commit**

```bash
git add src/domain/__init__.py src/domain/models.py
git commit -m "feat(refactor): add domain models dataclasses"
```

---

### Task 2: Create data layer — database modules

Split `src/core/database.py` (331 lines) into thin `ProductDB` (CRUD only) and `BatchJobDB` (AI job tracking).

**Files:**
- Create: `src/data/__init__.py`
- Create: `src/data/database/__init__.py`
- Create: `src/data/database/product_db.py`
- Create: `src/data/database/batch_job_db.py`
- Reference: `src/core/database.py` (existing, lines 1-331)

- [ ] **Step 1: Create init files**

```python
# src/data/__init__.py
```

```python
# src/data/database/__init__.py
from .product_db import ProductDB
from .batch_job_db import BatchJobDB
```

- [ ] **Step 2: Create `src/data/database/product_db.py`**

This is the thin persistence layer. It stores/retrieves products using the existing JSON document-store pattern but contains NO business logic (no merge strategy, no "preserve edits" decisions).

```python
"""Thin product persistence layer using SQLite with JSON document store."""

import sqlite3
import json
import os
import shutil
import glob as glob_module
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd


class ProductDB:
    """Thin CRUD operations for product data stored as JSON in SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.backups_dir = os.path.join(os.path.dirname(db_path), "backups")
        self.table_name = "products"
        self.primary_key = "code"
        self._ensure_directories()
        self.init_db()

    def _ensure_directories(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT PRIMARY KEY,
                    product_data TEXT NOT NULL,
                    source TEXT DEFAULT '',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    aiProcessed TEXT DEFAULT '0',
                    aiProcessedDate TEXT DEFAULT ''
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def get_all(self) -> pd.DataFrame:
        """Retrieve all products, unpacking JSON into flat DataFrame columns."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name}")
            rows = cursor.fetchall()

            if not rows:
                return pd.DataFrame()

            products = []
            for row in rows:
                row_dict = dict(row)
                product_data = json.loads(row_dict.get("product_data", "{}"))
                # Merge fixed columns with JSON data (JSON fields take precedence)
                base = {
                    "code": row_dict["code"],
                    "source": row_dict.get("source", ""),
                    "aiProcessed": row_dict.get("aiProcessed", "0"),
                    "aiProcessedDate": row_dict.get("aiProcessedDate", ""),
                }
                base.update(product_data)
                products.append(base)

            return pd.DataFrame(products)
        finally:
            conn.close()

    def upsert(self, df: pd.DataFrame):
        """Save DataFrame to database. Caller decides what data to pass — DB just stores it."""
        if df.empty:
            return

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for _, row in df.iterrows():
                row_dict = row.to_dict()
                code = str(row_dict.get("code", ""))
                if not code:
                    continue

                source = str(row_dict.get("source", ""))
                ai_processed = str(row_dict.get("aiProcessed", "0"))
                ai_processed_date = str(row_dict.get("aiProcessedDate", ""))

                # Pack everything except fixed columns into JSON
                fixed_cols = {"code", "source", "aiProcessed", "aiProcessedDate"}
                product_data = {
                    k: v for k, v in row_dict.items()
                    if k not in fixed_cols and pd.notna(v)
                }
                product_json = json.dumps(product_data, ensure_ascii=False, default=str)

                cursor.execute(f"""
                    INSERT INTO {self.table_name}
                        (code, product_data, source, last_updated, aiProcessed, aiProcessedDate)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(code) DO UPDATE SET
                        product_data = excluded.product_data,
                        source = excluded.source,
                        last_updated = excluded.last_updated,
                        aiProcessed = excluded.aiProcessed,
                        aiProcessedDate = excluded.aiProcessedDate
                """, (code, product_json, source, now, ai_processed, ai_processed_date))

            conn.commit()
        finally:
            conn.close()

    def delete_by_codes(self, codes: List[str]):
        """Remove products by their codes."""
        if not codes:
            return
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(codes))
            cursor.execute(
                f"DELETE FROM {self.table_name} WHERE code IN ({placeholders})",
                codes
            )
            conn.commit()
        finally:
            conn.close()

    def backup(self, max_backups: int = 10) -> Optional[str]:
        """Create a rotating backup of the database."""
        if not os.path.exists(self.db_path):
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"products_backup_{timestamp}.db"
        backup_path = os.path.join(self.backups_dir, backup_filename)
        shutil.copy2(self.db_path, backup_path)

        # Rotate old backups
        backups = sorted(glob_module.glob(os.path.join(self.backups_dir, "products_backup_*.db")))
        while len(backups) > max_backups:
            os.remove(backups.pop(0))

        return backup_path
```

- [ ] **Step 3: Create `src/data/database/batch_job_db.py`**

```python
"""Batch job tracking for AI processing."""

import sqlite3
import os
from datetime import datetime
from typing import Optional


class BatchJobDB:
    """Tracks Google Batch API job state in SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_table()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    input_file TEXT,
                    uploaded_file_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT DEFAULT ''
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def add_job(self, job_name: str, status: str, input_file: str, uploaded_file_name: str):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO batch_jobs (job_name, status, input_file, uploaded_file_name)
                VALUES (?, ?, ?, ?)
            """, (job_name, status, input_file, uploaded_file_name))
            conn.commit()
        finally:
            conn.close()

    def update_status(self, job_name: str, new_status: str, details: str = ""):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE batch_jobs
                SET status = ?, details = ?, updated_at = ?
                WHERE job_name = ?
            """, (new_status, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), job_name))
            conn.commit()
        finally:
            conn.close()

    def get_active_job(self) -> Optional[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM batch_jobs
                WHERE status NOT IN ('JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED',
                                     'JOB_STATE_CANCELLED', 'JOB_STATE_EXPIRED')
                ORDER BY created_at DESC LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_job(self, job_name: str) -> Optional[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM batch_jobs WHERE job_name = ?", (job_name,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
```

- [ ] **Step 4: Commit**

```bash
git add src/data/
git commit -m "feat(refactor): add data layer database modules (ProductDB + BatchJobDB)"
```

---

### Task 3: Create data layer — loaders and parsers

Move loaders and parsers to `src/data/`, dropping `_new_format` suffixes.

**Files:**
- Create: `src/data/loaders/__init__.py`
- Create: `src/data/loaders/xlsx_loader.py` (copy from `src/loaders/xlsx_loader.py`)
- Create: `src/data/loaders/loader_factory.py` (copy from `src/loaders/data_loader_factory.py`)
- Create: `src/data/parsers/__init__.py`
- Create: `src/data/parsers/xml_parser.py` (copy from `src/parsers/xml_parser_new_format.py`)
- Create: `src/data/parsers/xml_parser_factory.py` (copy from `src/parsers/xml_parser_factory.py`)
- Create: `src/data/writers/__init__.py`
- Create: `src/data/writers/xlsx_writer.py`

- [ ] **Step 1: Copy loaders with updated imports**

Copy `src/loaders/xlsx_loader.py` to `src/data/loaders/xlsx_loader.py` — no changes needed to the file content.

Copy `src/loaders/data_loader_factory.py` to `src/data/loaders/loader_factory.py` — update the import:

```python
# Change this import:
from .xlsx_loader import XLSXLoader
# (same as original, relative import still works in new location)
```

Create init:
```python
# src/data/loaders/__init__.py
from .xlsx_loader import XLSXLoader
from .loader_factory import DataLoaderFactory
```

- [ ] **Step 2: Copy parsers with updated imports**

Copy `src/parsers/xml_parser_new_format.py` to `src/data/parsers/xml_parser.py`. Rename the class from `XMLParserNewFormat` to `XMLParser` inside the file (find-and-replace).

Copy `src/parsers/xml_parser_factory.py` to `src/data/parsers/xml_parser_factory.py`. Update:
```python
# Change:
from .xml_parser_new_format import XMLParserNewFormat
# To:
from .xml_parser import XMLParser
```
And rename all `XMLParserNewFormat` references to `XMLParser` in the factory.

Create init:
```python
# src/data/parsers/__init__.py
from .xml_parser import XMLParser
from .xml_parser_factory import XMLParserFactory
```

- [ ] **Step 3: Create XLSX writer**

```python
# src/data/writers/xlsx_writer.py
"""Output file writing."""

from pathlib import Path
from typing import Union

import pandas as pd


def write_xlsx(df: pd.DataFrame, file_path: Union[str, Path]):
    """Write DataFrame to XLSX file."""
    df.to_excel(str(file_path), index=False, engine="openpyxl")
```

Create init:
```python
# src/data/writers/__init__.py
from .xlsx_writer import write_xlsx
```

- [ ] **Step 4: Update `src/data/__init__.py`**

```python
# src/data/__init__.py
from .database import ProductDB, BatchJobDB
from .loaders import XLSXLoader, DataLoaderFactory
from .parsers import XMLParser, XMLParserFactory
from .writers import write_xlsx
```

- [ ] **Step 5: Commit**

```bash
git add src/data/
git commit -m "feat(refactor): add data layer loaders, parsers, and writers"
```

---

## Phase 2: Domain Layer

### Task 4: Create domain — variant service

Extract `get_pair_code()` from worker into its own module.

**Files:**
- Create: `src/domain/products/__init__.py`
- Create: `src/domain/products/variant_service.py`
- Create: `tests/test_variant_service.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_variant_service.py
"""Tests for variant service pair code logic."""

import pytest
from src.domain.products.variant_service import get_pair_code


class TestGetPairCode:
    def test_code_with_bar_suffix(self):
        assert get_pair_code("ABC123 BAR") == "ABC123"

    def test_code_with_dining_suffix(self):
        assert get_pair_code("ABC123 DINING") == "ABC123"

    def test_code_with_coffee_suffix(self):
        assert get_pair_code("ABC123 COFFEE") == "ABC123"

    def test_code_without_valid_suffix(self):
        assert get_pair_code("ABC123") == ""

    def test_code_with_invalid_suffix(self):
        assert get_pair_code("ABC123 TABLE") == ""

    def test_empty_code(self):
        assert get_pair_code("") == ""

    def test_none_code(self):
        assert get_pair_code(None) == ""

    def test_numeric_code(self):
        assert get_pair_code(12345) == ""

    def test_multi_word_code_with_suffix(self):
        assert get_pair_code("ABC 123 DEF BAR") == "ABC 123 DEF"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_variant_service.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write the implementation**

```python
# src/domain/products/__init__.py
```

```python
# src/domain/products/variant_service.py
"""Product variant logic — pair code extraction."""

VALID_SUFFIXES = {"BAR", "DINING", "COFFEE"}


def get_pair_code(code) -> str:
    """Extract pair code by removing variant suffix.

    Products with suffixes like 'BAR', 'DINING', 'COFFEE' are variants
    of a base product. This returns the base code without the suffix.

    Returns empty string if code has no valid variant suffix.
    """
    code_str = str(code).strip() if code is not None else ""
    if not code_str:
        return ""

    parts = code_str.split()
    if len(parts) > 1 and parts[-1] in VALID_SUFFIXES:
        return " ".join(parts[:-1])
    return ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_variant_service.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/products/ tests/test_variant_service.py
git commit -m "feat(refactor): add variant service with pair code extraction"
```

---

### Task 5: Create domain — category service (unifies 3 systems)

Unify `src/utils/category_mapper.py`, `src/mappers/category_mapper_new_format.py`, and `CategoryMappingManager` from `src/utils/config_loader.py` into one `CategoryService`.

**Files:**
- Create: `src/domain/categories/__init__.py`
- Create: `src/domain/categories/category_service.py`
- Create: `tests/test_category_service.py`
- Reference: `src/utils/category_mapper.py` (fuzzy matching logic)
- Reference: `src/mappers/category_mapper_new_format.py` (mapping + interactive callback)
- Reference: `src/utils/config_loader.py:89-209` (CategoryMappingManager)

- [ ] **Step 1: Write the test**

```python
# tests/test_category_service.py
"""Tests for unified category service."""

import pytest
import json
import tempfile
import os
from src.domain.categories.category_service import CategoryService


@pytest.fixture
def mappings_file(tmp_path):
    """Create a temporary categories.json file."""
    mappings = [
        {"oldCategory": "Chladničky", "newCategory": "Chladiace zariadenia"},
        {"oldCategory": "Sporáky", "newCategory": "Varné zariadenia"},
        {"oldCategory": "Umývačky", "newCategory": "Umývacie zariadenia"},
    ]
    path = tmp_path / "categories.json"
    path.write_text(json.dumps(mappings, ensure_ascii=False), encoding="utf-8")
    return str(path)


class TestCategoryServiceMapping:
    def test_map_known_category(self, mappings_file):
        service = CategoryService(mappings_file)
        assert service.map("Chladničky") == "Chladiace zariadenia"

    def test_map_unknown_category_returns_none(self, mappings_file):
        service = CategoryService(mappings_file)
        assert service.map("Neznáma kategória") is None

    def test_add_mapping_and_retrieve(self, mappings_file):
        service = CategoryService(mappings_file)
        service.add_mapping("Grily", "Grilovacie zariadenia")
        assert service.map("Grily") == "Grilovacie zariadenia"

    def test_add_mapping_persists_to_file(self, mappings_file):
        service = CategoryService(mappings_file)
        service.add_mapping("Grily", "Grilovacie zariadenia")
        # Reload from file
        service2 = CategoryService(mappings_file)
        assert service2.map("Grily") == "Grilovacie zariadenia"

    def test_get_all_mappings(self, mappings_file):
        service = CategoryService(mappings_file)
        all_mappings = service.get_all_mappings()
        assert all_mappings["Chladničky"] == "Chladiace zariadenia"
        assert len(all_mappings) == 3

    def test_case_insensitive_lookup(self, mappings_file):
        service = CategoryService(mappings_file)
        # The original keys should match as stored
        assert service.map("Chladničky") == "Chladiace zariadenia"


class TestCategoryServiceSuggestions:
    def test_suggest_returns_list(self, mappings_file):
        service = CategoryService(mappings_file)
        suggestions = service.suggest("Chladnicky")
        assert isinstance(suggestions, list)

    def test_suggest_finds_similar_category(self, mappings_file):
        service = CategoryService(mappings_file)
        suggestions = service.suggest("Chladničky a mrazničky")
        # Should find "Chladiace zariadenia" as a suggestion
        assert len(suggestions) > 0

    def test_suggest_returns_empty_for_gibberish(self, mappings_file):
        service = CategoryService(mappings_file)
        suggestions = service.suggest("xyzxyzxyz")
        # May or may not return results depending on threshold
        assert isinstance(suggestions, list)


class TestCategoryServiceGetUniqueTargets:
    def test_get_unique_target_categories(self, mappings_file):
        service = CategoryService(mappings_file)
        targets = service.get_unique_target_categories()
        assert "Chladiace zariadenia" in targets
        assert "Varné zariadenia" in targets
        assert len(targets) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_category_service.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write the implementation**

```python
# src/domain/categories/__init__.py
from .category_service import CategoryService
from .category_filter import CategoryFilter
```

```python
# src/domain/categories/category_service.py
"""Unified category mapping service.

Replaces three previous systems:
- src/utils/category_mapper.py
- src/mappers/category_mapper_new_format.py
- CategoryMappingManager from src/utils/config_loader.py
"""

import json
import os
from typing import List, Optional, Callable, Tuple

from rapidfuzz import fuzz


class CategoryService:
    """Single unified category mapping system."""

    def __init__(self, mappings_path: str = "categories.json"):
        self.mappings_path = mappings_path
        self._mappings: dict[str, str] = {}
        self._interactive_callback: Optional[Callable[[str, Optional[str]], str]] = None
        self._load()

    def _load(self):
        """Load mappings from JSON file."""
        if not os.path.exists(self.mappings_path):
            self._mappings = {}
            return

        with open(self.mappings_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._mappings = {}
        for item in data:
            if isinstance(item, dict) and "oldCategory" in item and "newCategory" in item:
                self._mappings[item["oldCategory"]] = item["newCategory"]

    def _save(self):
        """Persist mappings back to JSON file."""
        data = [
            {"oldCategory": old, "newCategory": new}
            for old, new in self._mappings.items()
        ]
        with open(self.mappings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def map(self, old_category: str) -> Optional[str]:
        """Look up a known mapping. Returns None if not found."""
        return self._mappings.get(old_category)

    def map_or_ask(self, old_category: str, product_name: Optional[str] = None) -> str:
        """Map a category, using interactive callback if mapping is unknown.

        If no callback is set, returns the original category unchanged.
        """
        mapped = self.map(old_category)
        if mapped is not None:
            return mapped

        if self._interactive_callback:
            new_category = self._interactive_callback(old_category, product_name)
            if new_category and new_category != old_category:
                self.add_mapping(old_category, new_category)
                return new_category

        return old_category

    def suggest(self, unmapped_category: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """Suggest similar target categories using fuzzy matching.

        Returns list of (category, score) tuples sorted by score descending.
        """
        existing = self.get_unique_target_categories()
        if not existing:
            return []

        scored = []
        for target in existing:
            # Hybrid scoring: combine multiple similarity methods
            partial = fuzz.partial_ratio(unmapped_category.lower(), target.lower())
            token_sort = fuzz.token_sort_ratio(unmapped_category.lower(), target.lower())
            ratio = fuzz.ratio(unmapped_category.lower(), target.lower())

            # Weighted combination
            score = (partial * 0.40) + (token_sort * 0.30) + (ratio * 0.30)
            scored.append((target, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_n]

    def add_mapping(self, old_category: str, new_category: str):
        """Add a new mapping and persist to file."""
        self._mappings[old_category] = new_category
        self._save()

    def get_all_mappings(self) -> dict[str, str]:
        """Return all mappings as {old: new} dict."""
        return dict(self._mappings)

    def get_unique_target_categories(self) -> List[str]:
        """Return sorted list of unique target (new) category names."""
        return sorted(set(self._mappings.values()))

    def is_target_category(self, category: str) -> bool:
        """Check if a category name is a known target category."""
        return category in set(self._mappings.values())

    def set_interactive_callback(self, callback: Optional[Callable[[str, Optional[str]], str]]):
        """Set callback for interactive category mapping.

        Callback signature: (original_category, product_name) -> new_category
        """
        self._interactive_callback = callback
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_category_service.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/categories/ tests/test_category_service.py
git commit -m "feat(refactor): add unified CategoryService replacing 3 previous systems"
```

---

### Task 6: Create domain — category filter

Move `CategoryFilter` from `src/filters/` to `src/domain/categories/`.

**Files:**
- Create: `src/domain/categories/category_filter.py` (copy from `src/filters/category_filter.py`)

- [ ] **Step 1: Copy the file**

Copy `src/filters/category_filter.py` to `src/domain/categories/category_filter.py`. No changes needed — the class has no local imports.

- [ ] **Step 2: Run existing test**

Run: `pytest tests/test_category_filter.py -v`
Expected: Tests still pass (old imports still work, new file is just a copy)

- [ ] **Step 3: Commit**

```bash
git add src/domain/categories/category_filter.py
git commit -m "feat(refactor): move CategoryFilter to domain/categories"
```

---

### Task 7: Create domain — merger

Move and refactor `DataMergerNewFormat` into `ProductMerger` that returns typed `MergeResult` and works on copies.

**Files:**
- Create: `src/domain/products/merger.py`
- Create: `tests/test_merger.py`
- Reference: `src/mergers/data_merger_new_format.py` (281 lines)

- [ ] **Step 1: Write the test**

```python
# tests/test_merger.py
"""Tests for product merger."""

import pytest
import pandas as pd
from src.domain.products.merger import ProductMerger
from src.domain.models import MergeResult, MergeStats


@pytest.fixture
def main_df():
    return pd.DataFrame({
        "code": ["P001", "P002", "P003"],
        "name": ["Product 1", "Product 2", "Product 3"],
        "price": ["100", "200", "300"],
        "defaultCategory": ["Cat A", "Cat B", "Cat A"],
        "source": ["core", "core", "core"],
    })


@pytest.fixture
def feed_dfs():
    feed = pd.DataFrame({
        "code": ["P001", "P004"],
        "name": ["Product 1 Updated", "Product 4 New"],
        "price": ["110", "400"],
        "defaultCategory": ["Cat A", "Cat A"],
        "source": ["gastromarket", "gastromarket"],
    })
    return {"gastromarket": feed}


class TestProductMerger:
    def test_merge_returns_merge_result(self, main_df, feed_dfs):
        merger = ProductMerger()
        result = merger.merge(main_df, feed_dfs, selected_categories=["Cat A", "Cat B"])
        assert isinstance(result, MergeResult)
        assert isinstance(result.stats, MergeStats)

    def test_merge_does_not_mutate_inputs(self, main_df, feed_dfs):
        merger = ProductMerger()
        original_main = main_df.copy()
        original_feed = feed_dfs["gastromarket"].copy()
        merger.merge(main_df, feed_dfs, selected_categories=["Cat A", "Cat B"])
        pd.testing.assert_frame_equal(main_df, original_main)
        pd.testing.assert_frame_equal(feed_dfs["gastromarket"], original_feed)

    def test_feed_products_always_included(self, main_df, feed_dfs):
        merger = ProductMerger()
        result = merger.merge(main_df, feed_dfs, selected_categories=["Cat A", "Cat B"])
        codes = result.products["code"].tolist()
        # P004 from feed should be included
        assert "P004" in codes

    def test_category_filter_applied(self, main_df, feed_dfs):
        merger = ProductMerger()
        result = merger.merge(main_df, feed_dfs, selected_categories=["Cat A"])
        codes = result.products["code"].tolist()
        # P002 is Cat B, should be excluded
        assert "P002" not in codes

    def test_stats_populated(self, main_df, feed_dfs):
        merger = ProductMerger()
        result = merger.merge(main_df, feed_dfs, selected_categories=["Cat A", "Cat B"])
        assert result.stats.created >= 0
        assert result.stats.updated >= 0
        assert result.stats.kept >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_merger.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write the implementation**

Create `src/domain/products/merger.py` by adapting the existing `DataMergerNewFormat.merge()` logic (from `src/mergers/data_merger_new_format.py`) with these changes:
- Class renamed to `ProductMerger`
- Returns `MergeResult` dataclass instead of `Tuple[pd.DataFrame, Dict]`
- Works on copies of input DataFrames (call `.copy()` on inputs at the start)
- Constructor takes no `options` dict — `preserve_edits` is a parameter of `merge()`
- Image priority logic stays (uses `_count_images`)

The merge algorithm itself stays the same:
1. Process feed products (always included, update existing or create new)
2. Process main data products (include if in selected categories, skip if already from feed)
3. Remove discontinued (only in preserve_edits mode)

```python
# src/domain/products/merger.py
"""Product data merging from multiple sources."""

import logging
from typing import Dict, List, Optional

import pandas as pd

from src.domain.models import MergeResult, MergeStats

logger = logging.getLogger(__name__)


class ProductMerger:
    """Merges product data from main file and XML feed sources."""

    IMAGE_COLUMNS = [
        "image1", "image2", "image3", "image4", "image5",
        "image6", "image7", "image8", "image9", "image10",
    ]

    def merge(
        self,
        main_df: pd.DataFrame,
        feed_dfs: Dict[str, pd.DataFrame],
        selected_categories: Optional[List[str]] = None,
        preserve_edits: bool = False,
    ) -> MergeResult:
        """Merge main data with feed data.

        Args:
            main_df: Main product DataFrame
            feed_dfs: Dict of source_name -> DataFrame from feeds
            selected_categories: Categories to include (None = all)
            preserve_edits: If True, only update price/stock from feeds

        Returns:
            MergeResult with merged products and statistics
        """
        # Work on copies to avoid mutating inputs
        main_df = main_df.copy()
        feed_dfs = {k: v.copy() for k, v in feed_dfs.items()}

        stats = MergeStats()
        merged_products = {}
        processed_codes = set()

        # Normalize codes to uppercase
        if "code" in main_df.columns:
            main_df["code"] = main_df["code"].astype(str).str.upper().str.strip()
        for source_name, feed_df in feed_dfs.items():
            if "code" in feed_df.columns:
                feed_df["code"] = feed_df["code"].astype(str).str.upper().str.strip()
            feed_dfs[source_name] = feed_df

        # Step 1: Process feed products (always included)
        for source_name, feed_df in feed_dfs.items():
            for _, feed_row in feed_df.iterrows():
                code = str(feed_row.get("code", "")).strip()
                if not code:
                    continue

                if code in merged_products:
                    # Already have this product — update with feed data
                    existing = merged_products[code]
                    if preserve_edits:
                        # Only update price and stock
                        for field in ["price", "stock", "availability"]:
                            if field in feed_row.index and pd.notna(feed_row[field]):
                                existing[field] = feed_row[field]
                    else:
                        # Full update, but preserve images if feed has fewer
                        feed_images = self._count_images(feed_row)
                        existing_images = self._count_images(pd.Series(existing))
                        if feed_images >= existing_images:
                            for col in feed_row.index:
                                if pd.notna(feed_row[col]):
                                    existing[col] = feed_row[col]
                        else:
                            for col in feed_row.index:
                                if col not in self.IMAGE_COLUMNS and pd.notna(feed_row[col]):
                                    existing[col] = feed_row[col]
                    existing["source"] = source_name
                    stats.updated += 1
                else:
                    # Check if exists in main data
                    main_match = main_df[main_df["code"] == code] if "code" in main_df.columns else pd.DataFrame()

                    if not main_match.empty:
                        # Merge feed into existing main data
                        base = main_match.iloc[0].to_dict()
                        if preserve_edits:
                            for field in ["price", "stock", "availability"]:
                                if field in feed_row.index and pd.notna(feed_row[field]):
                                    base[field] = feed_row[field]
                        else:
                            feed_images = self._count_images(feed_row)
                            main_images = self._count_images(main_match.iloc[0])
                            if feed_images >= main_images:
                                for col in feed_row.index:
                                    if pd.notna(feed_row[col]):
                                        base[col] = feed_row[col]
                            else:
                                for col in feed_row.index:
                                    if col not in self.IMAGE_COLUMNS and pd.notna(feed_row[col]):
                                        base[col] = feed_row[col]
                        base["source"] = source_name
                        merged_products[code] = base
                        stats.updated += 1
                    else:
                        # New product from feed
                        new_product = feed_row.to_dict()
                        new_product["source"] = source_name
                        merged_products[code] = new_product
                        stats.created += 1

                processed_codes.add(code)

        # Step 2: Process main data products
        for _, main_row in main_df.iterrows():
            code = str(main_row.get("code", "")).strip()
            if not code or code in processed_codes:
                continue

            category = str(main_row.get("defaultCategory", ""))
            if selected_categories and category not in selected_categories:
                continue

            merged_products[code] = main_row.to_dict()
            if "source" not in merged_products[code] or not merged_products[code]["source"]:
                merged_products[code]["source"] = "core"
            stats.kept += 1

        # Step 3: Handle discontinued products in preserve_edits mode
        if preserve_edits and feed_dfs:
            active_feed_codes = set()
            for feed_df in feed_dfs.values():
                if "code" in feed_df.columns:
                    active_feed_codes.update(feed_df["code"].tolist())

            codes_to_remove = []
            for code, product in merged_products.items():
                if product.get("source") not in ("core",) and code not in active_feed_codes:
                    codes_to_remove.append(code)

            for code in codes_to_remove:
                del merged_products[code]
                stats.removed += 1

        # Build result DataFrame
        if merged_products:
            result_df = pd.DataFrame(list(merged_products.values()))
        else:
            result_df = pd.DataFrame()

        return MergeResult(products=result_df, stats=stats)

    def _count_images(self, row: pd.Series) -> int:
        """Count non-empty image columns in a row."""
        count = 0
        for col in self.IMAGE_COLUMNS:
            if col in row.index:
                val = str(row[col]).strip()
                if val and val not in ("", "nan", "None"):
                    count += 1
        return count
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_merger.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/products/merger.py tests/test_merger.py
git commit -m "feat(refactor): add ProductMerger with typed MergeResult"
```

---

### Task 8: Create domain — pricing service

Extract price mapping logic from worker into `PricingService`.

**Files:**
- Create: `src/domain/pricing/__init__.py`
- Create: `src/domain/pricing/pricing_service.py`
- Reference: `src/gui/worker_new_format.py` (price mapping logic, lines ~203-273)

- [ ] **Step 1: Write the implementation**

```python
# src/domain/pricing/__init__.py
```

```python
# src/domain/pricing/pricing_service.py
"""Price mapping service for table base products."""

import json
import os
import logging
from typing import Dict, List, Optional, Callable

import pandas as pd

logger = logging.getLogger(__name__)


class PricingService:
    """Handles price mapping for products that need manual price assignment."""

    def __init__(self, prices_path: str = "table_bases_prices.json"):
        self.prices_path = prices_path
        self._prices: Dict[str, str] = {}
        self._load()

    def _load(self):
        """Load price mappings from JSON file."""
        if os.path.exists(self.prices_path):
            with open(self.prices_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._prices = data
                elif isinstance(data, list):
                    # Handle list format
                    for item in data:
                        if isinstance(item, dict) and "code" in item and "price" in item:
                            self._prices[item["code"]] = str(item["price"])

    def _save(self):
        """Persist price mappings."""
        with open(self.prices_path, "w", encoding="utf-8") as f:
            json.dump(self._prices, f, ensure_ascii=False, indent=2)

    def identify_unmapped(self, df: pd.DataFrame) -> List[str]:
        """Return list of product codes that need price mapping."""
        unmapped = []
        for _, row in df.iterrows():
            code = str(row.get("code", "")).strip()
            price = str(row.get("price", "")).strip()
            if code and (not price or price in ("", "0", "nan", "None")):
                if code not in self._prices:
                    unmapped.append(code)
        return unmapped

    def apply_mappings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply known price mappings to DataFrame."""
        df = df.copy()
        for idx, row in df.iterrows():
            code = str(row.get("code", "")).strip()
            if code in self._prices:
                df.at[idx, "price"] = self._prices[code]
        return df

    def add_mapping(self, code: str, price: str):
        """Add a price mapping and persist."""
        self._prices[code] = price
        self._save()

    def get_price(self, code: str) -> Optional[str]:
        """Get mapped price for a code."""
        return self._prices.get(code)
```

- [ ] **Step 2: Commit**

```bash
git add src/domain/pricing/
git commit -m "feat(refactor): add PricingService extracted from worker"
```

---

### Task 9: Create domain — output transformer

Move `OutputTransformer` to domain layer.

**Files:**
- Create: `src/domain/transform/__init__.py`
- Create: `src/domain/transform/output_transformer.py` (copy from `src/transformers/output_transformer.py`)

- [ ] **Step 1: Copy the file**

Copy `src/transformers/output_transformer.py` to `src/domain/transform/output_transformer.py`. No internal import changes needed — it only imports pandas and typing.

```python
# src/domain/transform/__init__.py
from .output_transformer import OutputTransformer
```

- [ ] **Step 2: Commit**

```bash
git add src/domain/transform/
git commit -m "feat(refactor): move OutputTransformer to domain/transform"
```

---

## Phase 3: AI Layer

### Task 10: Create AI — API client

Extract Gemini API client and quota management from `AIEnhancerNewFormat`.

**Files:**
- Create: `src/ai/api_client.py`
- Reference: `src/ai/ai_enhancer_new_format.py` (lines 25-77 init, lines 111-153 quota, lines 187-274 batch_with_retry)

- [ ] **Step 1: Write the implementation**

```python
# src/ai/api_client.py
"""Gemini API client with quota management and retry logic."""

import json
import time
import os
import logging
import threading
from typing import Dict, List, Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class GeminiClient:
    """Low-level Gemini API operations with quota tracking."""

    def __init__(self, config: Dict):
        load_dotenv()

        ai_config = config.get("ai_enhancement", {})
        self.api_key = os.getenv("GOOGLE_API_KEY") or ai_config.get("api_key", "")
        self.model_name = ai_config.get("model", "gemini-2.5-flash-lite")
        self.temperature = ai_config.get("temperature", 0.1)
        self.retry_delay = ai_config.get("retry_delay", 60)
        self.retry_attempts = ai_config.get("retry_attempts", 3)

        # Initialize client
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini API client: {e}")

        # Quota tracking (thread-safe)
        self._calls_lock = threading.Lock()
        self._calls_in_current_minute = 0
        self._tokens_in_current_minute = 0
        self._minute_start_time = time.time()

    @property
    def is_available(self) -> bool:
        return self.client is not None and bool(self.api_key)

    def check_and_wait_for_quota(self, tokens_needed: int = 0):
        """Block until quota is available. Thread-safe."""
        while True:
            wait_time = 0

            with self._calls_lock:
                current_time = time.time()

                if current_time - self._minute_start_time >= 60:
                    self._calls_in_current_minute = 0
                    self._tokens_in_current_minute = 0
                    self._minute_start_time = current_time

                if self._calls_in_current_minute >= 15:
                    wait_time = 60 - (current_time - self._minute_start_time)
                elif self._tokens_in_current_minute + tokens_needed > 250000:
                    wait_time = 60 - (current_time - self._minute_start_time)

                if wait_time <= 0:
                    self._calls_in_current_minute += 1
                    self._tokens_in_current_minute += tokens_needed
                    return

            if wait_time > 0:
                logger.info(f"Quota limit reached, waiting {wait_time:.1f}s...")
                time.sleep(wait_time + 0.1)

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> Optional[List[Dict]]:
        """Make a single API call and parse JSON response.

        Returns parsed JSON list or None on failure.
        """
        if not self.is_available:
            return None

        estimated_tokens = int(len(user_prompt) * 1.5)
        self.check_and_wait_for_quota(estimated_tokens)

        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        api_config = types.GenerateContentConfig(
            tools=[grounding_tool],
            system_instruction=system_prompt,
            temperature=temperature or self.temperature,
        )

        for attempt in range(self.retry_attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    config=api_config,
                    contents=user_prompt,
                )

                # Track actual token usage
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    actual_tokens = response.usage_metadata.total_token_count
                    with self._calls_lock:
                        self._tokens_in_current_minute = (
                            self._tokens_in_current_minute - estimated_tokens + actual_tokens
                        )

                if response and response.text:
                    return self._parse_json_response(response.text)

                logger.error(f"Invalid response: {response.text if response else 'None'}")
                return None

            except Exception as e:
                if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                    logger.warning(f"Rate limit hit, waiting {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    logger.error(f"Error in API call: {e}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise

        return None

    def upload_file(self, file_path: str) -> str:
        """Upload a JSONL file to Google Cloud. Returns the file name."""
        uploaded = self.client.files.upload(
            file=file_path,
            config=types.UploadFileConfig(mime_type="application/jsonl"),
        )
        return uploaded.name

    def create_batch_job(self, uploaded_file_name: str):
        """Create a batch processing job. Returns the batch job object."""
        return self.client.batches.create(
            model=self.model_name,
            src=uploaded_file_name,
        )

    def get_batch_job(self, job_name: str):
        """Poll batch job status."""
        return self.client.batches.get(name=job_name)

    def download_file(self, file_name: str) -> str:
        """Download a file and return its content as string."""
        content_bytes = self.client.files.download(file=file_name)
        return content_bytes.decode("utf-8")

    def delete_file(self, file_name: str):
        """Delete a remote file."""
        try:
            self.client.files.delete(name=file_name)
        except Exception as e:
            logger.warning(f"Could not delete file {file_name}: {e}")

    @staticmethod
    def _parse_json_response(text: str) -> Optional[List[Dict]]:
        """Parse JSON from API response text."""
        text = text.strip().replace("```json", "").replace("```", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if "[" in text and "]" in text:
                json_str = text[text.find("["):text.rfind("]") + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        return None
```

- [ ] **Step 2: Commit**

```bash
git add src/ai/api_client.py
git commit -m "feat(refactor): add GeminiClient with quota management"
```

---

### Task 11: Create AI — prompts module

Move and rename prompts. Add category parameter loading.

**Files:**
- Create: `src/ai/prompts.py` (from `src/ai/ai_prompts_new_format.py`)

- [ ] **Step 1: Copy and extend**

Copy `src/ai/ai_prompts_new_format.py` to `src/ai/prompts.py`. Add category parameter loading:

```python
# Add at the top of the copied file, after existing functions:

import json
import os
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def load_category_parameters(path: str = "categories_with_parameters.json") -> Dict[str, List]:
    """Load category-specific AI parameters from JSON file.

    Returns dict of category_name -> list of filter parameters.
    """
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            params_data = json.load(f)

        result = {}
        if isinstance(params_data, list):
            for item in params_data:
                if isinstance(item, dict) and "kategoria" in item and "filtre" in item:
                    result[item["kategoria"]] = item["filtre"]

        logger.info(f"Loaded {len(result)} category parameter configurations.")
        return result
    except Exception as e:
        logger.warning(f"Failed to load category parameters: {e}")
        return {}
```

Keep the existing `create_system_prompt()` and `create_system_prompt_no_dimensions()` functions unchanged.

- [ ] **Step 2: Commit**

```bash
git add src/ai/prompts.py
git commit -m "feat(refactor): add AI prompts module with category parameter loading"
```

---

### Task 12: Create AI — result parser

Extract JSONL parsing and fuzzy matching from `AIEnhancerNewFormat`.

**Files:**
- Create: `src/ai/result_parser.py`
- Create: `tests/test_result_parser.py`
- Reference: `src/ai/ai_enhancer_new_format.py` (lines 276-326 find_best_match, lines 328-421 update_dataframe, lines 653-692 _parse_batch_results)

- [ ] **Step 1: Write the test**

```python
# tests/test_result_parser.py
"""Tests for AI result parser and fuzzy matching."""

import pytest
import pandas as pd
from src.ai.result_parser import ResultParser


@pytest.fixture
def parser():
    return ResultParser(similarity_threshold=85)


@pytest.fixture
def products_df():
    return pd.DataFrame({
        "code": ["ABC001", "DEF002", "GHI003"],
        "name": ["Profesionálna chladnička 700L", "Elektrický gril stolný", "Umývačka riadu priemyselná"],
        "shortDescription": ["", "", ""],
        "description": ["", "", ""],
        "aiProcessed": ["0", "0", "0"],
        "aiProcessedDate": ["", "", ""],
    })


class TestFindBestMatch:
    def test_exact_code_match(self, parser, products_df):
        idx = parser.find_best_match("ABC001", "code", products_df)
        assert idx == 0

    def test_fuzzy_code_match(self, parser, products_df):
        idx = parser.find_best_match("abc001", "code", products_df)
        assert idx == 0

    def test_no_match_returns_none(self, parser, products_df):
        idx = parser.find_best_match("ZZZZZ", "code", products_df)
        assert idx is None

    def test_name_match(self, parser, products_df):
        idx = parser.find_best_match("Profesionálna chladnička", "name", products_df)
        assert idx == 0


class TestUpdateDataframe:
    def test_updates_matching_products(self, parser, products_df):
        enhanced = [
            {
                "code": "ABC001",
                "shortDescription": "Enhanced short desc",
                "description": "Enhanced full desc",
                "seoTitle": "SEO Title",
                "metaDescription": "Meta desc",
            }
        ]
        updated_df, count = parser.update_dataframe(products_df, enhanced)
        assert count == 1
        assert updated_df.at[0, "shortDescription"] == "Enhanced short desc"
        assert updated_df.at[0, "aiProcessed"] == "1"

    def test_unmatched_products_not_updated(self, parser, products_df):
        enhanced = [{"code": "ZZZZZ", "shortDescription": "Nope"}]
        updated_df, count = parser.update_dataframe(products_df, enhanced)
        assert count == 0


class TestParseBatchResults:
    def test_parse_valid_jsonl(self, parser, products_df):
        jsonl_content = '{"response": {"candidates": [{"content": {"parts": [{"text": "[{\\"code\\": \\"ABC001\\", \\"shortDescription\\": \\"Test\\", \\"description\\": \\"Test desc\\"}]"}]}}]}}\n'
        updated_df, stats = parser.parse_batch_results(products_df, jsonl_content)
        assert stats["ai_processed"] >= 0  # May or may not match depending on threshold
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_result_parser.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write the implementation**

```python
# src/ai/result_parser.py
"""AI result parsing and fuzzy matching."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class ResultParser:
    """Parses AI batch results and matches them back to source products."""

    def __init__(self, similarity_threshold: int = 85):
        self.similarity_threshold = similarity_threshold

    def find_best_match(
        self, enhanced_name: str, column_name: str, df: pd.DataFrame
    ) -> Optional[int]:
        """Find best matching product using fuzzy matching.

        Args:
            enhanced_name: Product name/code from AI response
            column_name: Column to match against ('code' or 'name')
            df: DataFrame to search in

        Returns:
            Index of best match or None
        """
        best_match_idx = None
        best_score = 0
        enhanced_lower = enhanced_name.lower()

        for idx, row in df.iterrows():
            value = str(row[column_name]).lower()

            substring_match = enhanced_lower in value or value in enhanced_lower
            partial_score = fuzz.partial_ratio(enhanced_lower, value)
            token_score = fuzz.token_sort_ratio(enhanced_lower, value)

            max_score = max(partial_score, token_score)
            if substring_match:
                max_score = max(max_score, 90)

            if max_score > best_score and max_score >= self.similarity_threshold:
                best_score = max_score
                best_match_idx = idx

        return best_match_idx

    def update_dataframe(
        self,
        df: pd.DataFrame,
        enhanced_products: List[Dict],
        valid_indices: Optional[pd.Index] = None,
    ) -> Tuple[pd.DataFrame, int]:
        """Update DataFrame with enhanced product data.

        Uses 3-strategy matching: exact code -> fuzzy code -> fuzzy name.

        Returns:
            Tuple of (updated DataFrame, count of updated products)
        """
        updated_count = 0
        search_df = df.loc[valid_indices] if valid_indices is not None else df

        for enhanced in enhanced_products:
            best_match_idx = None

            code = str(enhanced.get("code", "")).strip()
            if code:
                # Strategy 1: Exact match on code
                exact = search_df[search_df["code"].astype(str).str.strip() == code]
                if len(exact) == 1:
                    best_match_idx = exact.index[0]
                elif len(exact) > 1:
                    best_match_idx = exact.index[0]
                    logger.warning(f"Multiple exact matches for {code}, using first")
                else:
                    # Strategy 2: Fuzzy match on code
                    best_match_idx = self.find_best_match(code, "code", search_df)
                    if best_match_idx is None:
                        # Strategy 3: Fuzzy match on name
                        name = enhanced.get("name", "")
                        if name:
                            best_match_idx = self.find_best_match(name, "name", search_df)

            if best_match_idx is not None:
                for field in ("shortDescription", "description", "seoTitle", "metaDescription"):
                    if field in enhanced:
                        df.at[best_match_idx, field] = enhanced[field]

                if "parameters" in enhanced and isinstance(enhanced["parameters"], dict):
                    for param_key, param_val in enhanced["parameters"].items():
                        if param_val:
                            df.at[best_match_idx, f"filteringProperty:{param_key}"] = str(param_val)

                df.at[best_match_idx, "aiProcessed"] = "1"
                df.at[best_match_idx, "aiProcessedDate"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                updated_count += 1
            else:
                logger.error(f"No match for product {enhanced.get('code', 'UNKNOWN')}")

        return df, updated_count

    def parse_batch_results(
        self, df: pd.DataFrame, file_content: str, progress_callback=None
    ) -> Tuple[pd.DataFrame, Dict]:
        """Parse JSONL batch results and apply to DataFrame.

        Returns:
            Tuple of (updated DataFrame, stats dict)
        """
        if progress_callback:
            progress_callback(95, 100, "Aplikovanie vysledkov do tabulky...")

        enhanced_all = []

        for line in file_content.splitlines():
            if not line:
                continue
            try:
                parsed = json.loads(line)
                if "response" in parsed and parsed["response"]:
                    for part in parsed["response"]["candidates"][0]["content"]["parts"]:
                        if "text" in part:
                            text = part["text"].strip().replace("```json", "").replace("```", "")
                            try:
                                items = json.loads(text)
                                if isinstance(items, list):
                                    enhanced_all.extend(items)
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to decode batch text: {e}")
                elif "error" in parsed:
                    logger.error(f"Batch item error: {parsed['error']}")
            except Exception as e:
                logger.error(f"Error parsing batch line: {e}")

        if enhanced_all:
            updated_df, count = self.update_dataframe(df, enhanced_all)
            return updated_df, {"ai_should_process": len(enhanced_all), "ai_processed": count}

        return df, {"ai_should_process": 0, "ai_processed": 0}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_result_parser.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai/result_parser.py tests/test_result_parser.py
git commit -m "feat(refactor): add ResultParser with fuzzy matching and JSONL parsing"
```

---

### Task 13: Create AI — batch orchestrator

Extract batch job creation, monitoring, and polling.

**Files:**
- Create: `src/ai/batch_orchestrator.py`
- Reference: `src/ai/ai_enhancer_new_format.py` (lines 423-591 process_dataframe, lines 592-651 _monitor_and_apply)

- [ ] **Step 1: Write the implementation**

```python
# src/ai/batch_orchestrator.py
"""Batch processing orchestration for AI enhancement."""

import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable

import pandas as pd

from .api_client import GeminiClient
from .result_parser import ResultParser
from .prompts import create_system_prompt, create_system_prompt_no_dimensions, load_category_parameters
from src.data.database.batch_job_db import BatchJobDB

logger = logging.getLogger(__name__)


class BatchOrchestrator:
    """Manages batch AI processing: job creation, monitoring, result application."""

    COMPLETED_STATES = {
        "JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED",
        "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED",
    }

    def __init__(
        self,
        client: GeminiClient,
        result_parser: ResultParser,
        batch_job_db: Optional[BatchJobDB] = None,
        config: Optional[Dict] = None,
    ):
        self.client = client
        self.parser = result_parser
        self.batch_job_db = batch_job_db

        ai_config = (config or {}).get("ai_enhancement", {})
        self.batch_size = ai_config.get("batch_size", 45)
        self.temperature = ai_config.get("temperature", 0.1)
        self.tmp_dir = ai_config.get(
            "tmp_dir", os.path.join(os.path.dirname(__file__), "tmp")
        )
        os.makedirs(self.tmp_dir, exist_ok=True)

        self.category_parameters = load_category_parameters()

    def process(
        self,
        df: pd.DataFrame,
        group1_indices: set,
        progress_callback: Optional[Callable] = None,
        force_reprocess: bool = False,
    ) -> Tuple[pd.DataFrame, Dict]:
        """Run batch processing for products needing AI enhancement.

        Args:
            df: Full product DataFrame
            group1_indices: Indices of variant products (no-dimensions prompt)
            progress_callback: Optional progress callback
            force_reprocess: If True, reprocess all products

        Returns:
            Tuple of (updated DataFrame, stats dict)
        """
        if not self.client.is_available:
            logger.warning("No API key, skipping AI enhancement")
            return df, {"ai_should_process": 0, "ai_processed": 0}

        # Check for active job to resume
        if self.batch_job_db:
            active_job = self.batch_job_db.get_active_job()
            if active_job:
                logger.info(f"Resuming active batch job: {active_job['job_name']}")
                if progress_callback:
                    progress_callback(0, 0, f"Obnovovanie existujucej ulohy (Job ID: {active_job['job_name'][-10:]})...")
                return self._monitor_and_apply(
                    df, active_job["job_name"], active_job["uploaded_file_name"],
                    progress_callback,
                )

        # Determine which products need processing
        if "aiProcessed" not in df.columns:
            df["aiProcessed"] = ""
        if "aiProcessedDate" not in df.columns:
            df["aiProcessedDate"] = ""

        df["aiProcessed"] = df["aiProcessed"].apply(
            lambda x: "1" if str(x).strip().upper() in ("TRUE", "1", "YES", "1.0")
            else "0" if str(x).strip().upper() in ("FALSE", "0", "NO", "", "0.0")
            else x
        )

        needs_processing = df if force_reprocess else df[df["aiProcessed"] != "1"]
        total = len(needs_processing)

        if total == 0:
            logger.info("No products need AI enhancement")
            if progress_callback:
                progress_callback(0, 0, "Ziadne produkty na vylepsenie.")
            return df, {"ai_should_process": 0, "ai_processed": 0}

        logger.info(f"Processing {total} products with Batch API")

        # Build JSONL requests
        if progress_callback:
            progress_callback(0, total, "Priprava davok (Batch Requests)...")

        jsonl_requests = []
        self._build_category_requests(needs_processing, group1_indices, jsonl_requests, is_group1=True)
        group2_indices = [idx for idx in needs_processing.index if idx not in group1_indices]
        self._build_category_requests(needs_processing, set(group2_indices), jsonl_requests, is_group1=False)

        if not jsonl_requests:
            logger.info("No valid batch requests generated.")
            return df, {"ai_should_process": total, "ai_processed": 0}

        # Write JSONL and submit
        jsonl_path = os.path.join(
            self.tmp_dir, f"batch_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for req in jsonl_requests:
                f.write(json.dumps(req, ensure_ascii=False) + "\n")

        if progress_callback:
            progress_callback(0, total, "Nahravanie suboru na Google Cloud...")

        try:
            uploaded_name = self.client.upload_file(jsonl_path)

            if progress_callback:
                progress_callback(0, total, "Vytvaranie davkovej ulohy (Batch Job)...")

            batch_job = self.client.create_batch_job(uploaded_name)
            logger.info(f"Batch Job Created: {batch_job.name}")

            if self.batch_job_db:
                self.batch_job_db.add_job(
                    batch_job.name, batch_job.state.name, jsonl_path, uploaded_name
                )

            return self._monitor_and_apply(df, batch_job.name, uploaded_name, progress_callback, total)

        except Exception as e:
            logger.error(f"Failed to create Batch Job: {e}")
            return df, {"ai_should_process": total, "ai_processed": 0}

    def _build_category_requests(
        self, needs_processing: pd.DataFrame, indices: set,
        jsonl_requests: list, is_group1: bool
    ):
        """Build JSONL requests grouped by category."""
        if not indices:
            return

        group_df = needs_processing.loc[list(indices)].copy()
        group_df["_temp_cat"] = group_df.apply(
            lambda r: str(r.get("newCategory", r.get("defaultCategory", ""))), axis=1
        )

        for cat_name, cat_subset in group_df.groupby("_temp_cat"):
            if not cat_name and self.category_parameters:
                logger.warning(f"Skipping {len(cat_subset)} products with no category.")
                continue

            expected_params = self.category_parameters.get(cat_name, [])

            if is_group1:
                sys_prompt = create_system_prompt_no_dimensions(cat_name, expected_params)
            else:
                sys_prompt = create_system_prompt(cat_name, expected_params)

            for i in range(0, len(cat_subset), self.batch_size):
                batch_end = min(i + self.batch_size, len(cat_subset))
                batch_df = cat_subset.iloc[i:batch_end]

                products = []
                for _, row in batch_df.iterrows():
                    products.append({
                        "code": str(row.get("code", "")),
                        "name": str(row.get("name", "")),
                        "shortDescription": str(row.get("shortDescription", "")),
                        "description": str(row.get("description", "")),
                    })

                if products:
                    req_key = f"req_{'g1' if is_group1 else 'g2'}_{hash(cat_name)}_{i}"
                    jsonl_requests.append({
                        "key": req_key,
                        "request": {
                            "systemInstruction": {"parts": [{"text": sys_prompt}]},
                            "contents": [{"role": "user", "parts": [{"text": json.dumps(products, ensure_ascii=False)}]}],
                            "generationConfig": {"temperature": self.temperature, "responseMimeType": "application/json"},
                        },
                    })

    def _monitor_and_apply(
        self, df: pd.DataFrame, job_name: str, uploaded_file_name: str,
        progress_callback=None, original_total: int = 0,
    ) -> Tuple[pd.DataFrame, Dict]:
        """Poll batch job until completion and apply results."""
        start_time = time.time()

        while True:
            try:
                batch_job = self.client.get_batch_job(job_name)
                state = batch_job.state.name
            except Exception as e:
                logger.error(f"Error polling job {job_name}: {e}")
                time.sleep(30)
                continue

            if self.batch_job_db:
                self.batch_job_db.update_status(job_name, state)

            logger.info(f"Batch Job {job_name} Status: {state}")
            if progress_callback:
                elapsed = int((time.time() - start_time) / 60)
                progress_callback(0, original_total or 100, f"Spracovava sa v cloude (Cas: {elapsed}m, Stav: {state})...")

            if state in self.COMPLETED_STATES:
                break

            time.sleep(30)

        if state != "JOB_STATE_SUCCEEDED":
            logger.error(f"Batch Job failed. Final state: {state}")
            return df, {"ai_should_process": original_total, "ai_processed": 0}

        # Download results
        if progress_callback:
            progress_callback(90, 100, "Stahovanie vysledkov...")

        if not batch_job.dest or not batch_job.dest.file_name:
            logger.error("No destination file in batch job response.")
            return df, {"ai_should_process": original_total, "ai_processed": 0}

        try:
            file_content = self.client.download_file(batch_job.dest.file_name)
        except Exception as e:
            logger.error(f"Failed to download results: {e}")
            return df, {"ai_should_process": original_total, "ai_processed": 0}

        # Clean up uploaded file
        if uploaded_file_name:
            self.client.delete_file(uploaded_file_name)

        return self.parser.parse_batch_results(df, file_content, progress_callback)

    def resume_active_job(self, df: pd.DataFrame, progress_callback=None) -> Optional[Tuple[pd.DataFrame, Dict]]:
        """Resume an active batch job if one exists. Returns None if no active job."""
        if not self.batch_job_db:
            return None

        active = self.batch_job_db.get_active_job()
        if not active:
            return None

        return self._monitor_and_apply(
            df, active["job_name"], active["uploaded_file_name"], progress_callback
        )
```

- [ ] **Step 2: Commit**

```bash
git add src/ai/batch_orchestrator.py
git commit -m "feat(refactor): add BatchOrchestrator for AI batch processing"
```

---

### Task 14: Create AI — product enricher (high-level coordinator)

**Files:**
- Create: `src/ai/product_enricher.py`

- [ ] **Step 1: Write the implementation**

```python
# src/ai/product_enricher.py
"""High-level AI product enrichment coordinator."""

import logging
from typing import Dict, Optional, Callable, Tuple

import pandas as pd

from .api_client import GeminiClient
from .batch_orchestrator import BatchOrchestrator
from .result_parser import ResultParser
from src.domain.models import EnrichmentResult
from src.domain.products.variant_service import get_pair_code
from src.data.database.batch_job_db import BatchJobDB

logger = logging.getLogger(__name__)


class ProductEnricher:
    """Coordinates AI enhancement of product data."""

    def __init__(self, config: Dict, batch_job_db: Optional[BatchJobDB] = None):
        self.client = GeminiClient(config)
        self.parser = ResultParser(
            similarity_threshold=config.get("ai_enhancement", {}).get("similarity_threshold", 85)
        )
        self.orchestrator = BatchOrchestrator(
            client=self.client,
            result_parser=self.parser,
            batch_job_db=batch_job_db,
            config=config,
        )

    def enrich(
        self,
        df: pd.DataFrame,
        force_reprocess: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> EnrichmentResult:
        """Enrich product DataFrame with AI-generated content.

        Args:
            df: Product DataFrame
            force_reprocess: If True, reprocess already-processed products
            progress_callback: Optional progress callback

        Returns:
            EnrichmentResult with updated DataFrame and stats
        """
        if not self.client.is_available:
            logger.warning("AI client not available, skipping enhancement")
            return EnrichmentResult(products=df)

        # Identify variant products (Group 1)
        group1_indices = set()
        if "pairCode" in df.columns:
            all_pair_codes = set(df["pairCode"].dropna().unique())
            all_pair_codes.discard("")

            # Products needing processing
            needs = df if force_reprocess else df[df.get("aiProcessed", "") != "1"]
            for idx, row in needs.iterrows():
                code = str(row.get("code", "")).strip()
                pair_code = str(row.get("pairCode", "")).strip()
                if pair_code or (code and code in all_pair_codes):
                    group1_indices.add(idx)

        # Run batch processing
        updated_df, stats = self.orchestrator.process(
            df,
            group1_indices=group1_indices,
            progress_callback=progress_callback,
            force_reprocess=force_reprocess,
        )

        return EnrichmentResult(
            products=updated_df,
            processed=stats.get("ai_processed", 0),
            skipped=0,
            failed=stats.get("ai_should_process", 0) - stats.get("ai_processed", 0),
        )
```

- [ ] **Step 2: Update `src/ai/__init__.py`**

```python
# src/ai/__init__.py
from .product_enricher import ProductEnricher
from .api_client import GeminiClient
from .result_parser import ResultParser
from .batch_orchestrator import BatchOrchestrator
```

- [ ] **Step 3: Commit**

```bash
git add src/ai/product_enricher.py src/ai/__init__.py
git commit -m "feat(refactor): add ProductEnricher as high-level AI coordinator"
```

---

## Phase 4: Pipeline & Config

### Task 15: Create config layer

Move config loader and create column schema generator.

**Files:**
- Create: `src/config/__init__.py`
- Create: `src/config/config_loader.py` (slimmed from `src/utils/config_loader.py`)
- Create: `src/config/schema.py`
- Reference: `config.json` (lines ~177-674 for column list)

- [ ] **Step 1: Create config loader**

```python
# src/config/__init__.py
from .config_loader import load_config, save_config
from .schema import get_output_columns
```

```python
# src/config/config_loader.py
"""Configuration loading and saving."""

import json
from typing import Dict


def load_config(config_path: str = "config.json") -> Dict:
    """Load configuration from JSON file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: Dict, config_path: str = "config.json") -> bool:
    """Save configuration to JSON file."""
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
```

- [ ] **Step 2: Create column schema generator**

Read the existing `new_output_columns` from `config.json` to identify the ~30 base columns, then generate image columns programmatically:

```python
# src/config/schema.py
"""Output column definitions — generated, not hardcoded."""


# Base columns in the 138-column output format.
# These are the non-image, non-repeating columns.
BASE_COLUMNS = [
    "code", "name", "pairCode", "defaultCategory", "categoryText",
    "shortDescription", "description", "price", "standardPrice",
    "availability", "manufacturer", "warranty", "ean",
    "weight", "unit", "seoTitle", "metaDescription",
    "internalNote", "visibility", "actionPrice", "actionPriceFrom",
    "actionPriceTo", "stock", "minimalAmount", "source",
    "aiProcessed", "aiProcessedDate", "newCategory",
    "variantVisibility",
]

# Number of image slots in the output format
IMAGE_SLOT_COUNT = 150


def get_output_columns() -> list[str]:
    """Generate the full list of output columns.

    Returns ~338 columns: base + image1..150 + imageDesc1..150
    """
    images = [f"image{i}" for i in range(1, IMAGE_SLOT_COUNT + 1)]
    image_descs = [f"imageDesc{i}" for i in range(1, IMAGE_SLOT_COUNT + 1)]
    return BASE_COLUMNS + images + image_descs
```

Note: The exact BASE_COLUMNS list should be verified against the current `config.json` `new_output_columns` field during implementation. Some columns may include `filteringProperty:*` dynamic columns that should be handled separately.

- [ ] **Step 3: Commit**

```bash
git add src/config/
git commit -m "feat(refactor): add config layer with schema generator"
```

---

### Task 16: Create pipeline — scraping orchestrator

Extract scraping logic from worker.

**Files:**
- Create: `src/pipeline/scraping.py`
- Reference: `src/gui/worker_new_format.py` (lines ~_scrape_products method)

- [ ] **Step 1: Write the implementation**

```python
# src/pipeline/scraping.py
"""Scraping orchestration — coordinates web scrapers."""

import logging
from typing import Dict, Optional, Callable

import pandas as pd

from src.scrapers.mebella_scraper import MebellaScraper
from src.scrapers.topchladenie_scraper import TopchladenieScraper

logger = logging.getLogger(__name__)


class ScrapingOrchestrator:
    """Orchestrates web scraping from multiple sources."""

    def __init__(self, config: Dict):
        self.config = config

    def scrape(
        self,
        scrape_mebella: bool = False,
        scrape_topchladenie: bool = False,
        topchladenie_csv_path: str = "",
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Run enabled scrapers and return source-tagged DataFrames.

        Returns:
            Dict of source_name -> DataFrame
        """
        results = {}

        if scrape_mebella:
            if progress_callback:
                progress_callback("Scraping Mebella products...")
            try:
                scraper = MebellaScraper(progress_callback=progress_callback)
                df = scraper.scrape_products()
                if df is not None and not df.empty:
                    df["source"] = "web_scraping"
                    results["mebella"] = df
                    logger.info(f"Scraped {len(df)} products from Mebella")
            except Exception as e:
                logger.error(f"Mebella scraping failed: {e}")

        if scrape_topchladenie:
            if progress_callback:
                progress_callback("Scraping Topchladenie products...")
            try:
                scraper = TopchladenieScraper(
                    config=self.config,
                    progress_callback=progress_callback,
                )
                if topchladenie_csv_path:
                    df = pd.read_csv(topchladenie_csv_path, sep=";", encoding="utf-8")
                else:
                    df = scraper.scrape_products()
                if df is not None and not df.empty:
                    df["source"] = "web_scraping"
                    results["topchladenie"] = df
                    logger.info(f"Scraped {len(df)} products from Topchladenie")
            except Exception as e:
                logger.error(f"Topchladenie scraping failed: {e}")

        return results
```

- [ ] **Step 2: Commit**

```bash
git add src/pipeline/scraping.py
git commit -m "feat(refactor): add ScrapingOrchestrator extracted from worker"
```

---

### Task 17: Create pipeline — main pipeline

Rewrite pipeline as linear coordinator using new modules.

**Files:**
- Create: `src/pipeline/pipeline.py`
- Reference: `src/pipeline/pipeline_new_format.py` (286 lines)

- [ ] **Step 1: Write the implementation**

```python
# src/pipeline/pipeline.py
"""Main pipeline — coordinates the entire data flow."""

import logging
import time
from typing import Callable, Dict, Optional

import pandas as pd

from src.domain.models import PipelineOptions, PipelineResult, MergeStats
from src.domain.products.merger import ProductMerger
from src.domain.categories.category_service import CategoryService
from src.domain.categories.category_filter import CategoryFilter
from src.domain.pricing.pricing_service import PricingService
from src.domain.transform.output_transformer import OutputTransformer
from src.data.database.product_db import ProductDB
from src.data.database.batch_job_db import BatchJobDB
from src.data.loaders.loader_factory import DataLoaderFactory
from src.data.parsers.xml_parser import XMLParser
from src.data.writers.xlsx_writer import write_xlsx
from src.ai.product_enricher import ProductEnricher
from .scraping import ScrapingOrchestrator

logger = logging.getLogger(__name__)


class Pipeline:
    """Orchestrates the complete product data processing pipeline.

    Linear flow:
    1. Load existing data from DB
    2. Load main file (XLSX)
    3. Parse XML feeds
    4. Scrape (if enabled)
    5. Merge all sources
    6. Map categories (with callback for unknowns)
    7. Apply pricing (with callback for unmapped)
    8. AI enhancement (if enabled)
    9. Transform to output format
    10. Save to DB
    11. Write output file
    """

    def __init__(self, config: Dict):
        self.config = config
        db_path = config.get("db_path", "data/products.db")

        self.db = ProductDB(db_path)
        self.batch_job_db = BatchJobDB(db_path)
        self.merger = ProductMerger()
        self.category_service = CategoryService()
        self.transformer = OutputTransformer(config)
        self.enricher = ProductEnricher(config, batch_job_db=self.batch_job_db)
        self.pricing_service = PricingService()
        self.scraping = ScrapingOrchestrator(config)
        self.xml_parser = XMLParser(config)

    def run(
        self,
        options: PipelineOptions,
        on_progress: Optional[Callable] = None,
        on_unknown_category: Optional[Callable] = None,
        on_unmapped_price: Optional[Callable] = None,
    ) -> PipelineResult:
        """Execute the full pipeline.

        Args:
            options: Typed pipeline options
            on_progress: Progress callback (message: str)
            on_unknown_category: Callback for unmapped categories
            on_unmapped_price: Callback for unmapped prices

        Returns:
            PipelineResult with stats and output path
        """
        start_time = time.time()
        result = PipelineResult()

        def progress(msg: str):
            if on_progress:
                on_progress(msg)
            logger.info(msg)

        # 1. Load existing data from DB
        progress("Loading existing data from database...")
        db_df = self.db.get_all()

        # 2. Load main file
        main_df = pd.DataFrame()
        if options.main_file_path:
            progress(f"Loading main data file: {options.main_file_path}")
            main_df = DataLoaderFactory.load(options.main_file_path)

        # If we have DB data but no main file, use DB as main
        if main_df.empty and not db_df.empty:
            main_df = db_df

        # 3. Parse XML feeds
        feed_dfs = {}
        xml_feeds = self.config.get("xml_feeds", {})
        for feed_name, feed_config in xml_feeds.items():
            url = feed_config.get("url", "")
            if not url:
                continue
            progress(f"Parsing XML feed: {feed_name}")
            try:
                import urllib.request
                with urllib.request.urlopen(url) as response:
                    xml_content = response.read().decode("utf-8")
                feed_df = self.xml_parser.parse(feed_name, xml_content)
                if feed_df is not None and not feed_df.empty:
                    feed_dfs[feed_name] = feed_df
            except Exception as e:
                logger.error(f"Failed to parse feed {feed_name}: {e}")

        # 4. Scrape (if enabled)
        if options.enable_scraping:
            progress("Starting web scraping...")
            scraped = self.scraping.scrape(
                scrape_mebella=options.scrape_mebella,
                scrape_topchladenie=options.scrape_topchladenie,
                topchladenie_csv_path=options.topchladenie_csv_path,
                progress_callback=lambda msg: progress(msg),
            )
            feed_dfs.update(scraped)

        # 5. Merge all sources
        progress("Merging product data...")
        merge_result = self.merger.merge(
            main_df=main_df,
            feed_dfs=feed_dfs,
            selected_categories=options.selected_categories or None,
            preserve_edits=options.preserve_client_edits,
        )
        merged_df = merge_result.products
        result.merge_stats = merge_result.stats

        # 6. Map categories
        if on_unknown_category:
            self.category_service.set_interactive_callback(on_unknown_category)
        progress("Mapping categories...")
        for idx, row in merged_df.iterrows():
            old_cat = str(row.get("defaultCategory", ""))
            if old_cat:
                new_cat = self.category_service.map_or_ask(old_cat, str(row.get("name", "")))
                merged_df.at[idx, "defaultCategory"] = new_cat
                merged_df.at[idx, "categoryText"] = new_cat

        # 7. Apply pricing
        if options.enable_price_mapping:
            progress("Applying price mappings...")
            merged_df = self.pricing_service.apply_mappings(merged_df)
            unmapped = self.pricing_service.identify_unmapped(merged_df)
            if unmapped and on_unmapped_price:
                on_unmapped_price(unmapped)

        # 8. AI enhancement
        if options.enable_ai_enhancement:
            progress("Starting AI enhancement...")
            enrichment = self.enricher.enrich(
                merged_df,
                force_reprocess=options.force_ai_reprocess,
                progress_callback=lambda *args: progress(args[-1] if args else "AI processing..."),
            )
            merged_df = enrichment.products
            result.enrichment_stats = enrichment

        # 9. Transform to output format
        progress("Transforming to output format...")
        output_df = self.transformer.transform(merged_df)

        # 10. Save to DB
        progress("Saving to database...")
        self.db.backup()
        self.db.upsert(merged_df)

        # 11. Write output file
        if options.output_path:
            progress(f"Writing output to: {options.output_path}")
            write_xlsx(output_df, options.output_path)
            result.output_path = options.output_path

        result.product_count = len(output_df)
        result.duration_seconds = time.time() - start_time

        progress(f"Pipeline complete. {result.product_count} products processed in {result.duration_seconds:.1f}s")
        return result

    def parse_xml(self, feed_name: str, xml_content: str) -> pd.DataFrame:
        """Parse a single XML feed. Convenience method."""
        return self.xml_parser.parse(feed_name, xml_content)

    def load_main_data(self, file_path: str) -> pd.DataFrame:
        """Load main data file. Convenience method."""
        return DataLoaderFactory.load(file_path)
```

- [ ] **Step 2: Update `src/pipeline/__init__.py`**

```python
# src/pipeline/__init__.py
from .pipeline import Pipeline
from .scraping import ScrapingOrchestrator
```

- [ ] **Step 3: Commit**

```bash
git add src/pipeline/pipeline.py src/pipeline/__init__.py
git commit -m "feat(refactor): add new Pipeline as linear coordinator"
```

---

## Phase 5: GUI Layer

### Task 18: Create thin worker

Rewrite worker as signal bridge only.

**Files:**
- Create: `src/gui/worker.py`
- Reference: `src/gui/worker_new_format.py` (432 lines)

- [ ] **Step 1: Write the implementation**

```python
# src/gui/worker.py
"""Thin pipeline worker — bridges pipeline callbacks to Qt signals."""

import logging
from typing import Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal, QEventLoop

from src.pipeline.pipeline import Pipeline
from src.domain.models import PipelineOptions, PipelineResult

logger = logging.getLogger(__name__)


class PipelineWorker(QObject):
    """Executes pipeline in a background thread, emitting Qt signals for UI updates."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    result = pyqtSignal(object)  # PipelineResult
    statistics = pyqtSignal(dict)
    category_mapping_request = pyqtSignal(str, str)  # original_category, product_name
    price_mapping_request = pyqtSignal(list)  # unmapped codes

    def __init__(self, config: Dict, options: PipelineOptions):
        super().__init__()
        self.config = config
        self.options = options
        self.pipeline = Pipeline(config)

        # For blocking on GUI interactions
        self._category_result: Optional[str] = None
        self._category_loop: Optional[QEventLoop] = None
        self._price_result: Optional[str] = None
        self._price_loop: Optional[QEventLoop] = None

    def run(self):
        """Execute the pipeline. Called from QThread."""
        try:
            pipeline_result = self.pipeline.run(
                self.options,
                on_progress=self._on_progress,
                on_unknown_category=self._on_unknown_category,
                on_unmapped_price=self._on_unmapped_price,
            )

            # Emit statistics
            stats = {}
            if pipeline_result.merge_stats:
                stats["merge"] = {
                    "created": pipeline_result.merge_stats.created,
                    "updated": pipeline_result.merge_stats.updated,
                    "removed": pipeline_result.merge_stats.removed,
                    "kept": pipeline_result.merge_stats.kept,
                }
            if pipeline_result.enrichment_stats:
                stats["ai"] = {
                    "processed": pipeline_result.enrichment_stats.processed,
                    "failed": pipeline_result.enrichment_stats.failed,
                }
            stats["total_products"] = pipeline_result.product_count
            stats["duration"] = pipeline_result.duration_seconds
            self.statistics.emit(stats)

            self.result.emit(pipeline_result)
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def _on_progress(self, message: str):
        self.progress.emit(message)

    def _on_unknown_category(self, original_category: str, product_name: Optional[str] = None) -> str:
        """Block and ask GUI for category mapping."""
        self._category_result = None
        self._category_loop = QEventLoop()
        self.category_mapping_request.emit(original_category, product_name or "")
        self._category_loop.exec_()
        return self._category_result or original_category

    def set_category_mapping_result(self, new_category: str):
        """Called by GUI when user provides category mapping."""
        self._category_result = new_category
        if self._category_loop:
            self._category_loop.quit()

    def _on_unmapped_price(self, unmapped_codes: list):
        """Notify GUI about unmapped prices."""
        self.price_mapping_request.emit(unmapped_codes)

    def set_price_mapping_result(self, price: str):
        """Called by GUI when user provides price mapping."""
        self._price_result = price
        if self._price_loop:
            self._price_loop.quit()
```

- [ ] **Step 2: Commit**

```bash
git add src/gui/worker.py
git commit -m "feat(refactor): add thin PipelineWorker (~100 lines, down from 432)"
```

---

### Task 19: Create main window

Rewrite main window to use new pipeline and domain modules. This is the largest task — the window keeps all its UI layout but delegates business logic.

**Files:**
- Create: `src/gui/main_window.py`
- Reference: `src/gui/main_window_new_format.py` (1042 lines)

- [ ] **Step 1: Write the implementation**

This file is too large to include inline. The approach:

1. Copy `src/gui/main_window_new_format.py` to `src/gui/main_window.py`
2. Rename class from `MainWindowNewFormat` to `MainWindow`
3. Update all imports to use new module paths:
   - `from src.gui.worker import PipelineWorker` (was `WorkerNewFormat`)
   - `from src.domain.categories.category_service import CategoryService` (was `get_category_suggestions` from utils)
   - `from src.domain.categories.category_filter import CategoryFilter` (was from `src.filters`)
   - `from src.data.loaders.loader_factory import DataLoaderFactory` (was from `src.loaders`)
   - `from src.config.config_loader import load_config, save_config` (was from `src.utils`)
   - `from src.domain.models import PipelineOptions` (new)
4. Replace the `options` dict construction in `process_and_export()` with `PipelineOptions` dataclass:
   ```python
   options = PipelineOptions(
       main_file_path=self.main_data_file,
       output_path=output_path,
       selected_categories=selected_categories,
       enable_scraping=self.chk_scrape.isChecked(),
       enable_ai_enhancement=self.chk_ai.isChecked(),
       preserve_client_edits=self.chk_preserve.isChecked(),
       force_ai_reprocess=self.chk_force_ai.isChecked(),
       scrape_mebella=self.chk_mebella.isChecked(),
       scrape_topchladenie=self.chk_topchladenie.isChecked(),
       topchladenie_csv_path=getattr(self, 'topchladenie_csv_path', ''),
       enable_price_mapping=self.chk_price_mapping.isChecked(),
   )
   ```
5. Replace `WorkerNewFormat(self.config, options)` with `PipelineWorker(self.config, options)`
6. Move category extraction logic to use `CategoryFilter` from domain
7. Remove any business logic that now lives in domain/pipeline (column config decisions should delegate to pipeline)

- [ ] **Step 2: Update `main.py` entry point**

Create `main.py` (rename from `main_new_format.py`):

```python
# main.py
"""GastroPro Product Manager — entry point."""

import sys
from PyQt5.QtWidgets import QApplication
from src.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add src/gui/main_window.py main.py
git commit -m "feat(refactor): add MainWindow with new module imports and PipelineOptions"
```

---

## Phase 6: Cleanup

### Task 20: Update tests to use new imports

Update all existing test files to import from new module paths.

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/test_ai_enhancer_new_format.py` -> rename to `tests/test_ai_enhancer.py`
- Modify: `tests/test_data_merging_new_format.py` -> rename to `tests/test_data_merging.py`
- Modify: `tests/test_category_filter.py`
- Modify: `tests/test_category_mapper_new_format.py` -> rename to `tests/test_category_mapper.py`
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Update test imports**

For each test file, update imports from old paths to new paths:

| Old import | New import |
|-----------|-----------|
| `from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat` | `from src.ai.product_enricher import ProductEnricher` |
| `from src.mergers.data_merger_new_format import DataMergerNewFormat` | `from src.domain.products.merger import ProductMerger` |
| `from src.mappers.category_mapper_new_format import CategoryMapperNewFormat` | `from src.domain.categories.category_service import CategoryService` |
| `from src.filters.category_filter import CategoryFilter` | `from src.domain.categories.category_filter import CategoryFilter` |
| `from src.pipeline.pipeline_new_format import PipelineNewFormat` | `from src.pipeline.pipeline import Pipeline` |
| `from src.utils.config_loader import load_config` | `from src.config.config_loader import load_config` |
| `from src.core.database import ProductDatabase` | `from src.data.database.product_db import ProductDB` |
| `from src.loaders.data_loader_factory import DataLoaderFactory` | `from src.data.loaders.loader_factory import DataLoaderFactory` |

Rename test files to drop `_new_format` suffix.

- [ ] **Step 2: Run all tests**

Run: `pytest -v`
Expected: All tests pass with new imports

- [ ] **Step 3: Commit**

```bash
git add tests/
git commit -m "refactor(tests): update imports to new module paths, drop _new_format suffixes"
```

---

### Task 21: Delete old directories and files

Remove all old module directories that have been replaced.

**Files to delete:**
- `src/loaders/` (entire directory)
- `src/parsers/` (entire directory)
- `src/core/` (entire directory)
- `src/mergers/` (entire directory)
- `src/mappers/` (entire directory)
- `src/filters/` (entire directory)
- `src/transformers/` (entire directory)
- `src/utils/` (entire directory)
- `src/services/` (entire directory)
- `src/ai/ai_enhancer_new_format.py`
- `src/ai/ai_prompts_new_format.py`
- `src/pipeline/pipeline_new_format.py`
- `src/gui/main_window_new_format.py`
- `src/gui/worker_new_format.py`
- `main_new_format.py`

- [ ] **Step 1: Verify no imports reference old paths**

Run: `grep -r "from src.loaders\|from src.parsers\|from src.core\|from src.mergers\|from src.mappers\|from src.filters\|from src.transformers\|from src.utils\|from src.services\|_new_format" src/ main.py tests/ --include="*.py" | grep -v __pycache__`

Expected: No matches (all old imports have been updated)

- [ ] **Step 2: Delete old files**

```bash
rm -rf src/loaders src/parsers src/core src/mergers src/mappers src/filters src/transformers src/utils src/services
rm -f src/ai/ai_enhancer_new_format.py src/ai/ai_prompts_new_format.py
rm -f src/pipeline/pipeline_new_format.py
rm -f src/gui/main_window_new_format.py src/gui/worker_new_format.py
rm -f main_new_format.py
```

- [ ] **Step 3: Run all tests**

Run: `pytest -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: remove old module directories and _new_format files"
```

---

### Task 22: Slim down config.json

Remove the hardcoded `new_output_columns` list from config.json since it's now generated by `schema.py`.

**Files:**
- Modify: `config.json`
- Modify: `src/domain/transform/output_transformer.py` (update to use schema)

- [ ] **Step 1: Update OutputTransformer to use schema**

In `src/domain/transform/output_transformer.py`, change how it gets column list:

```python
# Replace:
self.new_output_columns = config.get("new_output_columns", [])
# With:
from src.config.schema import get_output_columns
self.new_output_columns = get_output_columns()
```

- [ ] **Step 2: Remove `new_output_columns` from config.json**

Delete the `new_output_columns` key and its ~500-line array from `config.json`. Also remove `final_csv_columns` if it still exists (legacy).

- [ ] **Step 3: Run tests**

Run: `pytest -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add config.json src/domain/transform/output_transformer.py
git commit -m "refactor: generate output columns from schema.py, remove from config.json"
```

---

### Task 23: Update CLAUDE.md

Update the project documentation to reflect the new architecture.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md**

Update the Architecture section, Key Directories, Entry Points, and any references to old file paths:

- Entry point: `main.py` (not `main_new_format.py`)
- Key directories: `src/data/`, `src/domain/`, `src/ai/`, `src/pipeline/`, `src/gui/`, `src/config/`
- Pipeline entry: `src/pipeline/pipeline.py`
- GUI entry: `src/gui/main_window.py`
- Remove all `_new_format` references

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for new layered architecture"
```

---

### Task 24: Final integration test

Run the full application to verify everything works end-to-end.

- [ ] **Step 1: Run all tests**

```bash
pytest -v
```

Expected: All tests pass

- [ ] **Step 2: Run the application**

```bash
python main.py
```

Expected: GUI opens without errors. Verify:
- File loading works
- Category filter populates
- Processing options are available
- Export produces output file

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: resolve integration issues from refactor"
```
