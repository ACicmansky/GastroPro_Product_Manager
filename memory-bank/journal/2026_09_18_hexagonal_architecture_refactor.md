# 2026-09-18 Pragmatic Hexagonal Architecture (Ports and Adapters) Refactor

## Rationale
Following the architectural evaluation and approved implementation plan, the application was refactored to a **Pragmatic Hexagonal Architecture (Ports and Adapters)**. 

Prior to this refactor, `Pipeline` acted as a monolithic procedural coordinator that directly instantiated concrete persistence and AI adapters (`ProductDB`, `RunDB`, `ProductEnricher`, `ScrapingOrchestrator`) and accepted a sprawling list of 6 individual callbacks (`on_progress`, `on_stage`, `on_ai_progress`, etc.), while Qt worker threads used nested `QEventLoop`s directly coupled to the pipeline.

The goals of this refactor were:
1. Decouple application use cases from concrete databases, file systems, and Qt event loops.
2. Introduce lightweight structural subtyping (`typing.Protocol`) for driven ports without runtime overhead.
3. Extract single-responsibility Use Cases (`SyncCatalogUseCase`, `ExportCatalogUseCase`, `ResumeAiUseCase`, `EnrichCategoriesUseCase`).
4. Replace callback soup with an `EventSinkPort` (Observer pattern) and user interaction with a `UserResolutionPort`.
5. Maintain 100% backward compatibility for all existing tests and scripts.

## Changes Completed

### 1. Domain Ports Layer (`src/domain/ports/`)
- **`repositories.py`**: Defined `ProductRepositoryPort` and `RunRepositoryPort` Protocols.
- **`gateways.py`**: Defined `FeedGatewayPort`, `ScraperGatewayPort`, `AiEnricherPort`, and `ExcelIOPort` Protocols.
- **`events.py`**: Implemented `EventSinkPort` Protocol alongside `NullEventSink`, `CallbackEventSink`, and `ConsoleEventSink`.
- **`resolution.py`**: Implemented `UserResolutionPort` Protocol alongside `AutoSkipResolution` (for headless/automated runs) and `CallbackResolution`.

### 2. Application Use Cases (`src/pipeline/use_cases/`)
- **`SyncCatalogUseCase`**: Extracted the complete linear synchronization workflow (load DB/file -> fetch feeds -> scrape -> merge -> map categories -> enhance AI -> apply feed specs -> transform -> persist DB -> write output).
- **`ExportCatalogUseCase`**: Extracted direct SQLite database to 138-column Excel export logic, category filtering, and feed spec overrides.
- **`ResumeAiUseCase`**: Extracted AI resumption workflow against DB products.
- **`EnrichCategoriesUseCase`**: Extracted scoped AI re-runs for specific categories.

### 3. Hexagonal Pipeline Facade (`src/pipeline/pipeline.py`)
- Transformed `Pipeline` into a composition root and backward-compatible facade supporting constructor dependency injection (`product_repo=...`, `run_repo=...`, `feed_gateway=...`, `excel_io=...`).
- Fallbacks automatically instantiate default concrete adapters when not provided.
- Preserved step convenience methods (`parse_xml`, `map_categories`, `apply_transformation`, `save_output`) to ensure zero test regressions.

### 4. GUI Worker Adapters (`src/gui/worker.py`)
- Created `QtSignalEventSink` adapting Qt signals (`progress`, `stage`, `ai_progress`) to `EventSinkPort`.
- Created `QtDialogResolver` encapsulating `QEventLoop` blocking on dialogs into `UserResolutionPort`.
- Simplified `PipelineWorker`, `AIResumeWorker`, and `DBExportWorker` to delegate directly through the ports.

### 5. Automated Tests
- Created `tests/test_use_cases.py` with 6 new unit tests verifying `SyncCatalogUseCase`, `ExportCatalogUseCase`, `UserResolutionPort`, and `EventSinkPort` with an in-memory repository and mock gateways (<0.05s runtime without touching disk).
- Total test suite: **255 tests passing** (up from 249) with 0 regressions.

## Verification Results
- `ruff check`: All checks passed cleanly.
- `ruff format`: Formatted cleanly.
- `pytest`: 255 passed in 9.96s via `uv run poe check`.
- `pytest-cov`: 68% overall branch coverage report generated.
