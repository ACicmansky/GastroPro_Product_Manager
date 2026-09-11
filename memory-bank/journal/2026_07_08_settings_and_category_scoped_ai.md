# Settings UI + category-scoped AI re-runs

## Problem
App is heading multi-user: each user needs their own Gemini key, tunable AI values
lived only in config.json, and category AI filter parameters
(`categories_with_parameters.json`, 211 entries) had no UI and no way to re-run AI
for just one changed category (only "all unprocessed" or force-everything).

## What changed
- **`src/gui/settings_dialog.py`** (new): `SettingsDialog` with three tabs:
  - **API kľúč**: password field + 👁 toggle, "Otestovať kľúč" (sync `models.list()`
    ping), saved to `.env` via new `save_api_key` (also sets `os.environ` so it takes
    effect without restart — `load_dotenv()` won't override an existing var).
  - **AI nastavenia**: model combo (editable), batch_size/retry/parallel spinboxes,
    feed URL line-edits — written back with existing `save_config` (config dict is
    mutated in place, so MainWindow needs no reload).
  - **Parametre kategórií**: searchable category list, one-param-per-line editor,
    product count from DB, "💾 Uložiť parametre" and "🤖 Spustiť AI pre kategóriu"
    (confirm dialog with product count — paid API calls). Removing a param **clears
    its `filteringProperty:` values in the DB** for that category's products (user
    decision: stale extracted values must not linger in exports). Empty-list entries
    are kept (categories without filtre just get no param extraction — confirmed OK).
- **Category-scoped AI run**: `BatchOrchestrator.process(only_categories=...)` via new
  `_select()`; `ProductEnricher.enrich` passes through; `Pipeline.run_ai_for_categories`
  (DB in → DB out, refuses while a resumable run is pending); `AIResumeWorker` gained
  `categories=` param; MainWindow `_launch_ai_worker` shared between resume and scoped
  runs. Scoped runs go through RunDB → pausable/resumable like normal runs.
- **`_category_of` normalization (root-cause fix)**: DB rows saved before the category
  migration lack the "Tovary a kategórie > " prefix, so `category_parameters.get(cat)`
  and any scoped selection silently missed (0/9692 matched). `_category_of` now
  prepends the prefix when absent → 9465/9692 products, 187/211 param categories match.
  This also fixes the pre-existing silent miss in resume/missing-params passes.
- MainWindow: ⚙️ Nastavenia header button; first-run warning toast with
  "Otvoriť nastavenia" action when no key found; settings button disabled mid-run
  (prevents concurrent second AI run from the params tab).
- `config_loader`: `read_api_key` / `save_api_key`.

## Verification
Suite: 221 passed. Offscreen smoke: dialog tabs populate from real config
(211 categories listed, live product counts, e.g. Vínotéky a humidory = 54),
screenshots in `out/settings_tab*.png`.

## Follow-up (same day): params tab readability
- Dialog 980×640, resizable with min/maximize buttons (`Qt.WindowMaximizeButtonHint` —
  Windows dialogs hide them by default) + size grip.
- Flat 211-row list of full paths → `QTreeWidget`: leaf names grouped under parent
  path (27 groups), shared "Tovary a kategórie > " root stripped, full path in
  tooltip; selection header renders breadcrumb (`parents › …` small + leaf bold).
  Search filters leaves against the FULL path and hides empty groups.

## Skipped (ponytail)
- Editing output/feed column mappings in UI — structural, developer territory.
- Diacritics-insensitive category search ('umyva' won't match 'umývačky').
- Category old→new mapping table editor — mapping dialog already grows categories.json.
