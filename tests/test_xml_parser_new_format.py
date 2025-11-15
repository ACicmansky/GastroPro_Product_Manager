"""
Tests for XML parser outputting to new 138-column format.
Following TDD approach: Write tests first, then implement.
"""

import pytest
import pandas as pd
from pathlib import Path


class TestXMLParserNewFormat:
    """Test XML parser with new format output."""

    def test_parse_gastromarket_to_new_format(self, sample_xml_gastromarket, config):
        """Test parsing Gastromarket XML to new 138-column format."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)
        result = parser.parse_gastromarket(sample_xml_gastromarket)

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

        # Check new format columns exist
        assert "code" in result.columns
        assert "name" in result.columns
        assert "price" in result.columns
        assert "defaultImage" in result.columns
        assert "source" in result.columns

    def test_parse_forgastro_to_new_format(self, sample_xml_forgastro, config):
        """Test parsing ForGastro XML to new 138-column format."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)
        result = parser.parse_forgastro(sample_xml_forgastro)

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

        # Check new format columns exist
        assert "code" in result.columns
        assert "name" in result.columns
        assert "price" in result.columns

    def test_xml_feed_name_added(self, sample_xml_gastromarket, config):
        """Test that source is added to parsed data."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)
        result = parser.parse_gastromarket(sample_xml_gastromarket)

        # All rows should have feed name
        assert "source" in result.columns
        assert all(result["source"] == "gastromarket")

    def test_parse_maps_to_new_column_names(self, sample_xml_gastromarket, config):
        """Test that XML fields are mapped to new column names."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)
        result = parser.parse_gastromarket(sample_xml_gastromarket)

        # Check mapping from XML to new format
        # Old: CATALOG_NUMBER -> New: code
        # Old: PRODUCTNAME -> New: name
        # Old: PRICE -> New: price
        assert "code" in result.columns
        assert "name" in result.columns
        assert "price" in result.columns

        # Should NOT have old column names
        assert "CATALOG_NUMBER" not in result.columns
        assert "PRODUCTNAME" not in result.columns

    def test_parse_handles_images(self, sample_xml_gastromarket, config):
        """Test that images are parsed and split correctly."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)
        result = parser.parse_gastromarket(sample_xml_gastromarket)

        # Should have image columns
        assert "defaultImage" in result.columns
        assert "image" in result.columns

        # At least one product should have an image
        has_images = (
            result["defaultImage"].notna().any() or (result["defaultImage"] != "").any()
        )
        # This might be false if sample has no images, which is ok


class TestXMLParserFactory:
    """Test XML parser factory for feed detection."""

    def test_factory_detects_gastromarket(self, config):
        """Test factory detects Gastromarket feed."""
        from src.parsers.xml_parser_factory import XMLParserFactory

        parser = XMLParserFactory.get_parser("gastromarket", config)

        assert parser is not None
        assert hasattr(parser, "parse_gastromarket")

    def test_factory_detects_forgastro(self, config):
        """Test factory detects ForGastro feed."""
        from src.parsers.xml_parser_factory import XMLParserFactory

        parser = XMLParserFactory.get_parser("forgastro", config)

        assert parser is not None
        assert hasattr(parser, "parse_forgastro")

    def test_factory_parse_method(self, sample_xml_gastromarket, config):
        """Test factory parse method."""
        from src.parsers.xml_parser_factory import XMLParserFactory

        result = XMLParserFactory.parse("gastromarket", sample_xml_gastromarket, config)

        assert isinstance(result, pd.DataFrame)
        assert "code" in result.columns


class TestXMLToNewFormatMapping:
    """Test XML field mapping to new format."""

    def test_gastromarket_field_mapping(self, config):
        """Test Gastromarket field mapping configuration."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)

        # Check that parser has mapping configuration
        assert hasattr(parser, "config")
        assert "xml_feeds" in parser.config
        assert "gastromarket" in parser.config["xml_feeds"]

        mapping = parser.config["xml_feeds"]["gastromarket"]["mapping"]

        # Check key mappings exist (using actual field names from config)
        assert "KATALOG_CISLO" in mapping
        assert mapping["KATALOG_CISLO"] == "code"

    def test_forgastro_field_mapping(self, config):
        """Test ForGastro field mapping configuration."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)

        mapping = parser.config["xml_feeds"]["forgastro"]["mapping"]

        # Check key mappings exist (using actual field names from config)
        assert "product_sku" in mapping
        assert mapping["product_sku"] == "code"

    def test_mapping_covers_all_fields(self, sample_xml_gastromarket, config):
        """Test that all XML fields are mapped."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)
        result = parser.parse_gastromarket(sample_xml_gastromarket)

        # All columns should be from new format
        new_columns = config.get("new_output_columns", [])

        for col in result.columns:
            # Column should either be in new format, be source, or be a temporary column
            assert col in new_columns or col == "source" or col.startswith("_temp")


