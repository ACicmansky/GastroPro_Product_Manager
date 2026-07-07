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


def test_feed_specs_override_ai_dims():
    """ForGastro structured dims/weight overwrite filter columns; other sources untouched."""
    from src.domain.products.feed_specs import apply_feed_specs

    df = pd.DataFrame({
        "code": ["F1", "F2", "G1"],
        "source": ["forgastro", "forgastro", "gastromarket"],
        "feedWidth": ["38", "800", "999"],
        "feedDepth": ["51", "", "999"],
        "feedHeight": ["79.5", "bad", "999"],
        "feedDimUnit": ["CM", "MM", "CM"],
        "weight": ["12,5", "0", "50"],
        "filteringProperty:Šírka (mm)": ["370", "", ""],  # AI value gets overwritten
    })
    df = apply_feed_specs(df)
    assert df.at[0, "filteringProperty:Šírka (mm)"] == "380"     # CM -> mm, feed wins
    assert df.at[0, "filteringProperty:Hĺbka (mm)"] == "510"
    assert df.at[0, "filteringProperty:Výška (mm)"] == "795"
    assert df.at[0, "filteringProperty:Hmotnosť (kg)"] == "12.5"
    assert df.at[1, "filteringProperty:Šírka (mm)"] == "800"        # MM passthrough
    assert pd.isna(df.at[1, "filteringProperty:Hĺbka (mm)"])        # empty skipped
    assert pd.isna(df.at[1, "filteringProperty:Výška (mm)"])        # garbage skipped
    assert pd.isna(df.at[1, "filteringProperty:Hmotnosť (kg)"])     # zero skipped
    assert df.at[2, "filteringProperty:Šírka (mm)"] == ""           # non-forgastro untouched


def test_enforce_format_seo_fields():
    """seoTitle <=60, metaDescription <=155 + branding prefix, enforced in code."""
    from src.ai.result_parser import ResultParser

    fmt = ResultParser.enforce_format
    long_title = "Profesionálny konvektomat s bojlerovým vyvíjačom pary a automatickým umývaním"
    out = fmt("seoTitle", long_title)
    assert len(out) <= 60 and not out.endswith((" ", ","))
    assert fmt("seoTitle", "Krátky titulok") == "Krátky titulok"

    meta = fmt("metaDescription", "Robustný nerezový stôl pre gastro prevádzky.")
    assert meta.startswith("GastroPro.sk | ")
    already = fmt("metaDescription", "GastroPro.sk | Už s prefixom.")
    assert already.count("GastroPro.sk") == 1
    assert len(fmt("metaDescription", "x" * 300)) <= 155


def test_find_implausible_values():
    """Voltage enum + dimension ranges flag outliers (feed typo w=3800 cm case)."""
    from src.ai.validation import find_implausible

    df = pd.DataFrame({
        "code": ["A", "B", "C"],
        "name": ["a", "b", "c"],
        "filteringProperty:Napätie (V)": ["230", "999", ""],
        "filteringProperty:Šírka (mm)": ["800", "38000", "abc"],
    })
    issues = find_implausible(df)
    flagged = set(zip(issues["code"], issues["parameter"]))
    assert ("B", "Napätie (V)") in flagged
    assert ("B", "Šírka (mm)") in flagged      # 38000 mm out of range
    assert ("C", "Šírka (mm)") in flagged      # non-numeric
    assert ("A", "Napätie (V)") not in flagged
    assert ("A", "Šírka (mm)") not in flagged


def test_missing_param_requests_are_grounded():
    """Second pass: only unfilled expected params re-asked, with google_search tool."""
    from src.ai.batch_orchestrator import BatchOrchestrator

    orch = BatchOrchestrator(client=None, result_parser=None, config={})
    cat = next(iter(orch.category_parameters))
    expected = orch.category_parameters[cat]
    filled, missing = expected[0], expected[1:]

    df = pd.DataFrame({
        "code": ["X1"], "name": ["Produkt X1"], "shortDescription": ["popis"],
        "newCategory": [cat],
        f"filteringProperty:{filled}": ["230"],
    })
    requests, count = orch._build_missing_param_requests(df)
    assert count == 1 and len(requests) == 1
    req = requests[0]["request"]
    assert req["tools"] == [{"google_search": {}}]
    assert "responseMimeType" not in req["generationConfig"]  # conflicts with grounding
    import json
    payload = json.loads(req["contents"][0]["parts"][0]["text"])
    assert payload[0]["chybajuce_parametre"] == missing  # filled param not re-asked


def test_main_pass_has_schema_and_existing_params():
    """Main batch requests carry enum-locked responseSchema + existingParameters."""
    from src.ai.batch_orchestrator import BatchOrchestrator
    from src.ai.prompts import build_response_schema

    schema = build_response_schema(["Šírka (mm)", "So zásuvkou (Áno/Nie)"])
    props = schema["items"]["properties"]["parameters"]["properties"]
    assert props["So zásuvkou (Áno/Nie)"]["enum"] == ["Áno", "Nie"]
    assert props["Šírka (mm)"] == {"type": "STRING"}

    orch = BatchOrchestrator(client=None, result_parser=None, config={})
    cat = next(iter(orch.category_parameters))
    df = pd.DataFrame({
        "code": ["X1"], "name": ["Produkt X1"],
        "shortDescription": ["p"], "description": ["d"],
        "newCategory": [cat],
        "filteringProperty:Objem (l)": ["12"],
    })
    requests = []
    orch._build_category_requests(df, {0}, requests, is_group1=False)
    assert len(requests) == 1
    req = requests[0]["request"]
    assert "responseSchema" in req["generationConfig"]
    import json
    payload = json.loads(req["contents"][0]["parts"][0]["text"])
    assert payload[0]["existingParameters"] == {"Objem (l)": "12"}


def test_fuzzy_match_populates_audit():
    """Non-exact matches land in match_audit for review export."""
    from src.ai.result_parser import ResultParser

    parser = ResultParser()
    df = pd.DataFrame({"code": ["ABC-123"], "name": ["Chladnička X"], "aiProcessed": [""]})
    df, count = parser.update_dataframe(df, [{"code": "ABC123", "name": "Chladnička X"}])
    assert count == 1
    assert len(parser.match_audit) == 1
    assert parser.match_audit[0]["strategy"] in ("fuzzy_code", "fuzzy_name")
    assert parser.match_audit[0]["matched_code"] == "ABC-123"


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
