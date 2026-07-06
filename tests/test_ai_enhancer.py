"""
Tests for AI enhancement functionality (current implementation).
"""

import pytest
import pandas as pd
import os
from datetime import datetime

pytestmark = pytest.mark.ai_enhancement


def test_param_normalization_and_whitelist():
    """Filter values are deterministic: bare numbers, canonical Áno/Nie, no ad-hoc keys."""
    from src.ai.result_parser import ResultParser

    norm = ResultParser.normalize_param_value
    assert norm("Šírka (mm)", "800 mm") == "800"
    assert norm("Príkon (W)", "550W") == "550"
    assert norm("Objem (l)", "12,5 l") == "12.5"
    assert norm("Teplotný rozsah (°C)", "-2 až +8") == "-2 až +8"  # ranges keep text
    assert norm("Kapacita (GN)", "2x GN1/1") == "2x GN1/1"  # GN is not a scalar unit
    assert norm("So zásuvkou (Áno/Nie)", "yes") == "Áno"
    assert norm("Vypúšťací ventil (Áno/Nie)", "nie") == "Nie"
    assert norm("Materiál", "Nerez AISI 304") == "Nerez AISI 304"

    parser = ResultParser(allowed_params={"Šírka (mm)", "Materiál"})
    df = pd.DataFrame({"code": ["A1"], "name": ["N"], "aiProcessed": [""]})
    enhanced = [{
        "code": "A1",
        "parameters": {"Šírka": "800 mm", "Materiál": "Nerez", "Typ matrice": "T12"},
    }]
    df, count = parser.update_dataframe(df, enhanced)
    assert count == 1
    assert df.at[0, "filteringProperty:Šírka (mm)"] == "800"  # unit-less key canonicalized
    assert df.at[0, "filteringProperty:Materiál"] == "Nerez"
    assert "filteringProperty:Typ matrice" not in df.columns  # unrequested key dropped


def test_category_falls_back_when_newcategory_column_empty():
    """Empty newCategory column (e.g. DB export) must fall back to defaultCategory."""
    from src.ai.batch_orchestrator import BatchOrchestrator

    row = pd.Series({"newCategory": "", "defaultCategory": "Gastro > Pulty"})
    assert BatchOrchestrator._category_of(row) == "Gastro > Pulty"
    row_nan = pd.Series({"newCategory": float("nan"), "defaultCategory": "Gastro > Pulty"})
    assert BatchOrchestrator._category_of(row_nan) == "Gastro > Pulty"
    assert BatchOrchestrator._category_of(pd.Series({"code": "X"})) == ""


def test_cli_ai_dry_run_selects_only_unprocessed(tmp_path):
    """`pipeline_cli.py ai --dry-run --limit` counts pending products, no API."""
    import argparse
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import pipeline_cli

    df = pd.DataFrame({
        "code": [f"P{i}" for i in range(6)],
        "name": [f"Product {i}" for i in range(6)],
        "aiProcessed": ["1", "TRUE", "0", "", "NO", None],
    })
    src = tmp_path / "in.xlsx"
    df.to_excel(src, index=False)

    args = argparse.Namespace(
        input=str(src), out=str(tmp_path / "out.xlsx"),
        limit=2, force=False, dry_run=True,
    )
    already, selected = pipeline_cli.cmd_ai(args, config={})
    assert already == 2      # "1" and "TRUE"
    assert selected == 2     # 4 pending, capped by --limit


class TestCurrentAIEnhancement:
    """Test current AI enhancement functionality."""


    def test_ai_tracking_columns_exist(self, sample_old_format_df):
        """Test that AI tracking columns exist in DataFrame."""
        df = sample_old_format_df.copy()

        assert "Spracovane AI" in df.columns
        assert "AI_Processed_Date" in df.columns

    def test_ai_tracking_column_update(self, sample_old_format_df):
        """Test updating AI tracking columns."""
        df = sample_old_format_df.copy()

        # Simulate AI processing
        df.at[0, "Spracovane AI"] = "True"
        df.at[0, "AI_Processed_Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        assert df.loc[0, "Spracovane AI"] == "True"
        assert df.loc[0, "AI_Processed_Date"] != ""

    def test_skip_already_processed_products(self, sample_old_format_df):
        """Test that already processed products are identified."""
        df = sample_old_format_df.copy()

        # Mark one as processed
        df.at[0, "Spracovane AI"] = "True"

        # Filter unprocessed
        unprocessed = df[df["Spracovane AI"] != "True"]

        assert len(unprocessed) == 2
        assert df.loc[0, "Spracovane AI"] == "True"

    def test_fuzzy_matching_product_identification(self, sample_old_format_df):
        """Test fuzzy matching logic for product identification."""
        from rapidfuzz import fuzz

        df = sample_old_format_df.copy()

        # Test fuzzy matching
        search_name = "Product 1"
        for idx, row in df.iterrows():
            similarity = fuzz.ratio(search_name, row["Názov tovaru"])
            if similarity > 90:
                assert row["Názov tovaru"] == "Product 1"
                break

    def test_catalog_number_matching(self, sample_old_format_df):
        """Test matching products by catalog number."""
        df = sample_old_format_df.copy()

        # Find by catalog number
        catalog_code = "TEST001"
        mask = df["Kat. číslo"] == catalog_code

        assert mask.any()
        matched_row = df[mask].iloc[0]
        assert matched_row["Názov tovaru"] == "Product 1"


class TestAIEnhancementConfiguration:
    """Test AI enhancement configuration."""

    def test_ai_config_exists(self, config):
        """Test that AI enhancement configuration exists."""
        assert "ai_enhancement" in config
        ai_config = config["ai_enhancement"]

        assert "enabled" in ai_config
        assert "model" in ai_config
        assert "batch_size" in ai_config
        assert "temperature" in ai_config

    def test_ai_config_values(self, config):
        """Test AI configuration values."""
        ai_config = config["ai_enhancement"]

        assert isinstance(ai_config["enabled"], bool)
        assert isinstance(ai_config["batch_size"], int)
        assert ai_config["batch_size"] > 0
        assert 0 <= ai_config["temperature"] <= 1

    def test_ai_quota_settings(self, config):
        """Test AI quota management settings."""
        ai_config = config["ai_enhancement"]

        # Should have retry settings
        assert "retry_attempts" in ai_config
        assert "retry_delay" in ai_config
        assert ai_config["retry_attempts"] > 0
