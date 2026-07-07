# UI/UX modernization ("bring UI and UX to 2026")

## Problem
The GUI looked dated: `styles/main.qss` was broken legacy (`PUSHButton` typo meant every button rendered stock native gray; `box-shadow`/`transition` are unsupported in Qt; `.dark` classes nothing ever applied), no application style/font was set, default cramped spacing, and dialogs hardcoded light-only colors (`#e3f2fd`, `#f0f0f0`, `#666`) that would break in dark mode.

## What changed
- **`src/gui/theme.py`** (new): `apply_theme(app)` — Fusion style + Segoe UI 10pt + minimal QPalette + token-substituted QSS applied on the whole QApplication (so all dialogs inherit). LIGHT/DARK palette dicts; dark chosen automatically from the Windows registry (`AppsUseLightTheme`). `set_variant(widget, v)` switches QSS `[variant=...]` states at runtime with unpolish/polish.
- **`styles/main.qss`**: full rewrite as a `string.Template` ($token) template — card-style QGroupBox (surface bg, radius 10, muted title), secondary + `[primary="true"]` accent buttons, `[danger="true"]`, focus-ring inputs, custom checkbox indicators (`styles/check.svg`, also applied to `QListView::indicator` for the category checklist), modern thin scrollbars, slim accent progress bar, table/header styling, label variants (hint/success/warning), dialog cards (`[card="info"|"neutral"]`). NOTE: literal `$` in the QSS (even comments) breaks `Template.substitute`.
- **`main.py`**: `apply_theme(app)` after QApplication.
- **`src/gui/main_window.py`**: removed `load_stylesheet` (theme is app-wide now), window 760×820 with minimum size, margins/spacing on the root layout, `#appTitle` label, primary props on process/resume buttons, danger prop on AI cancel, `#statsDisplay` monospace, inline gray/green/darkorange styles → variant properties.
- **`src/gui/widgets.py`**: deleted dead `DropArea`/`TopchladenieCsvDropArea` (they called MainWindow methods that no longer exist); dialog hardcoded colors → `card`/`variant` properties.

## Verification
Offscreen smoke test (QSS parses clean, dark mode detected True on this machine) + rendered screenshots of main window and CategoryMappingDialog in both themes (offscreen platform has no fonts, so text is invisible in shots — layout/colors verified, fonts fine on desktop). Suite: 213 passed.

## Skipped (ponytail)
- Theme is read once at startup; live OS theme switching would need a registry watcher.

## Level 2 (same day, second pass)
- **Two-pane landscape layout** (1080×720): header (title + theme toggle), left column = sources/feeds/options/AI cards, right column = category filter (stretch) + KPI results card, footer = stage tracker + progress + status line + primary CTA. Empty-state placeholder (dashed card) in the right pane until a file is loaded (`_update_right_pane`).
- **Pipeline stage tracker**: `Pipeline.run` got an optional `on_stage` callback (keys: load/feeds/scrape/merge/categories/ai/export); `PipelineWorker` re-emits as a `stage` signal; `MainWindow._set_stage` marks earlier stages ✓ done / active / pending via QSS `[stage=...]` states. On error the tracker freezes at the failing stage.
- **Status line under the progress bar** — the old `progress_bar.setFormat(msg)` was invisible (indeterminate bars render no text), so pipeline messages were never seen.
- **KPI tiles** replace the monospace stats dump, which read keys the worker never emitted (`total_created`, `created` per-source dicts…) and so showed zeros; tiles consume the real schema (`merge{created,updated,kept,removed}`, `ai{processed,failed}`, `total_products`, `duration`).
- **Theme toggle** Auto/Light/Dark persisted via `QSettings("GastroPro","ProductManager")`, applies live (`apply_theme` re-callable); auto = Windows registry.
- **Drag & drop** XLSX anywhere on the window; **Ctrl+O** open, **Ctrl+R** run.
- Tests: `tests/test_gui_window.py` (offscreen; stage transitions + KPI tiles against the exact worker schema; NB: QApplication must be held by a fixture or PyQt GC destroys the widget tree between tests).
- **Test pollution fix (unrelated bug found)**: `test_category_mapper_new_format.py` wrote to the production `categories.json` on every run (`add_mapping` on a CategoryService pointed at the real file) and asserted against production mapping data (broken by the user's `update_categories.py` prefixing `Tovary a kategórie > `). Both tests now use isolated tmp mapping files; polluted line restored via git checkout. OutputTransformer verified to not double-prefix. Suite: 215 passed.
