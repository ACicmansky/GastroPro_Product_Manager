"""
Tests for category mapper with new format transformation.
Following TDD approach: Write tests first, then implement.
"""

import pytest
import pandas as pd


class TestCategoryMapperNewFormat:
    """Test category mapper with new format transformation."""

    def test_mapper_initialization(self, config):
        """Test category mapper initializes with config."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        mapper = CategoryMapperNewFormat(config)

        assert mapper.config is not None
        assert hasattr(mapper, "map_category")

    def test_apply_category_transformation(self, config):
        """Test applying category transformation to new format."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        mapper = CategoryMapperNewFormat(config)

        # Input: old format category
        input_category = "Vitríny/Chladiace vitríny"

        # Expected: new format with prefix and separator change
        result = mapper.transform_category(input_category)

        assert result == "Tovary a kategórie > Vitríny > Chladiace vitríny"

    def test_transform_adds_prefix(self, config):
        """Test that transformation adds required prefix."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        mapper = CategoryMapperNewFormat(config)

        result = mapper.transform_category("Kategória")

        assert result.startswith("Tovary a kategórie > ")

    def test_transform_replaces_separator(self, config):
        """Test that transformation replaces / with >."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        mapper = CategoryMapperNewFormat(config)

        result = mapper.transform_category("Cat1/Cat2/Cat3")

        assert "/" not in result
        assert "Cat1 > Cat2 > Cat3" in result

    def test_transform_empty_category(self, config):
        """Test transformation of empty category."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        mapper = CategoryMapperNewFormat(config)

        result = mapper.transform_category("")

        assert result == ""


class TestCategoryMappingDataFrame:
    """Test category mapping on DataFrames."""

    def test_map_dataframe_categories(self, config):
        """Test mapping categories in DataFrame."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["Product 1", "Product 2"],
                "defaultCategory": ["Vitríny/Chladiace", "Umývačky/Priemyselné"],
            }
        )

        mapper = CategoryMapperNewFormat(config)
        result = mapper.map_dataframe(df)

        # Should have transformed categories
        assert all(result["defaultCategory"].str.startswith("Tovary a kategórie > "))
        assert all(~result["defaultCategory"].str.contains("/"))

    def test_map_updates_both_category_columns(self, config):
        """Test that both defaultCategory and categoryText are updated."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "defaultCategory": ["Vitríny/Chladiace"],
                "categoryText": [""],
            }
        )

        mapper = CategoryMapperNewFormat(config)
        result = mapper.map_dataframe(df)

        # Both should be updated with same value
        assert result.loc[0, "defaultCategory"] == result.loc[0, "categoryText"]
        assert "Tovary a kategórie > " in result.loc[0, "categoryText"]

    def test_map_preserves_other_columns(self, config):
        """Test that mapping preserves other columns."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "defaultCategory": ["Vitríny"],
            }
        )

        mapper = CategoryMapperNewFormat(config)
        result = mapper.map_dataframe(df)

        # Other columns should be unchanged
        assert result.loc[0, "code"] == "PROD001"
        assert result.loc[0, "name"] == "Product 1"
        assert result.loc[0, "price"] == "100.00"


