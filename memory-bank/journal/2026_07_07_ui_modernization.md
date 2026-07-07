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
- No in-app theme toggle — follows Windows setting; add only if requested.
- Theme is read once at startup; live OS theme switching would need a registry watcher.
