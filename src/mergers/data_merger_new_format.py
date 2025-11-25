"""
Data Merger for new 138-column format with image priority.
Merges main data with multiple feed sources, prioritizing sources with more images.
"""

import pandas as pd
from typing import Dict, Tuple, Optional, List
from datetime import datetime


class DataMergerNewFormat:
    """Merger for new format data with image priority logic."""

    def __init__(self, options: Dict):
        """
        Initialize data merger with configuration.

        Args:
            options: Options from GUI
        """

        self.options = options
        self.image_columns = [
            "image",
            "image2",
            "image3",
            "image4",
            "image5",
            "image6",
            "image7",
            "image8",
        ]

    def merge(
        self,
        main_df: pd.DataFrame,
        feed_dfs: Dict[str, pd.DataFrame],
        selected_categories: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Merge main DataFrame with multiple feed DataFrames.

        Features:
        1. Image priority: if multiple sources have the same product, use the source with the most images.
        2. Category filtering: if selected_categories is provided, only include main products from those categories.
        3. Statistics: returns detailed statistics about the merge process.

        Args:
            main_df: Main DataFrame (can be empty)
            feed_dfs: Dictionary of feed name -> DataFrame
            selected_categories: Optional list of selected category names (None = all)

        Returns:
            Tuple of (Merged DataFrame, Statistics dictionary)
        """
        print("\n" + "=" * 60)
        print("MERGING DATA")
        if selected_categories:
            print(
                f"Category filter active: {len(selected_categories)} categories selected"
            )
        print("=" * 60)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Track statistics
        stats = {
            "created": {},  # By source
            "updated": {},  # By source
            "removed": 0,
            "total_created": 0,
            "total_updated": 0,
            "total_kept": 0,
            "total_products": 0,
        }

        # Initialize counters for each feed
        for feed_name in feed_dfs.keys():
            stats["created"][feed_name] = 0
            stats["updated"][feed_name] = 0
        stats["created"]["core"] = 0

        # Uppercase codes for matching
        if not main_df.empty and "code" in main_df.columns:
            main_df["code"] = main_df["code"].str.upper()
        for feed_name, feed_df in feed_dfs.items():
            if not feed_df.empty and "code" in feed_df.columns:
                feed_df["code"] = feed_df["code"].str.upper()

        # Track products by code
        products_by_code = {}
        processed_codes = set()

        # Step 1: Process feed/scraped products (always included)
        print("\nStep 1: Processing feed/scraped products (always included)...")
        for feed_name, feed_df in feed_dfs.items():
            if feed_df.empty or "code" not in feed_df.columns:
                continue

            print(f"  Processing {feed_name}: {len(feed_df)} products")

            for idx, row in feed_df.iterrows():
                code = str(row["code"])
                if not code or code == "nan" or code == "":
                    continue

                # Check if product exists in main data
                main_product = None
                if not main_df.empty and "code" in main_df.columns:
                    main_match = main_df[main_df["code"] == code]
                    if not main_match.empty:
                        main_product = main_match.iloc[0].to_dict()

                if main_product:
                    # Update existing product
                    merged_data = main_product.copy()

                    # Update price from feed
                    if "price" in row and pd.notna(row["price"]):
                        merged_data["price"] = str(row["price"])

                    # Update images from feed (if feed has more images)
                    feed_image_count = self._count_images(row)
                    main_image_count = self._count_images(pd.Series(main_product))

                    if feed_image_count > main_image_count:
                        for img_col in self.image_columns:
                            if img_col in row:
                                merged_data[img_col] = str(row[img_col])

                    # Update categories from feed if enabled in options
                    if self.options.get("update_categories_from_feeds", False):
                        if "defaultCategory" in row and pd.notna(
                            row["defaultCategory"]
                        ):
                            merged_data["defaultCategory"] = str(row["defaultCategory"])
                        if "categoryText" in row and pd.notna(row["categoryText"]):
                            merged_data["categoryText"] = str(row["categoryText"])

                    # Update pairCode from feed if present
                    if "pairCode" in row and pd.notna(row["pairCode"]):
                        merged_data["pairCode"] = str(row["pairCode"])

                    merged_data["source"] = feed_name
                    merged_data["last_updated"] = current_time
                    products_by_code[code] = merged_data
                    processed_codes.add(code)
                    stats["updated"][feed_name] += 1
                    stats["total_updated"] += 1
                else:
                    # New product from feed
                    product_data = row.to_dict()
                    product_data["source"] = feed_name
                    product_data["last_updated"] = current_time
                    products_by_code[code] = product_data
                    processed_codes.add(code)
                    stats["created"][feed_name] += 1
                    stats["total_created"] += 1

        # Step 2: Process main data products (only if in selected categories)
        print("\nStep 2: Processing main data products...")
        if not main_df.empty and "code" in main_df.columns:
            for idx, row in main_df.iterrows():
                code = str(row["code"])
                if not code or code == "nan" or code == "":
                    continue

                # Skip if already added/updated by feed
                if code in processed_codes:
                    continue

                # Check category filter
                if selected_categories is not None:
                    product_category = str(row.get("defaultCategory", ""))
                    if product_category not in selected_categories:
                        # Product removed (in unchecked category)
                        stats["removed"] += 1
                        continue

                # Include product from main data
                product_data = row.to_dict()
                # if source column has empty value then set to core
                if "source" in product_data and product_data["source"] == "":
                    product_data["source"] = "core"
                product_data["last_updated"] = current_time
                products_by_code[code] = product_data
                processed_codes.add(code)
                stats["total_kept"] += 1

        # Build result DataFrame
        if products_by_code:
            result_df = pd.DataFrame(list(products_by_code.values()))
        else:
            result_df = pd.DataFrame()

        # Add summary stats
        stats["total_products"] = len(result_df)

        # Print summary
        print(f"\nMerge complete: {len(result_df)} total products")
        print(
            f"  Created: {stats['total_created']}, Updated: {stats['total_updated']}, Kept: {stats['total_kept']}, Removed: {stats['removed']}"
        )
        print("=" * 60)

        return result_df, stats

    def _count_images(self, row: pd.Series) -> int:
        """
        Count non-empty images in a row.

        Args:
            row: DataFrame row

        Returns:
            Number of non-empty images
        """
        count = 0
        for img_col in self.image_columns:
            if img_col in row:
                value = str(row[img_col])
                if value and value != "nan" and value != "" and value != "None":
                    count += 1
        return count
