# 2026-09-12: Migration to uv Package Manager

## Context
The project previously relied on an unmanaged, global Python environment and a minimal `requirements.txt` file. Dependency installation was unpinned, slow, and lacked a deterministic lockfile. Furthermore, some essential dependencies such as `playwright` (used in `MebellaScraper`) were missing from `requirements.txt`.

## What Was Done
1. **Configured `pyproject.toml`**:
   - Specified PEP 621 metadata, `requires-python = ">=3.13"`.
   - Explicitly listed runtime dependencies: `PyQt5>=5.15.0`, `pandas>=2.0.0,<3.0.0`, `requests>=2.31.0`, `beautifulsoup4>=4.12.0`, `python-dotenv>=1.0.0`, `google-genai>=0.1.1`, `rapidfuzz>=3.0.0`, `openpyxl>=3.1.0`, `playwright>=1.40.0`.
   - Configured `[dependency-groups] dev = ["pytest>=8.0.0", "pytest-mock>=3.14.0", "ruff>=0.16.7"]`.
   - Configured `[tool.ruff]` for linting and formatting targeting Python 3.13.
   - Set `[tool.uv] package = false` (application mode) and specified `required-environments = ["sys_platform == 'win32' and platform_machine == 'AMD64'"]` to properly resolve Windows wheels for `pyqt5-qt5==5.15.2`.
   - Embedded pytest configuration into `[tool.pytest.ini_options]`.
2. **Pinned Python**:
   - Created `.python-version` specifying `3.13`.
3. **Environment & Lockfile**:
   - Ran `uv lock` to produce a deterministic `uv.lock`.
   - Ran `uv sync` to build the isolated `.venv` containing all 51 resolved packages.
4. **Tooling & IDE**:
   - Updated `.gitignore` to ignore `.venv/` and `.uv/` while keeping `uv.lock` tracked.
   - Updated `.vscode/settings.json` so `python.defaultInterpreterPath` points to `${workspaceFolder}\.venv\Scripts\python.exe`.
   - Updated `pytest.ini` with `pythonpath = .`.
   - Updated `requirements.txt` with header notice and synced packages.
   - Updated `CLAUDE.md` to recommend `uv run`, `uv sync`, and `uv add`.
5. **Code/Test Improvements**:
   - Updated `test_scraper_new_format.py` and `test_topchladenie_scraper.py` so string dtype assertions (`test_all_values_are_strings`) accept both `object` and `pd.StringDtype`, making them forward-compatible across Pandas 2 and Pandas 3.

## Verification
- Checked Python executable in `.venv`: Python 3.13.14.
- Verified all runtime modules (`PyQt5`, `pandas`, `google.genai`, `playwright`, `bs4`, `openpyxl`, `rapidfuzz`, `requests`) import properly.
- Tested application entry point: `uv run python -c "import main"`.
- Ran full test suite via `uv run pytest`: **221 passed** in ~8 seconds.
