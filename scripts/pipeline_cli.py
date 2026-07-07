"""Run pipeline stages independently — files in, file out.

Each subcommand wraps one existing component, so any stage can be run,
inspected, and re-run in isolation. Intermediate files are the audit trail.

Examples:
    python scripts/pipeline_cli.py feeds --out-dir out/feeds
    python scripts/pipeline_cli.py feeds --only forgastro --out-dir out/feeds
    python scripts/pipeline_cli.py merge main.xlsx --feeds out/feeds/*.xlsx -o merged.xlsx
    python scripts/pipeline_cli.py categories merged.xlsx -o mapped.xlsx
    python scripts/pipeline_cli.py transform mapped.xlsx -o output.xlsx
    python scripts/pipeline_cli.py run main.xlsx -o output.xlsx --preserve-edits
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.config_loader import load_config
from src.data.loaders.xlsx_loader import load_xlsx
from src.data.parsers.xml_parser_factory import XMLParserFactory
from src.data.writers.xlsx_writer import write_xlsx
from src.domain.categories.category_service import CategoryService
from src.domain.models import PipelineOptions
from src.domain.products.feed_specs import apply_feed_specs
from src.domain.products.merger import ProductMerger
from src.domain.transform.output_transformer import OutputTransformer
from src.logging_setup import setup_logging

logger = logging.getLogger("pipeline_cli")


def cmd_feeds(args, config):
    for name, feed_cfg in config.get("xml_feeds", {}).items():
        if args.only and name not in args.only:
            continue
        url = feed_cfg.get("url", "")
        if not url:
            continue
        logger.info("Fetching feed '%s'...", name)
        df = XMLParserFactory.fetch_and_parse(name, url, config)
        if df is None or df.empty:
            logger.warning("Feed '%s' returned no products", name)
            continue
        out = Path(args.out_dir) / f"{name}.xlsx"
        write_xlsx(df, out)
        logger.info("Feed '%s': %d products -> %s", name, len(df), out)


def cmd_merge(args, config):
    main_df = load_xlsx(args.main)
    feed_dfs = {Path(p).stem: load_xlsx(p) for p in args.feeds}
    result = ProductMerger().merge(
        main_df, feed_dfs, preserve_edits=args.preserve_edits
    )
    write_xlsx(result.products, args.out)
    s = result.stats
    logger.info(
        "Merge: created=%d updated=%d kept=%d removed=%d -> %d rows -> %s",
        s.created, s.updated, s.kept, s.removed, len(result.products), args.out,
    )


def cmd_categories(args, config):
    df = load_xlsx(args.input)
    service = CategoryService()
    unmapped = set()
    for idx, row in df.iterrows():
        old_cat = str(row.get("defaultCategory", "") or "").strip()
        if not old_cat:
            continue
        new_cat = service.map(old_cat)
        if new_cat:
            df.at[idx, "defaultCategory"] = new_cat
            df.at[idx, "categoryText"] = new_cat
        else:
            unmapped.add(old_cat)
    write_xlsx(df, args.out)
    logger.info("%d rows -> %s (%d unmapped categories)", len(df), args.out, len(unmapped))
    for cat in sorted(unmapped):
        logger.warning("unmapped category: %s", cat)


def cmd_transform(args, config):
    df = load_xlsx(args.input)
    out_df = OutputTransformer(config).transform(df)
    write_xlsx(out_df, args.out)
    logger.info("%d rows x %d cols -> %s", len(out_df), len(out_df.columns), args.out)


def cmd_ai(args, config):
    from src.ai.product_enricher import ProductEnricher  # imports AI stack — keep lazy
    from src.data.database.batch_job_db import BatchJobDB
    from src.data.database.run_db import RunDB
    import pandas as pd

    db_path = config.get("db_path", "data/products.db")

    if getattr(args, "status", False):
        run = RunDB(db_path).get_resumable_run()
        if not run:
            logger.info("No resumable AI run.")
        else:
            logger.info(
                "Run %s: status=%s %d/%d products, detail=%s",
                run["id"], run["status"], run["processed_products"], run["total_products"], run["detail"],
            )
        return

    if getattr(args, "resume", False):
        enricher = ProductEnricher(config, batch_job_db=BatchJobDB(db_path))
        if not enricher.get_resumable_run():
            logger.info("No resumable AI run.")
            return
        df = load_xlsx(args.input)
        progress = lambda *a: logger.info("%s", a[-1] if a else "")
        result = enricher.resume(df, progress_callback=progress)
        out_df = apply_feed_specs(result.products)
        write_xlsx(out_df, args.out)
        logger.info("AI resume: processed=%d -> %s", result.processed, args.out)
        _write_review_files(enricher, out_df, Path(args.out))
        return

    if getattr(args, "model", None):
        config.setdefault("ai_enhancement", {})["model"] = args.model
        logger.info("Model override: %s", args.model)

    df = load_xlsx(args.input)
    done = pd.Series(False, index=df.index)
    if "aiProcessed" in df.columns:
        done = (
            df["aiProcessed"].astype(str).str.strip().str.upper()
            .isin({"1", "TRUE", "YES", "1.0"})
        )
    pending = df if args.force else df[~done]
    if args.limit:
        pending = pending.head(args.limit)
    logger.info(
        "%d already enhanced, %d selected for enhancement (of %d total)",
        int(done.sum()), len(pending), len(df),
    )
    fill_missing = getattr(args, "fill_missing", False)
    if fill_missing:
        pending = df if not args.limit else df.head(args.limit)  # gaps live in "done" rows too
    if args.dry_run or pending.empty:
        return int(done.sum()), len(pending)

    # --limit micro-tests stay untracked (one-off, no chunking); unlimited runs get
    # run/chunk tracking so an interruption can be continued with `ai --resume`.
    enricher = ProductEnricher(config, batch_job_db=BatchJobDB(db_path) if not args.limit else None)
    progress = lambda *a: logger.info("%s", a[-1] if a else "")
    if fill_missing:
        result = enricher.fill_missing_params(
            pending.copy(), progress_callback=progress,
            model=getattr(args, "fill_model", None),
        )
    else:
        result = enricher.enrich(
            pending.copy(), force_reprocess=args.force, progress_callback=progress
        )

    out_df = apply_feed_specs(result.products)
    write_xlsx(out_df, args.out)
    logger.info(
        "AI: processed=%d failed=%d -> %s", result.processed, result.failed, args.out
    )
    _write_review_files(enricher, out_df, Path(args.out))
    return int(done.sum()), len(pending)


def _write_review_files(enricher, df, out_path: Path):
    """Human-review exports: non-exact matches + implausible filter values."""
    from src.ai.validation import find_implausible
    import pandas as pd

    if enricher.parser.match_audit:
        path = out_path.with_name(out_path.stem + "_match_review.csv")
        pd.DataFrame(enricher.parser.match_audit).to_csv(path, index=False, encoding="utf-8-sig")
        logger.warning("%d non-exact matches -> %s", len(enricher.parser.match_audit), path)

    issues = find_implausible(df)
    if not issues.empty:
        path = out_path.with_name(out_path.stem + "_param_review.csv")
        issues.to_csv(path, index=False, encoding="utf-8-sig")
        logger.warning("%d implausible parameter values -> %s", len(issues), path)


def cmd_classify(args, config):
    """Suggest categories for products without one (writes suggestedCategory, never defaultCategory)."""
    from src.ai.api_client import GeminiClient
    from src.ai.batch_orchestrator import BatchOrchestrator
    from src.ai.prompts import create_category_classification_prompt, load_category_parameters

    df = load_xlsx(args.input)
    known = sorted(load_category_parameters().keys())
    if not known:
        logger.error("No known categories loaded from categories_with_parameters.json")
        return

    def needs_category(row) -> bool:
        cat = BatchOrchestrator._category_of(row)
        return not cat or "neznáma" in cat.lower()

    mask = df.apply(needs_category, axis=1)
    targets = df[mask]
    if args.limit:
        targets = targets.head(args.limit)
    logger.info("%d products without category (of %d total)", len(targets), len(df))
    if args.dry_run or targets.empty:
        return

    client = GeminiClient(config)
    sys_prompt = create_category_classification_prompt(known)
    known_set = set(known)
    suggestions = {}
    chunk_size = 25
    for i in range(0, len(targets), chunk_size):
        chunk = targets.iloc[i:i + chunk_size]
        payload = [
            {
                "code": str(r.get("code", "")),
                "name": str(r.get("name", "")),
                "shortDescription": str(r.get("shortDescription", ""))[:300],
            }
            for _, r in chunk.iterrows()
        ]
        items = client.call(sys_prompt, json.dumps(payload, ensure_ascii=False)) or []
        for item in items:
            cat = str(item.get("category", "")).strip()
            if cat in known_set:
                suggestions[str(item.get("code", "")).strip()] = cat
        logger.info("Classified chunk %d-%d: %d suggestions so far", i, i + len(chunk), len(suggestions))

    df["suggestedCategory"] = ""
    codes = df["code"].astype(str).str.strip()
    df.loc[codes.isin(suggestions), "suggestedCategory"] = codes.map(suggestions)
    write_xlsx(df, args.out)
    logger.info("%d category suggestions -> %s (review, then copy into defaultCategory)", len(suggestions), args.out)


def cmd_run(args, config):
    from src.pipeline.pipeline import Pipeline  # imports AI/DB stack — keep lazy

    options = PipelineOptions(
        main_file_path=args.main,
        output_path=args.out,
        preserve_client_edits=args.preserve_edits,
        enabled_feeds=args.only,
    )
    result = Pipeline(config).run(options, on_progress=lambda m: None)
    for warning in result.warnings:
        logger.warning(warning)
    logger.info(
        "Done: %d products in %.1fs -> %s",
        result.product_count, result.duration_seconds, result.output_path,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config.json")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("feeds", help="fetch XML feeds, one xlsx per feed")
    p.add_argument("--only", nargs="*", help="feed names (default: all configured)")
    p.add_argument("--out-dir", default="out/feeds")
    p.set_defaults(func=cmd_feeds)

    p = sub.add_parser("merge", help="merge main file with feed files")
    p.add_argument("main")
    p.add_argument("--feeds", nargs="+", required=True, help="feed xlsx files (name = filename stem)")
    p.add_argument("-o", "--out", default="out/merged.xlsx")
    p.add_argument("--preserve-edits", action="store_true")
    p.set_defaults(func=cmd_merge)

    p = sub.add_parser("categories", help="apply categories.json mapping (non-interactive)")
    p.add_argument("input")
    p.add_argument("-o", "--out", default="out/mapped.xlsx")
    p.set_defaults(func=cmd_categories)

    p = sub.add_parser("transform", help="transform to 138-column output format")
    p.add_argument("input")
    p.add_argument("-o", "--out", default="out/output.xlsx")
    p.set_defaults(func=cmd_transform)

    p = sub.add_parser("ai", help="AI-enhance products (Gemini Batch API); --limit N for a micro test")
    p.add_argument("input")
    p.add_argument("-o", "--out", default="out/ai_enhanced.xlsx")
    p.add_argument("--limit", type=int, help="enhance only the first N pending products")
    p.add_argument("--force", action="store_true", help="reprocess already-enhanced products too")
    p.add_argument("--dry-run", action="store_true", help="report counts only, no API calls")
    p.add_argument("--model", help="override ai_enhancement.model for this run (A/B testing)")
    p.add_argument("--fill-missing", action="store_true",
                   help="second pass: web-grounded re-ask ONLY for missing filter params (ignores aiProcessed)")
    p.add_argument("--fill-model", help="stronger model for --fill-missing (tiered enhancement)")
    p.add_argument("--resume", action="store_true", help="continue the latest paused/interrupted run")
    p.add_argument("--status", action="store_true", help="print the latest resumable run's progress and exit")
    p.set_defaults(func=cmd_ai)

    p = sub.add_parser("classify", help="AI-suggest categories for products without one (review column)")
    p.add_argument("input")
    p.add_argument("-o", "--out", default="out/classified.xlsx")
    p.add_argument("--limit", type=int, help="classify only the first N uncategorized products")
    p.add_argument("--dry-run", action="store_true", help="report counts only, no API calls")
    p.set_defaults(func=cmd_classify)

    p = sub.add_parser("run", help="full headless pipeline (no scraping/AI)")
    p.add_argument("main")
    p.add_argument("-o", "--out", default="out/output.xlsx")
    p.add_argument("--preserve-edits", action="store_true")
    p.add_argument("--only", nargs="*", help="feed names (default: all configured)")
    p.set_defaults(func=cmd_run)

    args = parser.parse_args()
    setup_logging()
    config = load_config(args.config)
    args.func(args, config)


if __name__ == "__main__":
    main()
