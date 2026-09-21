"""CLI script to normalize, detect, and populate catalog product variants (pairCode).

Supports --dry-run (default) and --apply.
Creates automatic safety SQLite database backup before applying modifications.
"""

import argparse
import datetime
import json
import logging
import os
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.domain.products.variant_service import CatalogVariantService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_variant_population(db_path: str, apply_changes: bool = False) -> int:
    path = Path(db_path)
    if not path.exists():
        logger.error(f"Database not found: {db_path}")
        return 1

    sys.stdout.reconfigure(encoding="utf-8")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT code, product_data FROM products")

    products = {}
    for code, data_json in cursor.fetchall():
        products[code] = json.loads(data_json)

    logger.info(f"Loaded {len(products)} products from {db_path}")

    service = CatalogVariantService()
    updates, stats, (p1, p2, p3) = service.generate_all_updates(products)

    print("\n" + "=" * 60)
    print("      CATALOG VARIANT PAIRING & PARAMETER SUMMARY")
    print("=" * 60)
    print(f"Total catalog products:               {stats['total_catalog_products']}")
    print(f"Total products updated:               {stats['total_products_updated']}")
    print(f"Total products paired as variants:    {stats['total_products_paired']} ({stats['pairing_percentage']}%)")
    print(f"Standalone products (pairCode empty): {stats['total_catalog_products'] - stats['total_products_paired']}")
    print("-" * 60)
    print("1. Legacy float group normalization:")
    print(f"   - Variants normalized (e.g. BT100, TN70): {stats['legacy_variants_normalized']}")
    print(f"   - Singletons cleared to empty:            {stats['legacy_singletons_cleared']}")
    print("2. Mebella table base height pairing:")
    print(f"   - Multi-variant families created:         {stats['mebella_families_created']}")
    print(f"   - Table bases paired:                     {stats['mebella_products_paired']}")
    print("3. General catalog dimension pairing:")
    print(f"   - Strict dimension groups created:        {stats['dim_groups_created']}")
    print(f"   - Equipment items paired:                 {stats['dim_products_paired']}")
    print("=" * 60 + "\n")

    # Sample inspections
    print("Sample Group 1 (Legacy normalized - Cold Room BT100):")
    for code in ["BT100-1200-1200", "BT100-1200-1400", "BT100-1200-1600"]:
        if code in p1:
            print(f"   [{code}] -> {p1[code]}")

    print("\nSample Group 2 (Mebella Table Bases - FLAT SQUARE 02):")
    for code in ["FLAT SQUARE 02 BAR", "FLAT SQUARE 02 DINING", "FLAT SQUARE 02 COFFEE"]:
        if code in p2:
            print(f"   [{code}] -> {p2[code]}")

    print("\nSample Group 3 (General Dimension Variants):")
    for code in list(p3.keys())[:5]:
        print(f"   [{code}] ({products[code].get('name', '')[:40]}) -> {p3[code]}")

    if not apply_changes:
        print("\n[DRY RUN] No database modifications made. Run with --apply to commit.")
        conn.close()
        return 0

    # Apply changes
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"products_backup_before_variants_{ts}.db"
    conn.close()

    shutil.copy2(db_path, backup_path)
    logger.info(f"Created safety backup: {backup_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    applied_count = 0
    for code, upd_dict in updates.items():
        if code not in products:
            continue
        data = products[code]
        # Apply updates to product data dict
        for k, v in upd_dict.items():
            if v == "" and k in data and k not in ("pairCode", "variantVisibility"):
                del data[k]
            else:
                data[k] = v

        cursor.execute(
            "UPDATE products SET product_data = ?, last_updated = CURRENT_TIMESTAMP WHERE code = ?",
            (json.dumps(data, ensure_ascii=False), code),
        )
        applied_count += 1

    conn.commit()
    conn.close()

    logger.info(f"Successfully committed updates for {applied_count} products to {db_path}!")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Populate and normalize catalog product variants")
    parser.add_argument("--db", default="data/products.db", help="Path to products SQLite DB")
    parser.add_argument("--apply", action="store_true", help="Apply updates to database (creates backup)")
    args = parser.parse_args()

    sys.exit(run_variant_population(args.db, apply_changes=args.apply))


if __name__ == "__main__":
    main()
