"""CLI script to safely apply verified OEM specifications to catalog products."""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.database.product_db import ProductDB
from src.domain.specs.patcher import SpecPatcher
from src.scrapers.oem.forcold_adapter import ForcoldAdapter

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def patch_single_product(code: str, db_path: str = "data/products.db"):
    """Patch a single product using registered OEM adapters."""
    db = ProductDB(db_path)
    df = db.get_all()
    matches = df[df["code"].astype(str).str.strip() == code.strip()]
    if matches.empty:
        logger.error(f"Product with code '{code}' not found in {db_path}")
        return

    row = matches.iloc[0]
    name = str(row.get("name") or "")

    # Try adapters
    adapters = [ForcoldAdapter()]
    specs = None
    adapter_name = None
    for a in adapters:
        if a.can_handle(code, name):
            specs = a.get_specs(code, name)
            if specs:
                adapter_name = f"oem:{a.manufacturer_name.lower()}"
                break

    if not specs:
        logger.warning(f"No OEM specifications found for product {code} ({name})")
        return

    patcher = SpecPatcher(db_path=db_path)
    changes = patcher.patch_product_in_db(code, specs, verified_source=adapter_name, create_backup=True)
    if changes:
        logger.info(f"Successfully patched {code}:")
        for ch in changes:
            logger.info(f"  - {ch}")
    else:
        logger.info(f"Product {code} was already up to date with OEM specs.")


def patch_all_oem_products(db_path: str = "data/products.db"):
    """Scan all products in DB and apply OEM specs where available."""
    db = ProductDB(db_path)
    df = db.get_all()
    adapters = [ForcoldAdapter()]
    patcher = SpecPatcher(db_path=db_path)

    total_patched = 0
    total_changes = 0

    # Create single backup before batch
    first = True

    for _, row in df.iterrows():
        code = str(row.get("code") or "")
        name = str(row.get("name") or "")
        for a in adapters:
            if a.can_handle(code, name):
                specs = a.get_specs(code, name)
                if specs:
                    source_tag = f"oem:{a.manufacturer_name.lower()}"
                    changes = patcher.patch_product_in_db(code, specs, verified_source=source_tag, create_backup=first)
                    first = False
                    if changes:
                        total_patched += 1
                        total_changes += len(changes)

    logger.info(f"Batch OEM patch complete: {total_patched} products updated with {total_changes} changes.")


def main():
    parser = argparse.ArgumentParser(description="Patch product technical specifications from verified OEM sources")
    parser.add_argument("--code", help="Single product code to patch (e.g. F840130)")
    parser.add_argument("--all-oem", action="store_true", help="Patch all products matching registered OEM adapters")
    parser.add_argument("--db", default="data/products.db", help="Path to SQLite database")
    args = parser.parse_args()

    if args.code:
        patch_single_product(args.code, db_path=args.db)
    elif args.all_oem:
        patch_all_oem_products(db_path=args.db)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
