"""Tests for ProductDB — SQLite persistence round trips."""

import json
import sqlite3

import pandas as pd
import pytest

from src.data.database.product_db import ProductDB


@pytest.fixture
def product_db(tmp_path):
    return ProductDB(str(tmp_path / "products.db"))


@pytest.mark.unit
class TestProductDB:
    def test_empty_db_returns_empty_dataframe(self, product_db):
        assert product_db.get_all().empty

    def test_upsert_and_get_all_round_trip(self, product_db):
        df = pd.DataFrame(
            [
                {
                    "code": "ABC123",
                    "name": "Stôl",
                    "price": "99,00",
                    "source": "gastromarket",
                    "aiProcessed": "1",
                    "aiProcessedDate": "2026-07-05",
                }
            ]
        )
        product_db.upsert(df)
        result = product_db.get_all()
        assert len(result) == 1
        row = result.iloc[0]
        assert row["code"] == "ABC123"
        assert row["name"] == "Stôl"
        assert row["source"] == "gastromarket"
        assert row["aiProcessed"] == "1"

    def test_upsert_updates_existing_code(self, product_db):
        product_db.upsert(pd.DataFrame([{"code": "X1", "price": "10,00"}]))
        product_db.upsert(pd.DataFrame([{"code": "X1", "price": "20,00"}]))
        result = product_db.get_all()
        assert len(result) == 1
        assert result.iloc[0]["price"] == "20,00"

    def test_upsert_skips_rows_without_code(self, product_db):
        product_db.upsert(pd.DataFrame([{"code": "", "name": "no code"}]))
        assert product_db.get_all().empty

    def test_upsert_drops_nan_values_from_json(self, product_db):
        product_db.upsert(pd.DataFrame([{"code": "N1", "name": "ok", "stock": float("nan")}]))
        conn = sqlite3.connect(product_db.db_path)
        raw = conn.execute("SELECT product_data FROM products").fetchone()[0]
        conn.close()
        assert "stock" not in json.loads(raw)

    def test_delete_by_codes(self, product_db):
        product_db.upsert(pd.DataFrame([{"code": "A"}, {"code": "B"}]))
        product_db.delete_by_codes(["A"])
        result = product_db.get_all()
        assert result["code"].tolist() == ["B"]

    def test_backup_creates_file_and_rotates(self, product_db):
        import glob, os

        product_db.upsert(pd.DataFrame([{"code": "A"}]))
        path = product_db.backup(max_backups=2)
        assert path is not None and os.path.exists(path)
        # same-second timestamps overwrite each other, so only the count invariant holds
        for _ in range(2):
            product_db.backup(max_backups=2)
        backups = glob.glob(os.path.join(product_db.backups_dir, "products_backup_*.db"))
        assert 1 <= len(backups) <= 2
