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


# Integration test marker
pytestmark = pytest.mark.category_filter
