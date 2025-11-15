"""
Tests for AI enhancement with new 147-column format.
Following TDD approach: Write tests first, then implement.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch


class TestAIEnhancerNewFormat:
    """Test AI enhancer with new format columns."""

    def test_enhancer_initialization(self, config):
        """Test AI enhancer initializes with config."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        enhancer = AIEnhancerNewFormat(config)

        assert enhancer.config is not None
        assert hasattr(enhancer, "enhance_product")

    def test_enhance_updates_new_format_columns(self, config):
        """Test that enhancement updates new format columns."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Short name"],
                "shortDescription": [""],
                "description": [""],
                "aiProcessed": [""],
                "aiProcessedDate": [""],
            }
        )

        enhancer = AIEnhancerNewFormat(config)

        with patch.object(enhancer, "_call_ai_api") as mock_api:
            mock_api.return_value = {
                "shortDescription": "AI generated short description",
                "description": "AI generated full description",
            }

            result = enhancer.enhance_product(df.iloc[0])

            assert result["shortDescription"] == "AI generated short description"
            assert result["description"] == "AI generated full description"

    def test_marks_product_as_processed(self, config):
        """Test that AI processing is tracked."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product"],
                "aiProcessed": [""],
                "aiProcessedDate": [""],
            }
        )

        enhancer = AIEnhancerNewFormat(config)

        with patch.object(enhancer, "_call_ai_api") as mock_api:
            mock_api.return_value = {"shortDescription": "Test"}

            result = enhancer.enhance_product(df.iloc[0])

            assert result["aiProcessed"] == "1"
            assert result["aiProcessedDate"] != ""

    def test_skips_already_processed(self, config):
        """Test that already processed products are skipped."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product"],
                "aiProcessed": ["1"],
                "aiProcessedDate": ["2024-01-01"],
            }
        )

        enhancer = AIEnhancerNewFormat(config)

        with patch.object(enhancer, "_call_ai_api") as mock_api:
            result = enhancer.enhance_product(df.iloc[0])

            # API should not be called
            mock_api.assert_not_called()

            # Should return original data
            assert result["aiProcessed"] == "1"


class TestAIEnhancementBatch:
    """Test batch AI enhancement."""

    def test_enhance_dataframe(self, config):
        """Test enhancing entire DataFrame."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["Product 1", "Product 2"],
                "shortDescription": ["", ""],
                "aiProcessed": ["", ""],
            }
        )

        enhancer = AIEnhancerNewFormat(config)

        with patch.object(enhancer, "_call_ai_api") as mock_api:
            mock_api.return_value = {"shortDescription": "Enhanced"}

            result = enhancer.enhance_dataframe(df)

            # Both products should be processed
            assert all(result["aiProcessed"] == "1")
            assert mock_api.call_count == 2

    def test_batch_skips_processed_products(self, config):
        """Test batch processing skips already processed products."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002", "PROD003"],
                "name": ["P1", "P2", "P3"],
                "aiProcessed": ["1", "", "1"],
                "aiProcessedDate": ["2024-01-01", "", "2024-01-01"],
            }
        )

        enhancer = AIEnhancerNewFormat(config)

        with patch.object(enhancer, "_call_ai_api") as mock_api:
            mock_api.return_value = {"shortDescription": "Enhanced"}

            result = enhancer.enhance_dataframe(df)

            # Only PROD002 should be processed
            assert mock_api.call_count == 1

    def test_batch_with_force_reprocess(self, config):
        """Test batch processing with force reprocess flag."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["P1", "P2"],
                "aiProcessed": ["1", "1"],
            }
        )

        enhancer = AIEnhancerNewFormat(config)

        with patch.object(enhancer, "_call_ai_api") as mock_api:
            mock_api.return_value = {"shortDescription": "Enhanced"}

            result = enhancer.enhance_dataframe(df, force_reprocess=True)

            # Both should be processed despite being marked
            assert mock_api.call_count == 2


