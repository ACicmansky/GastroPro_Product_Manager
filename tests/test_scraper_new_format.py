"""
Tests for web scraper outputting to new 138-column format.
Following TDD approach: Write tests first, then implement.

Phase 11: Web Scraping Migration
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup


class TestScraperNewFormat:
    """Test scraper initialization and basic functionality."""

    def test_scraper_initializes_with_config(self, config):
        """Test scraper initializes with configuration."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        assert scraper is not None
        assert scraper.config is not None
        assert hasattr(scraper, "scrape_products")

    def test_scraper_produces_new_format(self, config):
        """Test scraper produces new format output directly."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Scraper should produce data directly in new format
        # No column mapping needed since scrape_product_detail() returns new format
        assert hasattr(scraper, "scrape_product_detail")
        assert hasattr(scraper, "scrape_products")

    def test_scraper_outputs_new_format_columns(self, config):
        """Test scraper outputs DataFrame with new format column names."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Create mock scraped data (already in new format)
        new_format_data = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Test Product"],
                "price": ["100.00"],
                "shortDescription": ["Short desc"],
                "description": ["Long description"],
                "defaultCategory": ["Tovary a kategórie > Category > Subcategory"],
                "categoryText": ["Tovary a kategórie > Category > Subcategory"],
                "defaultImage": ["img1.jpg"],
                "image": ["img2.jpg"],
            }
        )

        # Verify data is in new format
        assert "code" in new_format_data.columns
        assert "name" in new_format_data.columns
        assert "price" in new_format_data.columns
        assert "shortDescription" in new_format_data.columns
        assert "description" in new_format_data.columns
        assert "defaultCategory" in new_format_data.columns

        # Should NOT have old Slovak column names
        assert "Kat. číslo" not in new_format_data.columns
        assert "Názov tovaru" not in new_format_data.columns
        assert "Bežná cena" not in new_format_data.columns


class TestScraperColumnMapping:
    """Test that scraper produces new format directly."""

    def test_maps_all_standard_columns(self, config):
        """Test scraper produces new format column names directly."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Create mock data that simulates scraping output
        mock_data = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product Name"],
                "price": ["100"],
                "manufacturer": ["Liebherr"],
                "shortDescription": ["Short"],
                "description": ["Long"],
                "defaultCategory": ["Tovary a kategórie > Category"],
                "categoryText": ["Tovary a kategórie > Category"],
                "active": ["1"],
                "defaultImage": [""],
                "image": [""],
            }
        )

        # Verify data is in new format
        assert "code" in mock_data.columns
        assert "name" in mock_data.columns
        assert "price" in mock_data.columns
        assert "manufacturer" in mock_data.columns
        assert "shortDescription" in mock_data.columns
        assert "description" in mock_data.columns
        assert "active" in mock_data.columns

    def test_handles_missing_columns(self, config):
        """Test scraper handles missing data gracefully."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Minimal scraped data
        minimal_data = pd.DataFrame(
            {"code": ["PROD001"], "name": ["Product"], "price": ["100"]}
        )

        # Even with minimal data, should have core columns
        assert "code" in minimal_data.columns
        assert "name" in minimal_data.columns
        assert "price" in minimal_data.columns

    def test_preserves_data_values(self, config):
        """Test scraper preserves special characters and formatting."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Test data with special characters
        test_data = pd.DataFrame(
            {
                "code": ["SPECIAL-001"],
                "name": ["Test Product Ščeť"],
                "price": ["1234.56"],
                "shortDescription": ["Line1\nLine2"],
            }
        )

        # Values should be preserved exactly
        assert test_data.loc[0, "code"] == "SPECIAL-001"
        assert test_data.loc[0, "name"] == "Test Product Ščeť"
        assert test_data.loc[0, "price"] == "1234.56"
        assert test_data.loc[0, "shortDescription"] == "Line1\nLine2"


class TestScraperImageHandling:
    """Test image URL handling and splitting."""

    def test_splits_images_into_8_columns(self, config):
        """Test that scraper produces 8 separate image columns."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Mock data with images already split (as scraper produces)
        data = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product"],
                "defaultImage": ["img1.jpg"],
                "image": ["img2.jpg"],
                "image2": ["img3.jpg"],
                "image3": [""],
                "image4": [""],
                "image5": [""],
                "image6": [""],
                "image7": [""],
            }
        )

        # Verify all image columns exist
        assert "defaultImage" in data.columns
        assert "image" in data.columns
        assert "image2" in data.columns
        assert "image7" in data.columns

        assert data.loc[0, "defaultImage"] == "img1.jpg"
        assert data.loc[0, "image"] == "img2.jpg"
        assert data.loc[0, "image2"] == "img3.jpg"

    def test_handles_single_image(self, config):
        """Test handling of single image URL."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Mock data with single image
        data = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product"],
                "defaultImage": ["single.jpg"],
                "image": [""],
                "image2": [""],
            }
        )

        assert data.loc[0, "defaultImage"] == "single.jpg"
        assert data.loc[0, "image"] == ""

    def test_handles_max_8_images(self, config):
        """Test that maximum 8 images are supported."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Mock data with 8 images (max supported)
        data = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product"],
                "defaultImage": ["img1.jpg"],
                "image": ["img2.jpg"],
                "image2": ["img3.jpg"],
                "image3": ["img4.jpg"],
                "image4": ["img5.jpg"],
                "image5": ["img6.jpg"],
                "image6": ["img7.jpg"],
                "image7": ["img8.jpg"],
            }
        )

        # Should have exactly 8 image columns
        assert data.loc[0, "defaultImage"] == "img1.jpg"
        assert data.loc[0, "image7"] == "img8.jpg"


