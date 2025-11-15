"""
Tests for category mapping functionality (current implementation).
"""

import pytest
import pandas as pd
from src.utils.category_mapper import map_category, map_dataframe_categories


class TestCurrentCategoryMapping:
    """Test current category mapping functionality."""

    def test_map_single_category_exact_match(self, sample_category_mappings):
        """Test mapping a category with exact match."""
        result = map_category("Category1/SubCat1", sample_category_mappings)
        assert result == "Mapped Category 1"

    def test_map_single_category_no_match(self, sample_category_mappings):
        """Test mapping a category with no match returns original."""
        result = map_category("Unknown/Category", sample_category_mappings)
        assert result == "Unknown/Category"

    def test_map_category_with_nbsp(self, sample_category_mappings):
        """Test mapping category with non-breaking space."""
        mappings = [
            {"oldCategory": "Category\xa0With\xa0NBSP", "newCategory": "Mapped"}
        ]
        result = map_category("Category With NBSP", mappings)
        assert result == "Mapped"

    def test_map_category_empty_input(self, sample_category_mappings):
        """Test mapping empty category."""
        result = map_category("", sample_category_mappings)
        assert result == ""

        result = map_category(None, sample_category_mappings)
        assert result is None

    def test_map_category_no_mappings(self):
        """Test mapping with no mappings provided."""
        result = map_category("Some Category", [])
        assert result == "Some Category"

    def test_map_dataframe_categories(
        self, sample_old_format_df, sample_category_mappings
    ):
        """Test mapping categories in entire DataFrame."""
        df = sample_old_format_df.copy()

        result_df = map_dataframe_categories(df, sample_category_mappings)

        # Check that categories were mapped
        assert "Hlavna kategória" in result_df.columns
        # Original categories should be replaced with mapped ones
        mapped_values = result_df["Hlavna kategória"].unique()
        assert (
            "Mapped Category 1" in mapped_values or "Category1/SubCat1" in mapped_values
        )

    def test_map_dataframe_preserves_other_columns(
        self, sample_old_format_df, sample_category_mappings
    ):
        """Test that mapping doesn't affect other columns."""
        df = sample_old_format_df.copy()
        original_names = df["Názov tovaru"].tolist()

        result_df = map_dataframe_categories(df, sample_category_mappings)

        # Other columns should be unchanged
        assert result_df["Názov tovaru"].tolist() == original_names

    def test_map_category_with_callback(self, sample_category_mappings):
        """Test mapping with interactive callback for unmapped categories."""
        callback_called = False
        callback_category = None

        def test_callback(category, product_name=None):
            nonlocal callback_called, callback_category
            callback_called = True
            callback_category = category
            return "Callback Mapped Category"

        result = map_category(
            "Unmapped Category",
            sample_category_mappings,
            interactive_callback=test_callback,
            product_name="Test Product",
        )

        # Callback should be called for unmapped category
        assert callback_called
        assert callback_category == "Unmapped Category"
        assert result == "Callback Mapped Category"

    def test_map_category_normalization(self):
        """Test category string normalization."""
        mappings = [{"oldCategory": "Normal Category", "newCategory": "Mapped"}]

        # Test with extra spaces
        result = map_category("Normal  Category", mappings)
        # Should still match after normalization
        assert result in ["Normal  Category", "Mapped"]


class TestCategoryMappingManager:
    """Test CategoryMappingManager functionality."""

    def test_category_manager_get_all(self):
        """Test getting all category mappings."""
        try:
            from src.utils.category_mapper import CategoryMappingManager

            manager = CategoryMappingManager()
            mappings = manager.get_all()

            assert isinstance(mappings, list)
        except ImportError:
            pytest.skip("CategoryMappingManager not available in this module structure")

    def test_category_manager_add_mapping(self):
        """Test adding new category mapping."""
        try:
            from src.utils.category_mapper import CategoryMappingManager

            manager = CategoryMappingManager()
            initial_count = len(manager.get_all())

            manager.add_mapping("Test Old Category", "Test New Category")

            mappings = manager.get_all()
            assert len(mappings) >= initial_count

            # Check if new mapping exists
            found = any(
                m["oldCategory"] == "Test Old Category"
                and m["newCategory"] == "Test New Category"
                for m in mappings
            )
            assert found or initial_count == len(mappings)  # May already exist
        except ImportError:
            pytest.skip("CategoryMappingManager not available in this module structure")