class TestAIEnhancementFields:
    """Test AI enhancement of specific fields."""

    def test_enhance_short_description(self, config):
        """Test AI enhancement of shortDescription field."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        product = pd.Series(
            {
                "code": "PROD001",
                "name": "Professional Coffee Machine",
                "shortDescription": "",
                "manufacturer": "TestBrand",
            }
        )

        enhancer = AIEnhancerNewFormat(config)

        with patch.object(enhancer, "_call_ai_api") as mock_api:
            mock_api.return_value = {
                "shortDescription": "High-quality professional coffee machine"
            }

            result = enhancer.enhance_product(product)

            assert result["shortDescription"] != ""
            assert "coffee" in result["shortDescription"].lower()

    def test_enhance_full_description(self, config):
        """Test AI enhancement of description field."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        product = pd.Series(
            {"code": "PROD001", "name": "Coffee Machine", "description": ""}
        )

        enhancer = AIEnhancerNewFormat(config)

        with patch.object(enhancer, "_call_ai_api") as mock_api:
            mock_api.return_value = {
                "description": "Detailed description of the coffee machine..."
            }

            result = enhancer.enhance_product(product)

            assert result["description"] != ""

    def test_preserve_existing_descriptions(self, config):
        """Test that existing descriptions are preserved."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        product = pd.Series(
            {
                "code": "PROD001",
                "name": "Product",
                "shortDescription": "Existing short description",
                "description": "Existing full description",
                "aiProcessed": "",
            }
        )

        enhancer = AIEnhancerNewFormat(config)

        with patch.object(enhancer, "_call_ai_api") as mock_api:
            mock_api.return_value = {}

            result = enhancer.enhance_product(product, preserve_existing=True)

            # Should not call API if descriptions exist
            mock_api.assert_not_called()


class TestAIEnhancementConfiguration:
    """Test AI enhancement configuration."""

    def test_uses_config_api_settings(self, config):
        """Test that enhancer uses API settings from config."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        enhancer = AIEnhancerNewFormat(config)

        # Should have API configuration
        assert hasattr(enhancer, "config")
        if "ai_enhancement" in config:
            assert enhancer.config.get("ai_enhancement") is not None

    def test_respects_field_configuration(self, config):
        """Test that enhancer respects field configuration."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        enhancer = AIEnhancerNewFormat(config)

        # Should know which fields to enhance
        assert hasattr(enhancer, "enhance_product")

    def test_handles_missing_api_key(self, config):
        """Test handling of missing API key."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        # Remove API key from config
        config_no_key = config.copy()
        if "ai_enhancement" in config_no_key:
            config_no_key["ai_enhancement"].pop("api_key", None)

        enhancer = AIEnhancerNewFormat(config_no_key)

        product = pd.Series({"code": "PROD001", "name": "Product", "aiProcessed": ""})

        # Should handle gracefully (skip or raise appropriate error)
        result = enhancer.enhance_product(product)

        # Should not crash
        assert result is not None


class TestAIEnhancementTracking:
    """Test AI enhancement tracking and statistics."""

    def test_tracks_enhancement_statistics(self, config):
        """Test that enhancement tracks statistics."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002", "PROD003"],
                "name": ["P1", "P2", "P3"],
                "aiProcessed": ["", "", "1"],
            }
        )

        enhancer = AIEnhancerNewFormat(config)

        with patch.object(enhancer, "_call_ai_api") as mock_api:
            mock_api.return_value = {"shortDescription": "Enhanced"}

            result, stats = enhancer.enhance_dataframe_with_stats(df)

            assert "total_processed" in stats
            assert "already_processed" in stats
            assert "newly_processed" in stats
            assert stats["newly_processed"] == 2
            assert stats["already_processed"] == 1

    def test_tracks_api_calls(self, config):
        """Test tracking of API calls."""
        from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

        df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["P1", "P2"],
                "aiProcessed": ["", ""],
            }
        )

        enhancer = AIEnhancerNewFormat(config)

        with patch.object(enhancer, "_call_ai_api") as mock_api:
            mock_api.return_value = {"shortDescription": "Enhanced"}

            result, stats = enhancer.enhance_dataframe_with_stats(df)

            assert "api_calls" in stats
            assert stats["api_calls"] == 2
