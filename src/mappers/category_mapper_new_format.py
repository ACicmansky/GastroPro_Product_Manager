"""
Category Mapper for new 138-column format.
Applies category transformation: adds prefix and changes separator.
"""

import pandas as pd
from typing import Dict, Optional, Callable
import re
from ..utils.config_loader import CategoryMappingManager


class CategoryMapperNewFormat:
    """Category mapper with new format transformation."""

    def __init__(self, config: Dict, mappings_path: str = "categories.json"):
        """
        Initialize category mapper with configuration.

        Args:
            config: Configuration dictionary from config.json
            mappings_path: Path to category mappings JSON file
        """
        self.config = config
        self.custom_mappings = {}
        self.category_manager = CategoryMappingManager(mappings_path)
        self.interactive_callback = None

    def map_category(self, category: str, product_name: Optional[str] = None) -> str:
        """
        Map category using mappings.

        Mapping priority:
        1. Check CategoryMappingManager (loaded from categories.json)
        2. Check custom mappings
        3. If not found and interactive_callback is set, prompt user
        4. If not found, return original category

        Args:
            category: Original category
            product_name: Optional product name for context in interactive dialog

        Returns:
            Mapped category string
        """
        if not category or category in ["", "nan", "None"]:
            return ""

        original_category = str(category).strip()

        # 1. Check CategoryMappingManager first
        manager_mapping = self.category_manager.find_mapping(original_category)
        if manager_mapping:
            return manager_mapping

        # 2. Check custom mappings
        if original_category in self.custom_mappings:
            return self.custom_mappings[original_category]

        # 3. Check if it is already a valid target category
        if self.category_manager.is_target_category(original_category):
            return original_category

        # 4. Interactive callback for unmapped categories
        if self.interactive_callback:
            print(f"\n  [INTERACTIVE] Unmapped category found: '{original_category}'")
            print(f"  [INTERACTIVE] Product: '{product_name}'")
            print(f"  [INTERACTIVE] Requesting user input...")
            new_category = self.interactive_callback(original_category, product_name)
            print(f"  [INTERACTIVE] User response: '{new_category}'")

            # Always save the mapping (even if user cancelled or kept original)
            # This prevents asking for the same category multiple times
            if new_category and new_category != original_category:
                # User provided a new category
                self.category_manager.add_mapping(original_category, new_category)
                return new_category
            else:
                # User cancelled or kept original - save original→original to avoid re-asking
                self.category_manager.add_mapping(original_category, original_category)
                return original_category

        # No mapping found and no interactive callback
        if original_category:
            print(
                f"  [WARNING] No mapping for '{original_category}' and no interactive callback set"
            )

        # Return original category if no mapping found
        return original_category

    def map_dataframe(
        self, df: pd.DataFrame, enable_interactive: bool = True
    ) -> pd.DataFrame:
        """
        Map categories in DataFrame.

        Updates both defaultCategory and categoryText columns.

        Args:
            df: DataFrame with category columns
            enable_interactive: If True, prompts user for unmapped categories

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

        # Map and transform defaultCategory
        print("\nMapping and transforming categories...")
        print(
            f"  Interactive mapping: {'ENABLED' if enable_interactive else 'DISABLED'}"
        )
        print(
            f"  Interactive callback: {'SET' if self.interactive_callback else 'NOT SET'}"
        )
        if enable_interactive:
            # Map with interactive callback (includes transformation)
            # Process row by row to ensure new mappings are immediately available
            for idx in result_df.index:
                category = (
                    str(result_df.at[idx, "defaultCategory"])
                    if pd.notna(result_df.at[idx, "defaultCategory"])
                    else ""
                )
                product_name = (
                    str(result_df.at[idx, "name"])
                    if pd.notna(result_df.at[idx, "name"])
                    else None
                )
                result_df.at[idx, "defaultCategory"] = self.map_category(
                    category, product_name
                )
        else:
            # Just transform (no interactive mapping)
            # Since transform_category is removed, we just use map_category without interaction
            # or if we want to support direct mapping without interaction:
            result_df["defaultCategory"] = result_df["defaultCategory"].apply(
                lambda x: self.map_category(str(x)) if pd.notna(x) else ""
            )

        # Copy to categoryText (both should have same value)
        result_df["categoryText"] = result_df["defaultCategory"]

        # Count transformed
        transformed_count = (result_df["defaultCategory"] != "").sum()

        print(f"  Transformed {transformed_count} categories")
        print("=" * 60)

        return result_df

    def set_interactive_callback(
        self, callback: Optional[Callable[[str, Optional[str]], str]]
    ):
        """
        Set callback function for interactive category mapping.

        The callback should accept (original_category, product_name) and return new_category.

        Args:
            callback: Function(original_category: str, product_name: Optional[str]) -> str
        """
        self.interactive_callback = callback

    def set_custom_mappings(self, mappings: Dict[str, str]):
        """
        Set custom category mappings.

        Args:
            mappings: Dictionary of old_category -> new_category
        """
        self.custom_mappings = mappings
        print(f"Loaded {len(mappings)} custom category mappings")

    def reload_mappings(self):
        """
        Reload category mappings from disk.
        Useful after external changes to categories.json.
        """
        self.category_manager.reload()
        print("Reloaded category mappings from disk")

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
