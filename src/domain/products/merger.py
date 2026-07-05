"""Product data merging from multiple sources."""

import logging
from typing import Dict, List, Optional, Set

import pandas as pd

from src.domain.models import MergeResult, MergeStats

logger = logging.getLogger(__name__)


class ProductMerger:
    """Merges product data from main file and XML feed sources."""

    # Image columns in priority order (first is the primary image)
    IMAGE_COLUMNS = ["image"] + [f"image{i}" for i in range(2, 11)]

    # Fields that are never overridden by feed data when they exist in main.
    # These are AI-enhanced, manually edited, or tracking fields.
    PRESERVED_FIELDS = {"name", "shortDescription", "longDescription", "description",
                        "aiProcessed", "AI_Processed_Date", "Spracovane AI"}

    # Category fields — only updated when update_categories=True
    CATEGORY_FIELDS = {"defaultCategory", "categoryText"}

    def merge(
        self,
        main_df: pd.DataFrame,
        feed_dfs: Dict[str, pd.DataFrame],
        selected_categories: Optional[List[str]] = None,
        preserve_edits: bool = False,
        update_categories: bool = False,
    ) -> MergeResult:
        """Merge main data with feed data.

        Args:
            main_df: Main product DataFrame
            feed_dfs: Dict of source_name -> DataFrame from feeds
            selected_categories: Categories to include from main (None = all)
            preserve_edits: If True, only update price/stock from feeds and
                            remove products no longer present in feeds
            update_categories: If True, allow feed data to update category fields

        Returns:
            MergeResult with merged products and statistics
        """
        # Work on copies to avoid mutating inputs
        main_df = main_df.copy()
        feed_dfs = {k: v.copy() for k, v in feed_dfs.items()}
        self._normalize_codes(main_df, feed_dfs)

        skip_fields = set(self.PRESERVED_FIELDS)
        if not update_categories:
            skip_fields |= self.CATEGORY_FIELDS

        stats = MergeStats()
        merged_products: Dict[str, dict] = {}

        processed_codes = self._merge_feed_products(
            main_df, feed_dfs, merged_products, stats, preserve_edits, skip_fields
        )
        self._keep_main_products(
            main_df, merged_products, processed_codes, selected_categories, stats
        )
        if preserve_edits and feed_dfs:
            self._remove_discontinued(feed_dfs, merged_products, stats)

        result_df = (
            pd.DataFrame(list(merged_products.values()))
            if merged_products
            else pd.DataFrame()
        )
        return MergeResult(products=result_df, stats=stats)

    def _normalize_codes(self, main_df: pd.DataFrame, feed_dfs: Dict[str, pd.DataFrame]):
        """Normalize product codes to uppercase in place."""
        if "code" in main_df.columns:
            main_df["code"] = main_df["code"].astype(str).str.upper().str.strip()
        for feed_df in feed_dfs.values():
            if "code" in feed_df.columns:
                feed_df["code"] = feed_df["code"].astype(str).str.upper().str.strip()

    def _merge_feed_products(
        self,
        main_df: pd.DataFrame,
        feed_dfs: Dict[str, pd.DataFrame],
        merged_products: Dict[str, dict],
        stats: MergeStats,
        preserve_edits: bool,
        skip_fields: Set[str],
    ) -> Set[str]:
        """Step 1: feed products are always included and update existing data."""
        processed_codes: Set[str] = set()
        for source_name, feed_df in feed_dfs.items():
            for _, feed_row in feed_df.iterrows():
                code = str(feed_row.get("code", "")).strip()
                if not code:
                    continue

                if code in merged_products:
                    # Already merged from an earlier feed — update it
                    target = merged_products[code]
                    self._update_from_feed(target, feed_row, preserve_edits, skip_fields)
                    target["source"] = source_name
                    stats.updated += 1
                else:
                    main_match = (
                        main_df[main_df["code"] == code]
                        if "code" in main_df.columns
                        else pd.DataFrame()
                    )
                    if not main_match.empty:
                        # Merge feed into existing main data
                        base = main_match.iloc[0].to_dict()
                        self._update_from_feed(base, feed_row, preserve_edits, skip_fields)
                        base["source"] = source_name
                        merged_products[code] = base
                        stats.updated += 1
                    else:
                        # New product from feed
                        new_product = feed_row.to_dict()
                        new_product["source"] = source_name
                        # New products start with aiProcessed = "0"
                        if not new_product.get("aiProcessed"):
                            new_product["aiProcessed"] = "0"
                        merged_products[code] = new_product
                        stats.created += 1

                processed_codes.add(code)
        return processed_codes

    def _update_from_feed(
        self,
        target: dict,
        feed_row: pd.Series,
        preserve_edits: bool,
        skip_fields: Set[str],
    ):
        """Copy feed values into target, honoring edit preservation and image priority."""
        if preserve_edits:
            for field in ("price", "stock", "availability"):
                if field in feed_row.index and pd.notna(feed_row[field]):
                    target[field] = feed_row[field]
            return

        # Image merge prioritizes the source with more images
        keep_existing_images = (
            self._count_images(feed_row) < self._count_images(pd.Series(target))
        )
        for col in feed_row.index:
            if col in skip_fields or pd.isna(feed_row[col]):
                continue
            if keep_existing_images and col in self.IMAGE_COLUMNS:
                continue
            target[col] = feed_row[col]

    def _keep_main_products(
        self,
        main_df: pd.DataFrame,
        merged_products: Dict[str, dict],
        processed_codes: Set[str],
        selected_categories: Optional[List[str]],
        stats: MergeStats,
    ):
        """Step 2: keep main data products not present in any feed."""
        for _, main_row in main_df.iterrows():
            code = str(main_row.get("code", "")).strip()
            if not code or code in processed_codes:
                continue

            category = str(main_row.get("defaultCategory", ""))
            if selected_categories and category not in selected_categories:
                stats.removed += 1
                continue

            merged_products[code] = main_row.to_dict()
            if not merged_products[code].get("source"):
                merged_products[code]["source"] = "core"
            stats.kept += 1

    def _remove_discontinued(
        self,
        feed_dfs: Dict[str, pd.DataFrame],
        merged_products: Dict[str, dict],
        stats: MergeStats,
    ):
        """Step 3 (preserve_edits): drop feed-sourced products gone from all feeds."""
        active_feed_codes: Set[str] = set()
        for feed_df in feed_dfs.values():
            if "code" in feed_df.columns:
                active_feed_codes.update(feed_df["code"].tolist())

        codes_to_remove = [
            code
            for code, product in merged_products.items()
            if product.get("source") not in ("core",) and code not in active_feed_codes
        ]
        for code in codes_to_remove:
            del merged_products[code]
            stats.removed += 1

    def _count_images(self, row: pd.Series) -> int:
        """Count non-empty image columns in a row."""
        count = 0
        for col in self.IMAGE_COLUMNS:
            if col in row.index:
                val = str(row[col]).strip()
                if val and val not in ("", "nan", "None"):
                    count += 1
        return count