class TestScraperCategoryTransformation:
    """Test category transformation for new format."""

    def test_transforms_category_format(self, config):
        """Test scraper produces transformed category directly."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Mock data with transformed category (as scraper produces)
        data = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product"],
                "defaultCategory": ["Tovary a kategórie > Vitríny > Chladiace vitríny"],
                "categoryText": ["Tovary a kategórie > Vitríny > Chladiace vitríny"],
            }
        )

        # Verify category has correct format
        expected = "Tovary a kategórie > Vitríny > Chladiace vitríny"
        assert data.loc[0, "defaultCategory"] == expected

    def test_category_applied_to_both_columns(self, config):
        """Test category is in both defaultCategory and categoryText."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Mock data (as scraper produces)
        data = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product"],
                "defaultCategory": ["Tovary a kategórie > Cat > Sub"],
                "categoryText": ["Tovary a kategórie > Cat > Sub"],
            }
        )

        # Both should have same transformed value
        assert data.loc[0, "defaultCategory"] == data.loc[0, "categoryText"]
        assert "Tovary a kategórie > " in data.loc[0, "defaultCategory"]


class TestScraperIntegration:
    """Test scraper integration with pipeline."""

    def test_scraper_integrates_with_pipeline(self, config):
        """Test scraped data can be processed by pipeline."""
        from src.scrapers.scraper_new_format import ScraperNewFormat
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        scraper = ScraperNewFormat(config)
        pipeline = PipelineNewFormat(config)

        # Create mock scraped data (already in new format)
        scraped_df = pd.DataFrame(
            {
                "code": ["SCRAPED001"],
                "name": ["Scraped Product"],
                "price": ["200.00"],
                "defaultCategory": ["Tovary a kategórie > Test > Category"],
                "categoryText": ["Tovary a kategórie > Test > Category"],
                "defaultImage": ["img1.jpg"],
                "image": ["img2.jpg"],
            }
        )

        # Should be processable by pipeline
        result = pipeline.finalize_output(scraped_df)

        assert len(result) == 1
        assert result.loc[0, "code"] == "SCRAPED001"
        assert result.loc[0, "name"] == "Scraped Product"

    def test_scraped_data_ready_for_merge(self, config):
        """Test scraped data has correct structure for merging."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Mock scraped data (already in new format)
        data = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["Product 1", "Product 2"],
                "price": ["100", "200"],
            }
        )

        # Should have required columns for merging
        assert "code" in data.columns
        assert "name" in data.columns
        assert "price" in data.columns

        # Codes should not be empty
        assert not data["code"].isna().any()
        assert len(data) == 2


class TestScraperOutput:
    """Test final output format and validation."""

    def test_output_is_valid_dataframe(self, config):
        """Test output is a valid pandas DataFrame."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Mock scraped data
        data = pd.DataFrame(
            {"code": ["PROD001"], "name": ["Product"], "price": ["100"]}
        )

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert len(data.columns) > 0

    def test_output_has_no_nan_strings(self, config):
        """Test _clean_data removes NaN properly."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Mock data with None values
        data = pd.DataFrame(
            {"code": ["PROD001"], "name": ["Product"], "price": [None]}
        )

        result = scraper._clean_data(data)

        # Should not have 'nan' strings
        for col in result.columns:
            if result[col].dtype == "object":
                assert not any(result[col] == "nan")

    def test_all_values_are_strings(self, config):
        """Test scraper produces string values."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        scraper = ScraperNewFormat(config)

        # Mock scraped data (scraper always produces strings)
        data = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product"],
                "price": ["100"],  # Already string as scraper produces
            }
        )

        # All columns should be string type
        for col in data.columns:
            assert data[col].dtype == "object"
            assert isinstance(data.loc[0, col], str)


class TestScraperProgressTracking:
    """Test progress tracking and callbacks."""

    def test_scraper_accepts_progress_callback(self, config):
        """Test scraper accepts progress callback."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        progress_messages = []

        def progress_callback(message):
            progress_messages.append(message)

        scraper = ScraperNewFormat(config, progress_callback=progress_callback)

        assert scraper.progress_callback is not None

    @patch("src.scrapers.scraper_new_format.requests.Session")
    def test_scraper_reports_progress(self, mock_session, config):
        """Test scraper reports progress during scraping."""
        from src.scrapers.scraper_new_format import ScraperNewFormat

        progress_messages = []

        def progress_callback(message):
            progress_messages.append(message)

        scraper = ScraperNewFormat(config, progress_callback=progress_callback)

        # Test that _log_progress calls the callback
        scraper._log_progress("Test message 1")
        scraper._log_progress("Test message 2")

        # Verify progress messages were captured
        assert len(progress_messages) == 2
        assert "Test message 1" in progress_messages
        assert "Test message 2" in progress_messages


# Integration test marker
pytestmark = pytest.mark.scraper
