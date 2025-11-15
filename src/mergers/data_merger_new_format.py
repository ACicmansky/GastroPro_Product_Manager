"""
Data Merger for new 138-column format with image priority.
Merges main data with multiple feed sources, prioritizing sources with more images.
"""

import pandas as pd
from typing import Dict, Tuple, Optional, List
from datetime import datetime


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

                        # Update source if from feed
                        if "source" in row:
                            updated_data["source"] = row["source"]

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

    def merge_with_category_filter(
        self,
        main_df: pd.DataFrame,
        feed_dfs: Dict[str, pd.DataFrame],
        selected_categories: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Merge with new category filtering logic.
        
        Requirements:
        1. Feed/scraped products always included (update price/images if exists in main)
        2. Main data products only if in selected categories
        3. Track source and last_updated
        
        Args:
            main_df: Main DataFrame from loaded file
            feed_dfs: Dictionary of feed name -> DataFrame
            selected_categories: List of selected category names (None = all)
        
        Returns:
            Merged DataFrame with source and last_updated columns
        """
        print("\n" + "=" * 60)
        print("MERGING WITH CATEGORY FILTERING")
        print("=" * 60)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Uppercase codes for matching
        if not main_df.empty and "code" in main_df.columns:
            main_df["code"] = main_df["code"].str.upper()
        for feed_name, feed_df in feed_dfs.items():
            if not feed_df.empty and "code" in feed_df.columns:
                feed_df["code"] = feed_df["code"].str.upper()
        
        # Track products by code
        products_by_code = {}
        
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
                    # Req 1.2: Update price and images from feed
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
                    
                    merged_data["source"] = feed_name
                    merged_data["last_updated"] = current_time
                    products_by_code[code] = merged_data
                    print(f"    Updated {code} from {feed_name}")
                else:
                    # Req 1.1: New product from feed
                    product_data = row.to_dict()
                    product_data["source"] = feed_name
                    product_data["last_updated"] = current_time
                    products_by_code[code] = product_data
                    print(f"    Added new {code} from {feed_name}")
        
        # Step 2: Process main data products (only if in selected categories)
        print("\nStep 2: Processing main data products (category filtered)...")
        if not main_df.empty and "code" in main_df.columns:
            for idx, row in main_df.iterrows():
                code = str(row["code"])
                if not code or code == "nan" or code == "":
                    continue
                
                # Skip if already added/updated by feed
                if code in products_by_code:
                    continue
                
                # Check category filter
                if selected_categories is not None:
                    product_category = str(row.get("defaultCategory", ""))
                    if product_category not in selected_categories:
                        # Req 3: Skip products in unchecked categories
                        continue
                
                # Req 2: Include product from main data
                product_data = row.to_dict()
                product_data["source"] = "core"
                product_data["last_updated"] = current_time
                products_by_code[code] = product_data
        
        # Build result DataFrame
        if products_by_code:
            result_df = pd.DataFrame(list(products_by_code.values()))
        else:
            result_df = pd.DataFrame()
        
        print(f"\nMerge complete: {len(result_df)} total products")
        if selected_categories:
            print(f"  Category filter: {len(selected_categories)} categories selected")
        print("=" * 60)
        
        return result_df

    def merge_with_category_filter_and_stats(
        self,
        main_df: pd.DataFrame,
        feed_dfs: Dict[str, pd.DataFrame],
        selected_categories: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Merge with category filtering and return detailed statistics.
        
        Args:
            main_df: Main DataFrame from loaded file
            feed_dfs: Dictionary of feed name -> DataFrame
            selected_categories: List of selected category names (None = all)
        
        Returns:
            Tuple of (merged DataFrame, statistics dict)
        """
        print("\n" + "=" * 60)
        print("MERGING WITH CATEGORY FILTERING")
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
        }
        
        # Initialize counters for each feed
        for feed_name in feed_dfs.keys():
            stats["created"][feed_name] = 0
            stats["updated"][feed_name] = 0
        stats["created"]["core"] = 0
        
        # Track original main data codes
        original_main_codes = set()
        if not main_df.empty and "code" in main_df.columns:
            original_main_codes = set(main_df["code"].str.upper().values)
        
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
        print("\nStep 2: Processing main data products (category filtered)...")
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
        stats["original_main_products"] = len(original_main_codes)
        
        # Print summary
        print(f"\nMerge complete: {len(result_df)} total products")
        if selected_categories:
            print(f"  Category filter: {len(selected_categories)} categories selected")
        print(f"  Created: {stats['total_created']}, Updated: {stats['total_updated']}, Kept: {stats['total_kept']}, Removed: {stats['removed']}")
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
