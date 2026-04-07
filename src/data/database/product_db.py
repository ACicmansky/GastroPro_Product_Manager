"""Thin product persistence layer using SQLite with JSON document store."""

import sqlite3
import json
import os
import shutil
import glob as glob_module
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd


class ProductDB:
    """Thin CRUD operations for product data stored as JSON in SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.backups_dir = os.path.join(os.path.dirname(db_path), "backups")
        self.table_name = "products"
        self.primary_key = "code"
        self._ensure_directories()
        self.init_db()

    def _ensure_directories(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT PRIMARY KEY,
                    product_data TEXT NOT NULL,
                    source TEXT DEFAULT '',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    aiProcessed TEXT DEFAULT '0',
                    aiProcessedDate TEXT DEFAULT ''
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def get_all(self) -> pd.DataFrame:
        """Retrieve all products, unpacking JSON into flat DataFrame columns."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name}")
            rows = cursor.fetchall()

            if not rows:
                return pd.DataFrame()

            products = []
            for row in rows:
                row_dict = dict(row)
                product_data = json.loads(row_dict.get("product_data", "{}"))
                base = {
                    "code": row_dict["code"],
                    "source": row_dict.get("source", ""),
                    "aiProcessed": row_dict.get("aiProcessed", "0"),
                    "aiProcessedDate": row_dict.get("aiProcessedDate", ""),
                }
                base.update(product_data)
                products.append(base)

            return pd.DataFrame(products)
        finally:
            conn.close()

    def upsert(self, df: pd.DataFrame):
        """Save DataFrame to database. Caller decides what data to pass — DB just stores it."""
        if df.empty:
            return

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for _, row in df.iterrows():
                row_dict = row.to_dict()
                code = str(row_dict.get("code", ""))
                if not code:
                    continue

                source = str(row_dict.get("source", ""))
                ai_processed = str(row_dict.get("aiProcessed", "0"))
                ai_processed_date = str(row_dict.get("aiProcessedDate", ""))

                # Pack everything except fixed columns into JSON
                fixed_cols = {"code", "source", "aiProcessed", "aiProcessedDate"}
                product_data = {
                    k: v for k, v in row_dict.items()
                    if k not in fixed_cols and pd.notna(v)
                }
                product_json = json.dumps(product_data, ensure_ascii=False, default=str)

                cursor.execute(f"""
                    INSERT INTO {self.table_name}
                        (code, product_data, source, last_updated, aiProcessed, aiProcessedDate)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(code) DO UPDATE SET
                        product_data = excluded.product_data,
                        source = excluded.source,
                        last_updated = excluded.last_updated,
                        aiProcessed = excluded.aiProcessed,
                        aiProcessedDate = excluded.aiProcessedDate
                """, (code, product_json, source, now, ai_processed, ai_processed_date))

            conn.commit()
        finally:
            conn.close()

    def delete_by_codes(self, codes: List[str]):
        """Remove products by their codes."""
        if not codes:
            return
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(codes))
            cursor.execute(
                f"DELETE FROM {self.table_name} WHERE code IN ({placeholders})",
                codes
            )
            conn.commit()
        finally:
            conn.close()

    def backup(self, max_backups: int = 10) -> Optional[str]:
        """Create a rotating backup of the database."""
        if not os.path.exists(self.db_path):
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"products_backup_{timestamp}.db"
        backup_path = os.path.join(self.backups_dir, backup_filename)
        shutil.copy2(self.db_path, backup_path)

        # Rotate old backups
        backups = sorted(glob_module.glob(os.path.join(self.backups_dir, "products_backup_*.db")))
        while len(backups) > max_backups:
            os.remove(backups.pop(0))

        return backup_path
