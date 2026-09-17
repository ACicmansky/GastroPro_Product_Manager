"""
Script to restore product images from client file and recent database backup.
Preserves all AI fields, descriptions, SEO metadata, and category parameters.
"""

import sqlite3
import json
import shutil
import os
import re
from datetime import datetime
import openpyxl

DB_PATH = "data/products.db"
BACKUP_DB_PATH = "data/backups/products_backup_20260916_104351.db"
CLIENT_XLSX_PATH = r"C:\Users\Andrej\Downloads\products (2).xlsx"


def is_valid_image_url(val):
    if val is None:
        return False
    s = str(val).strip()
    if not s or s.lower() in ("none", "nan", "null", "false", "0", "[]", "{}", ""):
        return False
    if s.startswith("http://") or s.startswith("https://") or s.startswith("/") or s.startswith("www."):
        return True
    if re.search(r"\.(jpg|jpeg|png|webp|gif|svg)", s, re.I):
        return True
    return False


def main():
    print("=== STARTING PRODUCT IMAGE RESTORATION ===")

    # 1. Create a safety backup of current DB
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safety_backup = f"data/backups/products_backup_before_image_restore_{timestamp}.db"
    print(f"Creating safety backup: {safety_backup}...")
    shutil.copy2(DB_PATH, safety_backup)
    print("Safety backup created successfully.")

    # 2. Extract images from DB backup 2026-09-16 10:43:51
    print(f"\nReading backup database: {BACKUP_DB_PATH}...")
    db_backup_images = {}  # code -> dict of image_col -> url
    if os.path.exists(BACKUP_DB_PATH):
        conn_b = sqlite3.connect(BACKUP_DB_PATH)
        cur_b = conn_b.cursor()
        cur_b.execute("SELECT code, product_data FROM products")
        img_key_re = re.compile(r"^image\d*$")
        for code, data_str in cur_b.fetchall():
            if not code or not data_str:
                continue
            try:
                p = json.loads(data_str)
                imgs = {}
                for k, v in p.items():
                    if img_key_re.match(k) and is_valid_image_url(v):
                        imgs[k] = str(v).strip()
                if imgs:
                    db_backup_images[code.strip().upper()] = imgs
            except Exception:
                pass
        conn_b.close()
    print(f"Found images for {len(db_backup_images):,} products in DB backup.")

    # 3. Extract images from client file products (2).xlsx
    print(f"\nReading client file: {CLIENT_XLSX_PATH}...")
    client_images = {}  # code -> dict of image_col -> url
    if os.path.exists(CLIENT_XLSX_PATH):
        wb = openpyxl.load_workbook(CLIENT_XLSX_PATH, read_only=True)
        ws = wb.active
        headers = [cell for cell in next(ws.iter_rows(values_only=True))]
        code_idx = headers.index("code") if "code" in headers else headers.index("Kat. číslo")

        img_cols = []
        for i, h in enumerate(headers):
            if h and (str(h) == "defaultImage" or (str(h).startswith("image") and not str(h).startswith("imageDesc"))):
                img_cols.append((i, str(h)))

        for row in ws.iter_rows(min_row=2, values_only=True):
            code_val = row[code_idx]
            if not code_val:
                continue
            code = str(code_val).strip().upper()
            imgs = {}
            for col_idx, col_name in img_cols:
                val = row[col_idx]
                if is_valid_image_url(val):
                    # Map defaultImage -> image
                    target_key = "image" if col_name == "defaultImage" else col_name
                    imgs[target_key] = str(val).strip()
            if imgs:
                client_images[code] = imgs
    print(f"Found images for {len(client_images):,} products in client file.")

    # 4. Connect to target DB and restore images
    print(f"\nUpdating {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT code, product_data, aiProcessed FROM products")
    rows = cur.fetchall()

    restored_count = 0
    already_had_images = 0
    still_no_image = 0

    img_key_re = re.compile(r"^image\d*$")

    for code, data_str, ai_proc in rows:
        norm_code = code.strip().upper()
        try:
            p = json.loads(data_str) if data_str else {}
        except:
            p = {}

        # Check if product currently has any valid image
        has_curr_img = any(img_key_re.match(k) and is_valid_image_url(v) for k, v in p.items())

        # Determine source of images: client file has priority, then DB backup
        donor_imgs = {}
        if norm_code in client_images:
            donor_imgs = client_images[norm_code]
        elif norm_code in db_backup_images:
            donor_imgs = db_backup_images[norm_code]

        if donor_imgs:
            # Merge donor images without overwriting non-empty existing images
            changed = False
            for img_k, img_v in donor_imgs.items():
                if not is_valid_image_url(p.get(img_k)):
                    p[img_k] = img_v
                    changed = True

            if changed:
                restored_count += 1
                updated_json = json.dumps(p, ensure_ascii=False)
                cur.execute("UPDATE products SET product_data = ? WHERE code = ?", (updated_json, code))
            elif has_curr_img:
                already_had_images += 1
        else:
            if has_curr_img:
                already_had_images += 1
            else:
                still_no_image += 1

    conn.commit()

    # 5. Verification
    cur.execute("SELECT count(*) FROM products")
    total_after = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM products WHERE aiProcessed = '1' OR aiProcessed = 1 OR aiProcessed = 'True'")
    ai_enhanced_after = cur.fetchone()[0]

    # Check how many products have images now
    cur.execute("SELECT product_data FROM products")
    now_has_image = 0
    for (d_str,) in cur.fetchall():
        try:
            p = json.loads(d_str)
            if any(img_key_re.match(k) and is_valid_image_url(v) for k, v in p.items()):
                now_has_image += 1
        except:
            pass
    conn.close()

    print("\n==========================================")
    print("      IMAGE RESTORATION COMPLETE          ")
    print("==========================================")
    print(f"Total Products in DB:       {total_after:,}")
    print(f"AI-Enhanced Products:       {ai_enhanced_after:,} (100% PRESERVED)")
    print(f"Products Restored:          {restored_count:,}")
    print(f"Products WITH image(s) now: {now_has_image:,} ({now_has_image / total_after * 100:.2f}%)")
    print(
        f"Products WITHOUT images:    {total_after - now_has_image:,} ({(total_after - now_has_image) / total_after * 100:.2f}%)"
    )
    print("==========================================")


if __name__ == "__main__":
    main()
