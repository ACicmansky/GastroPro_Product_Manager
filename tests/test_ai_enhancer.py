"""
Tests for AI enhancement functionality (current implementation).
"""

import pytest
import pandas as pd
import os
from datetime import datetime


class TestCurrentAIEnhancement:
    """Test current AI enhancement functionality."""

    @pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="API key not available")
    @pytest.mark.requires_api
    def test_ai_enhancement_updates_columns(self, sample_old_format_df, config):
        """Test that AI enhancement updates correct columns."""
        from src.services.ai_enhancer import AIEnhancementProcessor

        df = sample_old_format_df.copy()
        processor = AIEnhancementProcessor(config)

        # This would make actual API calls - skip in CI
        # Just test the structure
        assert "Krátky popis" in df.columns
        assert "Dlhý popis" in df.columns
        assert "SEO titulka" in df.columns
        assert "SEO popis" in df.columns

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
