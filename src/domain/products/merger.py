"""Product data merging from multiple sources."""

import logging
from typing import Dict, List, Optional

import pandas as pd

from src.domain.models import MergeResult, MergeStats

logger = logging.getLogger(__name__)


class ProductMerger:
    """Merges product data from main file and XML feed sources."""

    IMAGE_COLUMNS = [
        "image1", "image2", "image3", "image4", "image5",
        "image6", "image7", "image8", "image9", "image10",
    ]

    def merge(
        self,
        main_df: pd.DataFrame,
        feed_dfs: Dict[str, pd.DataFrame],
        selected_categories: Optional[List[str]] = None,
        preserve_edits: bool = False,
    ) -> MergeResult:
        """Merge main data with feed data.

        Args:
            main_df: Main product DataFrame
            feed_dfs: Dict of source_name -> DataFrame from feeds
            selected_categories: Categories to include (None = all)
            preserve_edits: If True, only update price/stock from feeds

        Returns:
            MergeResult with merged products and statistics
        """
        # Work on copies to avoid mutating inputs
        main_df = main_df.copy()
        feed_dfs = {k: v.copy() for k, v in feed_dfs.items()}

        stats = MergeStats()
        merged_products = {}
        processed_codes = set()

        # Normalize codes to uppercase
        if "code" in main_df.columns:
            main_df["code"] = main_df["code"].astype(str).str.upper().str.strip()
        for source_name, feed_df in feed_dfs.items():
            if "code" in feed_df.columns:
                feed_df["code"] = feed_df["code"].astype(str).str.upper().str.strip()
            feed_dfs[source_name] = feed_df

        # Step 1: Process feed products (always included)
        for source_name, feed_df in feed_dfs.items():
            for _, feed_row in feed_df.iterrows():
                code = str(feed_row.get("code", "")).strip()
                if not code:
                    continue

                if code in merged_products:
                    # Already have this product — update with feed data
                    existing = merged_products[code]
                    if preserve_edits:
                        # Only update price and stock
                        for field in ["price", "stock", "availability"]:
                            if field in feed_row.index and pd.notna(feed_row[field]):
                                existing[field] = feed_row[field]
                    else:
                        # Full update, but preserve images if feed has fewer
                        feed_images = self._count_images(feed_row)
                        existing_images = self._count_images(pd.Series(existing))
                        if feed_images >= existing_images:
                            for col in feed_row.index:
                                if pd.notna(feed_row[col]):
                                    existing[col] = feed_row[col]
                        else:
                            for col in feed_row.index:
                                if col not in self.IMAGE_COLUMNS and pd.notna(feed_row[col]):
                                    existing[col] = feed_row[col]
                    existing["source"] = source_name
                    stats.updated += 1
                else:
                    # Check if exists in main data
                    main_match = main_df[main_df["code"] == code] if "code" in main_df.columns else pd.DataFrame()

                    if not main_match.empty:
                        # Merge feed into existing main data
                        base = main_match.iloc[0].to_dict()
                        if preserve_edits:
                            for field in ["price", "stock", "availability"]:
                                if field in feed_row.index and pd.notna(feed_row[field]):
                                    base[field] = feed_row[field]
                        else:
                            feed_images = self._count_images(feed_row)
                            main_images = self._count_images(main_match.iloc[0])
                            if feed_images >= main_images:
                                for col in feed_row.index:
                                    if pd.notna(feed_row[col]):
                                        base[col] = feed_row[col]
                            else:
                                for col in feed_row.index:
                                    if col not in self.IMAGE_COLUMNS and pd.notna(feed_row[col]):
                                        base[col] = feed_row[col]
                        base["source"] = source_name
                        merged_products[code] = base
                        stats.updated += 1
                    else:
                        # New product from feed
                        new_product = feed_row.to_dict()
                        new_product["source"] = source_name
                        merged_products[code] = new_product
                        stats.created += 1

                processed_codes.add(code)

        # Step 2: Process main data products
        for _, main_row in main_df.iterrows():
            code = str(main_row.get("code", "")).strip()
            if not code or code in processed_codes:
                continue

            category = str(main_row.get("defaultCategory", ""))
            if selected_categories and category not in selected_categories:
                continue

            merged_products[code] = main_row.to_dict()
            if "source" not in merged_products[code] or not merged_products[code]["source"]:
                merged_products[code]["source"] = "core"
            stats.kept += 1

        # Step 3: Handle discontinued products in preserve_edits mode
        if preserve_edits and feed_dfs:
            active_feed_codes = set()
            for feed_df in feed_dfs.values():
                if "code" in feed_df.columns:
                    active_feed_codes.update(feed_df["code"].tolist())

            codes_to_remove = []
            for code, product in merged_products.items():
                if product.get("source") not in ("core",) and code not in active_feed_codes:
                    codes_to_remove.append(code)

            for code in codes_to_remove:
                del merged_products[code]
                stats.removed += 1

        # Build result DataFrame
        if merged_products:
            result_df = pd.DataFrame(list(merged_products.values()))
        else:
            result_df = pd.DataFrame()

        return MergeResult(products=result_df, stats=stats)

    def _count_images(self, row: pd.Series) -> int:
        """Count non-empty image columns in a row."""
        count = 0
        for col in self.IMAGE_COLUMNS:
            if col in row.index:
                val = str(row[col]).strip()
                if val and val not in ("", "nan", "None"):
                    count += 1
        return count
