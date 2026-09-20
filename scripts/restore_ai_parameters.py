"""Restore filteringProperty:* parameters from products_backup_20260917_205246.db into active data/products.db.

Preserves 100% of current images, descriptions, and metadata.
"""

import json
import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def restore_parameters(
    source_backup_path: str = "data/backups/products_backup_20260917_205246.db",
    target_db_path: str = "data/products.db",
):
    if not os.path.exists(source_backup_path):
        logger.error(f"Source backup not found: {source_backup_path}")
        return

    # 1. Create a safety backup of target before modifying
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    safety_backup = f"data/backups/products_backup_before_param_restore_{now_str}.db"
    shutil.copy2(target_db_path, safety_backup)
    logger.info(f"Created safety backup: {safety_backup}")

    # 2. Read all parameters from backup
    src_conn = sqlite3.connect(source_backup_path)
    src_cursor = src_conn.cursor()
    src_cursor.execute("SELECT code, product_data FROM products")

    backup_params = {}
    for code, pdata_str in src_cursor.fetchall():
        if pdata_str:
            pdata = json.loads(pdata_str)
            filtering = {k: v for k, v in pdata.items() if k.startswith("filteringProperty:")}
            if filtering:
                backup_params[code] = filtering
    src_conn.close()
    logger.info(f"Loaded filtering properties for {len(backup_params)} products from backup.")

    # 3. Update target DB
    tgt_conn = sqlite3.connect(target_db_path)
    tgt_cursor = tgt_conn.cursor()
    tgt_cursor.execute("SELECT code, product_data FROM products")
    tgt_rows = tgt_cursor.fetchall()

    updated_count = 0
    new_params_added = 0

    for code, pdata_str in tgt_rows:
        if code in backup_params:
            pdata = json.loads(pdata_str) if pdata_str else {}
            params_to_add = backup_params[code]
            modified = False
            for pk, pv in params_to_add.items():
                if pk not in pdata or not str(pdata[pk]).strip():
                    pdata[pk] = pv
                    new_params_added += 1
                    modified = True
            if modified:
                new_json = json.dumps(pdata, ensure_ascii=False)
                tgt_cursor.execute(
                    "UPDATE products SET product_data = ? WHERE code = ?",
                    (new_json, code),
                )
                updated_count += 1

    tgt_conn.commit()
    tgt_conn.close()

    logger.info(f"Successfully updated {updated_count} products with {new_params_added} restored filter parameters.")


if __name__ == "__main__":
    restore_parameters()
