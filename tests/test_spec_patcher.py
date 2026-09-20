import os
import sqlite3
import pytest
from src.domain.specs.patcher import SpecPatcher


def test_patch_product_dict_insulation_and_text_sync():
    old_pdata = {
        "code": "F840130",
        "name": "Forcold chladnička 1300l",
        "shortDescription": "Vďaka hrúbke steny 70 mm a chladeniu...",
        "description": "<p>Kvalitná 70 mm izolácia minimalizuje straty.</p><h3>FAQ</h3><p>Otázka: Aká je hrúbka steny? Odpoveď: Izolácia s hrúbkou 70 mm výrazne obmedzuje únik.</p>",
        "metaDescription": "GastroPro.sk | Chladnička Forcold 1300l s hrúbkou steny 70 mm.",
        "filteringProperty:Hrúbka izolácie (mm)": "70",
    }
    verified_specs = {
        "insulation_mm": 60,
        "power_w": 508,
        "volume_l": 1300,
        "source_url": "https://www.forcold.it/test",
    }

    new_pdata, changes = SpecPatcher.patch_product_dict(old_pdata, verified_specs, verified_source="oem:forcold")

    assert new_pdata["filteringProperty:Hrúbka izolácie (mm)"] == "60"
    assert "hrúbke steny 60 mm" in new_pdata["shortDescription"]
    assert "70 mm" not in new_pdata["shortDescription"]
    assert "60 mm izolácia" in new_pdata["description"]
    assert "Izolácia s hrúbkou 60 mm" in new_pdata["description"]
    assert "70 mm" not in new_pdata["description"]
    assert "hrúbkou steny 60 mm" in new_pdata["metaDescription"]
    assert "70 mm" not in new_pdata["metaDescription"]
    assert new_pdata["_verified_by"] == "oem:forcold"
    assert new_pdata["_verified_url"] == "https://www.forcold.it/test"
    assert len(changes) > 0


def test_patch_product_in_db(tmp_path):
    db_file = str(tmp_path / "test_products.db")
    backups_dir = tmp_path / "data" / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE products (
            code TEXT PRIMARY KEY,
            product_data TEXT,
            source TEXT,
            last_updated TEXT,
            aiProcessed TEXT,
            aiProcessedDate TEXT
        )
    """)
    init_pdata = '{"name": "Forcold 1300l", "shortDescription": "hrúbka steny 70 mm"}'
    c.execute("INSERT INTO products VALUES ('F840130', ?, 'gastromarket', '', '1', '')", (init_pdata,))
    conn.commit()
    conn.close()

    patcher = SpecPatcher(db_path=db_file)
    changes = patcher.patch_product_in_db(
        code="F840130",
        verified_specs={"insulation_mm": 60},
        verified_source="oem:forcold",
        create_backup=False,
    )

    assert len(changes) > 0
    conn = sqlite3.connect(db_file)
    row = conn.cursor().execute("SELECT product_data FROM products WHERE code = 'F840130'").fetchone()
    conn.close()
    assert "hrúbka steny 60 mm" in row[0]
    assert "70 mm" not in row[0]
