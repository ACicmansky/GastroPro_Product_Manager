"""
Data Merger for new 147-column format with image priority.
Merges main data with multiple feed sources, prioritizing sources with more images.
"""

import pandas as pd
from typing import Dict, Tuple


class DataMergerNewFormat:
    """Merger for new format data with image priority logic."""

    def __init__(self, config: Dict):
        """
        Initialize data merger with configuration.

        Args:
            config: Configuration dictionary from config.json
        """
        self.config = config
        self.image_columns = [
            "defaultImage",
            "image",
            "image2",
            "image3",
            "image4",
            "image5",
            "image6",
            "image7",
        ]

    def merge(
        self, main_df: pd.DataFrame, feed_dfs: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Merge main DataFrame with multiple feed DataFrames.

        Uses image priority: if multiple sources have the same product,
        use the source with the most images.

        Args:
            main_df: Main DataFrame (can be empty)
            feed_dfs: Dictionary of feed name -> DataFrame

        Returns:
            Merged DataFrame
        """
        print("\n" + "=" * 60)
        print("MERGING DATA WITH IMAGE PRIORITY")
        print("=" * 60)

        # Uppercase codes
        if "code" in main_df.columns:
            main_df["code"] = main_df["code"].str.upper()
        for feed_df in feed_dfs.values():
            if "code" in feed_df.columns:
                feed_df["code"] = feed_df["code"].str.upper()

        # Start with main data
        if main_df.empty:
            result_df = pd.DataFrame()
        else:
            result_df = main_df.copy()
            # Ensure code column exists
            if "code" not in result_df.columns:
                result_df["code"] = ""

        # Track products by code
        products_by_code = {}

        # Add main products to tracking
        if not result_df.empty and "code" in result_df.columns:
            for idx, row in result_df.iterrows():
                code = str(row["code"])
                if code and code != "nan" and code != "":
                    products_by_code[code] = {
                        "data": row.to_dict(),
                        "source": "main",
                        "image_count": self._count_images(row),
                    }

        # Process each feed
        for feed_name, feed_df in feed_dfs.items():
            print(f"\nProcessing feed: {feed_name}")

            if feed_df.empty:
                print(f"  Feed {feed_name} is empty, skipping")
                continue

            if "code" not in feed_df.columns:
                print(f"  Warning: Feed {feed_name} has no 'code' column, skipping")
                continue

            for idx, row in feed_df.iterrows():
                code = str(row["code"])
                if not code or code == "nan" or code == "":
                    continue

                image_count = self._count_images(row)

                if code in products_by_code:
                    # Product exists - check if this source has more images
                    existing = products_by_code[code]

                    if image_count > existing["image_count"]:
                        # This source has more images - use its images
                        print(
                            f"  Updating images for {code}: {existing['image_count']} -> {image_count} images"
                        )

                        # Keep main data but update price and images
                        updated_data = existing["data"].copy()
                        updated_data["price"] = row["price"]

                        # Update images
                        for img_col in self.image_columns:
                            if img_col in row:
                                updated_data[img_col] = row[img_col]

                        # Update xmlFeedName if from feed
                        if "xmlFeedName" in row:
                            updated_data["xmlFeedName"] = row["xmlFeedName"]

                        products_by_code[code] = {
                            "data": updated_data,
                            "source": feed_name,
                            "image_count": image_count,
                        }
                    else:
                        # Just update price, keep existing images
                        existing["data"]["price"] = row["price"]
                else:
                    # New product
                    products_by_code[code] = {
                        "data": row.to_dict(),
                        "source": feed_name,
                        "image_count": image_count,
                    }

            print(f"  Processed {len(feed_df)} products from {feed_name}")

        # Build result DataFrame
        if products_by_code:
            result_data = [prod["data"] for prod in products_by_code.values()]
            result_df = pd.DataFrame(result_data)

        print(f"\nMerge complete: {len(result_df)} total products")
        print("=" * 60)

        return result_df

    def merge_with_stats(
        self, main_df: pd.DataFrame, feed_dfs: Dict[str, pd.DataFrame]
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Merge with statistics tracking.

        Args:
            main_df: Main DataFrame
            feed_dfs: Dictionary of feed DataFrames

        Returns:
            Tuple of (merged DataFrame, statistics dict)
        """
        # Track initial state
        initial_codes = set()
        if not main_df.empty and "code" in main_df.columns:
            initial_codes = set(main_df["code"].values)

        # Perform merge
        result_df = self.merge(main_df, feed_dfs)

        # Calculate statistics
        final_codes = (
            set(result_df["code"].values) if "code" in result_df.columns else set()
        )

        new_products = len(final_codes - initial_codes)
        updated_products = len(final_codes & initial_codes)

        stats = {
            "total_products": len(result_df),
            "new_products": new_products,
            "updated_products": updated_products,
            "products_with_images_updated": 0,  # Would need more tracking to calculate accurately
        }

        # Count products with images
        if not result_df.empty:
            products_with_images = 0
            for idx, row in result_df.iterrows():
                if self._count_images(row) > 0:
                    products_with_images += 1
            stats["products_with_images"] = products_with_images

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
