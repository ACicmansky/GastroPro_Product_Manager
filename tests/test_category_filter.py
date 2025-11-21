"""
Tests for category filtering functionality.

Tests the CategoryFilter class that extracts categories from data
and filters products by selected categories.
"""

import pytest
import pandas as pd
from pathlib import Path


@pytest.fixture
def sample_data():
    """Create sample DataFrame with categories."""
    return pd.DataFrame(
        {
            "code": ["PROD001", "PROD002", "PROD003", "PROD004", "PROD005"],
            "name": ["Product 1", "Product 2", "Product 3", "Product 4", "Product 5"],
            "price": ["100", "200", "300", "400", "500"],
            "defaultCategory": [
                "Tovary a kategórie > Chladenie > Chladničky",
                "Tovary a kategórie > Chladenie > Mrazničky",
                "Tovary a kategórie > Chladenie > Chladničky",
                "Tovary a kategórie > Gastro > Sporáky",
                "Tovary a kategórie > Gastro > Rúry",
            ],
        }
    )


@pytest.fixture
def empty_data():
    """Create DataFrame with no categories."""
    return pd.DataFrame(
        {
            "code": ["PROD001", "PROD002"],
            "name": ["Product 1", "Product 2"],
            "price": ["100", "200"],
        }
    )


class TestCategoryExtraction:
    """Test extracting categories from DataFrame."""

    def test_extract_categories_from_data(self, sample_data):
        """Test extracting unique categories from DataFrame."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        categories = filter.extract_categories(sample_data)

        # Should return unique, sorted categories
        assert len(categories) == 4
        assert "Tovary a kategórie > Chladenie > Chladničky" in categories
        assert "Tovary a kategórie > Chladenie > Mrazničky" in categories
        assert "Tovary a kategórie > Gastro > Sporáky" in categories
        assert "Tovary a kategórie > Gastro > Rúry" in categories

    def test_extract_categories_sorted(self, sample_data):
        """Test categories are returned sorted."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        categories = filter.extract_categories(sample_data)

        # Should be sorted alphabetically
        assert categories == sorted(categories)

    def test_extract_categories_no_duplicates(self, sample_data):
        """Test no duplicate categories returned."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        categories = filter.extract_categories(sample_data)

        # Should have no duplicates
        assert len(categories) == len(set(categories))

    def test_extract_categories_missing_column(self, empty_data):
        """Test handling when defaultCategory column missing."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        categories = filter.extract_categories(empty_data)

        # Should return empty list
        assert categories == []

    def test_extract_categories_with_nan(self):
        """Test handling NaN values in categories."""
        from src.filters.category_filter import CategoryFilter

        df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002", "PROD003"],
                "defaultCategory": [
                    "Tovary a kategórie > Category 1",
                    None,
                    "Tovary a kategórie > Category 2",
                ],
            }
        )

        filter = CategoryFilter()
        categories = filter.extract_categories(df)

        # Should skip NaN values
        assert len(categories) == 2
        assert None not in categories

    def test_extract_categories_with_empty_strings(self):
        """Test handling empty string categories."""
        from src.filters.category_filter import CategoryFilter

        df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002", "PROD003"],
                "defaultCategory": [
                    "Tovary a kategórie > Category 1",
                    "",
                    "Tovary a kategórie > Category 2",
                ],
            }
        )

        filter = CategoryFilter()
        categories = filter.extract_categories(df)

        # Should skip empty strings
        assert len(categories) == 2
        assert "" not in categories


