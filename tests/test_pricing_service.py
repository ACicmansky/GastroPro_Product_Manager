"""Tests for PricingService — records format must survive round trips."""

import json

import pandas as pd
import pytest

from src.domain.pricing.pricing_service import PricingService


@pytest.fixture
def prices_file(tmp_path):
    path = tmp_path / "prices.json"
    path.write_text(json.dumps([
        {"code": "ROCKET DINING", "dimension": "420x420x720", "price": "88,00"},
    ]), encoding="utf-8")
    return str(path)


@pytest.mark.unit
class TestPricingService:
    def test_loads_records_format(self, prices_file):
        svc = PricingService(prices_file)
        assert svc.get_price("ROCKET DINING") == "88,00"

    def test_migrates_legacy_dict_format(self, tmp_path):
        path = tmp_path / "prices.json"
        path.write_text(json.dumps({"OLD CODE": "10,00"}), encoding="utf-8")
        svc = PricingService(str(path))
        assert svc.get_price("OLD CODE") == "10,00"

    def test_apply_mappings_fills_price(self, prices_file):
        svc = PricingService(prices_file)
        df = pd.DataFrame([{"code": "ROCKET DINING", "price": ""}])
        result = svc.apply_mappings(df)
        assert result.at[0, "price"] == "88,00"

    def test_identify_unmapped(self, prices_file):
        svc = PricingService(prices_file)
        df = pd.DataFrame([
            {"code": "ROCKET DINING", "price": ""},
            {"code": "UNKNOWN BAR", "price": ""},
            {"code": "HAS PRICE", "price": "5,00"},
        ])
        assert svc.identify_unmapped(df) == ["UNKNOWN BAR"]

    def test_add_mapping_persists_dimension(self, prices_file):
        PricingService(prices_file).add_mapping("NEW COFFEE", "42,00", "400x400x600")
        saved = json.loads(open(prices_file, encoding="utf-8").read())
        assert {"code": "NEW COFFEE", "dimension": "400x400x600", "price": "42,00"} in saved
        # reload sees it and dataframe keeps the dimension column
        svc = PricingService(prices_file)
        assert svc.get_price("NEW COFFEE") == "42,00"
        assert list(svc.as_dataframe().columns) == ["code", "dimension", "price"]
