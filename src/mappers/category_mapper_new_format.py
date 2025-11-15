"""
Category Mapper for new 147-column format.
Applies category transformation: adds prefix and changes separator.
"""

import pandas as pd
from typing import Dict, Optional
import re


class CategoryMapperNewFormat:
    """Category mapper with new format transformation."""

    def __init__(self, config: Dict):
        """
        Initialize category mapper with configuration.

        Args:
            config: Configuration dictionary from config.json
        """
        self.config = config
        self.custom_mappings = {}
        self.prefix = "Tovary a kategórie > "

    def transform_category(self, category: str) -> str:
        """
        Transform category to new format.

        Transformation:
        1. Add prefix "Tovary a kategórie > "
        2. Replace "/" with " > "

        Args:
            category: Original category string

        Returns:
            Transformed category string
        """
        if not category or category in ["", "nan", "None"]:
            return ""

        # Clean the category
        category = str(category).strip()

        if not category:
            return ""

        # Replace multiple slashes with single slash
        category = re.sub(r"/+", "/", category)

        # Remove leading/trailing slashes
        category = category.strip("/")

        if not category:
            return ""

        # Replace / with >
        # Handle spaces around slashes
        category = re.sub(r"\s*/\s*", " > ", category)

        # Add prefix
        result = self.prefix + category

        return result

    def map_category(self, category: str) -> str:
        """
        Map category using custom mappings, then apply transformation.

        Args:
            category: Original category

        Returns:
            Mapped and transformed category
        """
        # Check custom mappings first
        if category in self.custom_mappings:
            category = self.custom_mappings[category]

        # Apply transformation
        return self.transform_category(category)

    def map_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map categories in DataFrame.

        Updates both defaultCategory and categoryText columns.

        Args:
            df: DataFrame with category columns

        Returns:
            DataFrame with transformed categories
        """
        print("\n" + "=" * 60)
        print("CATEGORY MAPPING")
        print("=" * 60)

        result_df = df.copy()

        # Ensure category columns exist
        if "defaultCategory" not in result_df.columns:
            result_df["defaultCategory"] = ""
        if "categoryText" not in result_df.columns:
            result_df["categoryText"] = ""

        # Transform defaultCategory
        print("\nTransforming categories...")
        result_df["defaultCategory"] = result_df["defaultCategory"].apply(
            lambda x: self.transform_category(str(x)) if pd.notna(x) else ""
        )

        # Copy to categoryText (both should have same value)
        result_df["categoryText"] = result_df["defaultCategory"]

        # Count transformed
        transformed_count = (result_df["defaultCategory"] != "").sum()

        print(f"  Transformed {transformed_count} categories")
        print("=" * 60)

        return result_df

    def set_custom_mappings(self, mappings: Dict[str, str]):
        """
        Set custom category mappings.

        Args:
            mappings: Dictionary of old_category -> new_category
        """
        self.custom_mappings = mappings
        print(f"Loaded {len(mappings)} custom category mappings")

    def load_mappings(self, file_path: str) -> Dict[str, str]:
        """
        Load category mappings from file.

        Args:
            file_path: Path to mappings file (CSV or JSON)

        Returns:
            Dictionary of mappings
        """
        import json
        from pathlib import Path

        path = Path(file_path)

        if not path.exists():
            print(f"Warning: Mappings file not found: {file_path}")
            return {}

        if path.suffix == ".json":
            with open(path, "r", encoding="utf-8") as f:
                mappings = json.load(f)
        elif path.suffix == ".csv":
            # Load CSV with old_category, new_category columns
            df = pd.read_csv(path, encoding="utf-8")
            if "old_category" in df.columns and "new_category" in df.columns:
                mappings = dict(zip(df["old_category"], df["new_category"]))
            else:
                print(
                    "Warning: CSV must have 'old_category' and 'new_category' columns"
                )
                mappings = {}
        else:
            print(f"Warning: Unsupported file format: {path.suffix}")
            mappings = {}

        print(f"Loaded {len(mappings)} category mappings from {file_path}")
        return mappings