class TestCategoryFiltering:
    """Test filtering products by categories."""

    def test_filter_by_single_category(self, sample_data):
        """Test filtering by single category."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        selected = ["Tovary a kategórie > Chladenie > Chladničky"]

        result = filter.filter_by_categories(sample_data, selected)

        # Should return only products in selected category
        assert len(result) == 2
        assert all(result["defaultCategory"] == selected[0])

    def test_filter_by_multiple_categories(self, sample_data):
        """Test filtering by multiple categories."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        selected = [
            "Tovary a kategórie > Chladenie > Chladničky",
            "Tovary a kategórie > Gastro > Sporáky",
        ]

        result = filter.filter_by_categories(sample_data, selected)

        # Should return products in any of selected categories
        assert len(result) == 3
        assert all(result["defaultCategory"].isin(selected))

    def test_filter_by_empty_list_returns_all(self, sample_data):
        """Test filtering with empty selection returns all products."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        result = filter.filter_by_categories(sample_data, [])

        # Should return all products
        assert len(result) == len(sample_data)

    def test_filter_by_none_returns_all(self, sample_data):
        """Test filtering with None returns all products."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        result = filter.filter_by_categories(sample_data, None)

        # Should return all products
        assert len(result) == len(sample_data)

    def test_filter_preserves_data_integrity(self, sample_data):
        """Test filtering preserves all columns and data."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        selected = ["Tovary a kategórie > Chladenie > Chladničky"]

        result = filter.filter_by_categories(sample_data, selected)

        # Should preserve all columns
        assert list(result.columns) == list(sample_data.columns)

        # Should preserve data in other columns
        assert result.iloc[0]["code"] == "PROD001"
        assert result.iloc[0]["name"] == "Product 1"

    def test_filter_nonexistent_category(self, sample_data):
        """Test filtering by category that doesn't exist."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        selected = ["Tovary a kategórie > Nonexistent > Category"]

        result = filter.filter_by_categories(sample_data, selected)

        # Should return empty DataFrame
        assert len(result) == 0

    def test_filter_maintains_index(self, sample_data):
        """Test filtering maintains original DataFrame index."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        selected = ["Tovary a kategórie > Chladenie > Chladničky"]

        result = filter.filter_by_categories(sample_data, selected)

        # Should maintain original indices (0 and 2)
        assert 0 in result.index
        assert 2 in result.index


class TestCategorySearch:
    """Test category search/filter functionality."""

    def test_search_categories_by_text(self):
        """Test searching categories by text."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        categories = [
            "Tovary a kategórie > Chladenie > Chladničky",
            "Tovary a kategórie > Chladenie > Mrazničky",
            "Tovary a kategórie > Gastro > Sporáky",
            "Tovary a kategórie > Gastro > Rúry",
        ]

        result = filter.search_categories(categories, "Chladenie")

        # Should return only categories containing "Chladenie"
        assert len(result) == 2
        assert all("Chladenie" in cat for cat in result)

    def test_search_categories_case_insensitive(self):
        """Test search is case-insensitive."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        categories = [
            "Tovary a kategórie > Chladenie > Chladničky",
            "Tovary a kategórie > Gastro > Sporáky",
        ]

        result = filter.search_categories(categories, "chladenie")

        # Should find match regardless of case
        assert len(result) == 1
        assert "Chladenie" in result[0]

    def test_search_categories_empty_query(self):
        """Test search with empty query returns all."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        categories = [
            "Tovary a kategórie > Chladenie > Chladničky",
            "Tovary a kategórie > Gastro > Sporáky",
        ]

        result = filter.search_categories(categories, "")

        # Should return all categories
        assert len(result) == len(categories)

    def test_search_categories_no_matches(self):
        """Test search with no matches returns empty list."""
        from src.filters.category_filter import CategoryFilter

        filter = CategoryFilter()
        categories = [
            "Tovary a kategórie > Chladenie > Chladničky",
            "Tovary a kategórie > Gastro > Sporáky",
        ]

        result = filter.search_categories(categories, "Nonexistent")

        # Should return empty list
        assert result == []


class TestCategoryFilterIntegration:
    """Test integration with pipeline."""

    def test_filter_integrates_with_pipeline(self, sample_data):
        """Test category filter works with pipeline."""
        from src.filters.category_filter import CategoryFilter
        from src.pipeline.pipeline_new_format import PipelineNewFormat
        import json

        # Load config
        config_path = Path("config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        filter = CategoryFilter()
        pipeline = PipelineNewFormat(config, {})

        # Filter data
        selected = ["Tovary a kategórie > Chladenie > Chladničky"]
        filtered_data = filter.filter_by_categories(sample_data, selected)

        # Process through pipeline
        result = pipeline.apply_transformation(filtered_data)

        # Should process successfully
        assert len(result) == 2
        assert all(result["defaultCategory"] == selected[0])


# Integration test marker
pytestmark = pytest.mark.category_filter