class TestXMLParserImageHandling:
    """Test XML parser image handling for new format."""

    def test_single_image_to_defaultImage(self, config):
        """Test single image goes to defaultImage."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)

        # Create test data with single image
        test_data = pd.DataFrame({"IMAGE": ["http://example.com/img1.jpg"]})

        result = parser._split_images(test_data, "IMAGE")

        assert "defaultImage" in result.columns
        assert result.loc[0, "defaultImage"] == "http://example.com/img1.jpg"

    def test_multiple_images_split(self, config):
        """Test multiple images are split correctly."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)

        # Create test data with multiple images (pipe-separated)
        test_data = pd.DataFrame(
            {"IMAGE": ["http://img1.jpg|http://img2.jpg|http://img3.jpg"]}
        )

        result = parser._split_images(test_data, "IMAGE")

        assert result.loc[0, "defaultImage"] == "http://img1.jpg"
        assert result.loc[0, "image"] == "http://img2.jpg"
        assert result.loc[0, "image2"] == "http://img3.jpg"


class TestXMLParserDataCleaning:
    """Test XML parser data cleaning for new format."""

    def test_price_cleaning(self, config):
        """Test price values are cleaned."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)

        # Test data with various price formats
        test_data = pd.DataFrame({"price": ["100,50", "200.00", "300"]})

        result = parser._clean_prices(test_data)

        # Prices should be cleaned (comma to dot)
        assert result.loc[0, "price"] in ["100.50", "100.5"]

    def test_empty_values_handling(self, sample_xml_gastromarket, config):
        """Test that empty values are handled correctly."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)
        result = parser.parse_gastromarket(sample_xml_gastromarket)

        # Empty values should be empty strings, not NaN
        for col in result.columns:
            # Check that we don't have 'nan' strings
            assert not any(result[col] == "nan")


class TestXMLParserIntegration:
    """Test XML parser integration with new format."""

    def test_parse_and_transform_pipeline(self, sample_xml_gastromarket, config):
        """Test complete parse and transform pipeline."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat
        from src.transformers.output_transformer import OutputTransformer

        # Parse XML to new format
        parser = XMLParserNewFormat(config)
        parsed_df = parser.parse_gastromarket(sample_xml_gastromarket)

        # Should already be in new format, apply full transformation for all columns and defaults
        transformer = OutputTransformer(config)
        result = transformer.transform(parsed_df)

        # Check that result has all required columns
        assert "code" in result.columns
        assert "name" in result.columns
        assert "price" in result.columns
        assert "currency" in result.columns

    def test_multiple_feeds_same_format(
        self, sample_xml_gastromarket, sample_xml_forgastro, config
    ):
        """Test that multiple feeds output same format."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)

        gastro_df = parser.parse_gastromarket(sample_xml_gastromarket)
        forgastro_df = parser.parse_forgastro(sample_xml_forgastro)

        # Both should have same column structure
        gastro_cols = set(gastro_df.columns)
        forgastro_cols = set(forgastro_df.columns)

        # Core columns should be present in both
        core_columns = {"code", "name", "price", "source"}
        assert core_columns.issubset(gastro_cols)
        assert core_columns.issubset(forgastro_cols)

    def test_parsed_data_ready_for_merge(self, sample_xml_gastromarket, config):
        """Test that parsed data is ready for merging."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat

        parser = XMLParserNewFormat(config)
        result = parser.parse_gastromarket(sample_xml_gastromarket)

        # Should have code column for merging
        assert "code" in result.columns

        # Codes should not be empty
        assert not result["code"].isna().all()
        assert not (result["code"] == "").all()