class TestCategoryMappingWithMappingFile:
    """Test category mapping with mapping file."""

    def test_load_category_mappings(self, config, sample_category_mappings):
        """Test loading category mappings from file."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        mapper = CategoryMapperNewFormat(config)

        # Sample fixture returns a list, so we test the method exists
        # In production, this would load from a file
        assert hasattr(mapper, "load_mappings")

        # Test that it can handle dict input
        if isinstance(sample_category_mappings, list):
            # Convert list to dict for testing
            test_mappings = {
                item["oldCategory"]: item["newCategory"]
                for item in sample_category_mappings
            }
            mapper.set_custom_mappings(test_mappings)
            assert len(mapper.custom_mappings) > 0

    def test_apply_custom_mapping(self, config):
        """Test applying custom category mapping."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        mapper = CategoryMapperNewFormat(config)

        # Custom mapping
        custom_mappings = {"Old Category": "New Category"}

        if hasattr(mapper, "set_custom_mappings"):
            mapper.set_custom_mappings(custom_mappings)

            result = mapper.map_category("Old Category")

            # Should use custom mapping and apply transformation
            assert "New Category" in result
            assert "Tovary a kategórie > " in result

    def test_fallback_to_original_if_no_mapping(self, config):
        """Test fallback to original category if no mapping exists."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        mapper = CategoryMapperNewFormat(config)

        # Category with no mapping
        result = mapper.map_category("Unknown Category")

        # Should still apply transformation
        assert "Tovary a kategórie > Unknown Category" == result


class TestCategoryTransformationEdgeCases:
    """Test edge cases in category transformation."""

    def test_transform_multiple_slashes(self, config):
        """Test transformation with multiple consecutive slashes."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        mapper = CategoryMapperNewFormat(config)

        result = mapper.transform_category("Cat1//Cat2///Cat3")

        # Should handle multiple slashes
        assert "//" not in result
        assert "///" not in result

    def test_transform_leading_trailing_slashes(self, config):
        """Test transformation with leading/trailing slashes."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        mapper = CategoryMapperNewFormat(config)

        result = mapper.transform_category("/Category/")

        # Should handle cleanly
        assert not result.endswith(" > ")
        assert "Tovary a kategórie > " in result

    def test_transform_special_characters(self, config):
        """Test transformation with special characters."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        mapper = CategoryMapperNewFormat(config)

        result = mapper.transform_category("Kategória/Špeciálne")

        # Should preserve special characters
        assert "Kategória" in result
        assert "Špeciálne" in result

    def test_transform_whitespace(self, config):
        """Test transformation handles whitespace correctly."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        mapper = CategoryMapperNewFormat(config)

        result = mapper.transform_category("Cat1 / Cat2 / Cat3")

        # Should handle spaces around slashes
        assert "Cat1 > Cat2 > Cat3" in result


class TestCategoryMappingIntegration:
    """Test category mapping integration with pipeline."""

    def test_map_after_xml_parsing(self, config, sample_xml_gastromarket):
        """Test category mapping after XML parsing."""
        from src.parsers.xml_parser_new_format import XMLParserNewFormat
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        # Parse XML
        parser = XMLParserNewFormat(config)
        parsed_df = parser.parse_gastromarket(sample_xml_gastromarket)

        # Map categories
        mapper = CategoryMapperNewFormat(config)
        result = mapper.map_dataframe(parsed_df)

        # Categories should be transformed
        if "defaultCategory" in result.columns:
            for cat in result["defaultCategory"]:
                if cat and cat != "":
                    assert "Tovary a kategórie > " in cat or cat == ""

    def test_map_preserves_feed_name(self, config):
        """Test that category mapping preserves source."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "defaultCategory": ["Vitríny"],
                "source": ["gastromarket"],
            }
        )

        mapper = CategoryMapperNewFormat(config)
        result = mapper.map_dataframe(df)

        # source should be preserved
        assert result.loc[0, "source"] == "gastromarket"

    def test_map_works_with_merged_data(self, config):
        """Test category mapping works with merged data."""
        from src.mappers.category_mapper_new_format import CategoryMapperNewFormat

        # Simulated merged data
        df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002", "PROD003"],
                "name": ["P1", "P2", "P3"],
                "defaultCategory": ["Cat1/Sub1", "Cat2/Sub2", "Cat3"],
                "source": ["feed1", "feed2", ""],
            }
        )

        mapper = CategoryMapperNewFormat(config)
        result = mapper.map_dataframe(df)

        # All categories should be transformed
        assert len(result) == 3
        for idx, row in result.iterrows():
            if row["defaultCategory"]:
                assert "Tovary a kategórie > " in row["defaultCategory"]
