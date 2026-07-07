# Runbook — full AI re-enhancement (~9,657 products)

Goal: every product gets deterministic filter values (currently 0 of 5,691 "enhanced" DB products have any filteringProperty values). Costs Gemini quota only — no AI assistant needed to run this.

## 0. One-time prep
- `pip install -r requirements.txt` (fixed 2026-07-07: `google-genai`, not `google-generativeai`).
- `.env` has `GOOGLE_API_KEY`.
- Optional consistency tweak: `config.json` → `ai_enhancement.batch_size: 15` (currently 30). Smaller batches = more consistent outputs, more requests.
- Model stays `gemini-2.5-flash-lite` (A/B verdict: 3.1-flash-lite filled fewer params + factual errors).

## 1. Choose input
- **Simplest**: `2026_04_08_GastroPro_repaired.xlsx` (Downloads) — categories already backfilled.
- **Fresher**: rebuild first:
  ```
  python scripts/pipeline_cli.py feeds
  python scripts/pipeline_cli.py merge <repaired.xlsx> --feeds out/feeds/*.xlsx --preserve-edits -o out/merged.xlsx
  ```
  Then use `out/merged.xlsx` below.

## 2. Reset the enhanced flag (instead of --force)
`--force --limit N` re-selects the same first N every run — it can't be sliced. Blank `aiProcessed` once, then run *without* `--force` so slices progress naturally:
```python
import pandas as pd
df = pd.read_excel("input.xlsx", dtype=str).fillna("")
df["aiProcessed"] = ""
df.to_excel("out/reset.xlsx", index=False)
```

## 3. Micro test, then slices
```
python scripts/pipeline_cli.py ai out/reset.xlsx --dry-run          # pending count ≈ 9,657
python scripts/pipeline_cli.py ai out/reset.xlsx --limit 20 -o out/p0.xlsx   # eyeball filter columns
python scripts/pipeline_cli.py ai out/p0.xlsx --limit 2000 -o out/p1.xlsx
python scripts/pipeline_cli.py ai out/p1.xlsx --limit 2000 -o out/p2.xlsx
... repeat, chaining output → input, until --dry-run shows 0 pending.
```
- Interrupted run? Just re-run the same command — `BatchOrchestrator.process` auto-resumes the active batch job (`batch_jobs` table). Results also save to DB incrementally after each batch.
- Batch request JSONL lands in `out/batch_requests/` (gitignored).

## 4. Optional second pass + finish
```
python scripts/pipeline_cli.py ai out/pN.xlsx --fill-missing -o out/filled.xlsx   # web-grounded re-ask for still-missing params
python scripts/pipeline_cli.py transform out/filled.xlsx -o out/final.xlsx        # 138-column e-shop format
```

## 5. Verify
- Filter columns populated with bare numbers, units in headers (`Šírka (mm)`).
- Check the fuzzy-match audit CSV and the plausibility-validation review CSV written next to the output.
- `logs/gastropro.log` for per-batch counts.
