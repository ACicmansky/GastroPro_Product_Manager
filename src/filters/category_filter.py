"""
Category filtering for product data.

Provides functionality to extract categories from data and filter products
by selected categories.
"""

import pandas as pd
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class CategoryFilter:
    """
    Filter products by categories.

    Extracts unique categories from DataFrame and filters products
    based on selected categories.
    """

    def extract_categories(self, df: pd.DataFrame) -> List[str]:
        """
        Extract unique categories from DataFrame.

        Args:
            df: DataFrame with product data

        Returns:
            Sorted list of unique category names
        """
        if "defaultCategory" not in df.columns:
            logger.warning("defaultCategory column not found in DataFrame")
            return []

        # Get unique categories, drop NaN and empty strings
        categories = df["defaultCategory"].dropna().unique().tolist()
        categories = [cat for cat in categories if cat and str(cat).strip()]

        # Sort alphabetically
        categories = sorted(categories)

        logger.info(f"Extracted {len(categories)} unique categories")
        return categories

    def filter_by_categories(
        self, df: pd.DataFrame, selected_categories: Optional[List[str]]
    ) -> pd.DataFrame:
        """
        Filter DataFrame to include only products in selected categories.

        Args:
            df: DataFrame with product data
            selected_categories: List of category names to include (None or empty = all)

        Returns:
            Filtered DataFrame
        """
        # If no categories selected, return all data
        if not selected_categories:
            logger.info("No categories selected, returning all products")
            return df

        # Filter by selected categories
        if "defaultCategory" in df.columns:
            filtered_df = df[df["defaultCategory"].isin(selected_categories)]
            logger.info(
                f"Filtered {len(df)} products to {len(filtered_df)} "
                f"products in {len(selected_categories)} categories"
            )
            return filtered_df
        else:
            logger.warning("defaultCategory column not found, returning all products")
            return df

    def search_categories(self, categories: List[str], search_text: str) -> List[str]:
        """
        Search/filter categories by text.

        Args:
            categories: List of category names
            search_text: Text to search for (case-insensitive)

        Returns:
            Filtered list of categories containing search text
        """
        if not search_text or not search_text.strip():
            return categories

        search_text_lower = search_text.lower()
        filtered = [cat for cat in categories if search_text_lower in cat.lower()]

        logger.debug(
            f"Searched for '{search_text}', found {len(filtered)} matching categories"
        )
        return filtered
