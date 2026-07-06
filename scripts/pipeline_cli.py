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
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.config_loader import load_config
from src.data.loaders.loader_factory import DataLoaderFactory
from src.data.parsers.xml_parser_factory import XMLParserFactory
from src.data.writers.xlsx_writer import write_xlsx
from src.domain.categories.category_service import CategoryService
from src.domain.models import PipelineOptions
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
    main_df = DataLoaderFactory.load(args.main)
    feed_dfs = {Path(p).stem: DataLoaderFactory.load(p) for p in args.feeds}
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
    df = DataLoaderFactory.load(args.input)
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
    df = DataLoaderFactory.load(args.input)
    out_df = OutputTransformer(config).transform(df)
    write_xlsx(out_df, args.out)
    logger.info("%d rows x %d cols -> %s", len(out_df), len(out_df.columns), args.out)


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
