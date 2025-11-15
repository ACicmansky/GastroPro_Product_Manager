"""
AI Enhancer for new 138-column format.
Enhances product descriptions using AI while tracking processing status.
"""

import pandas as pd
from typing import Dict, Tuple
from datetime import datetime


class AIEnhancerNewFormat:
    """AI enhancer for new format with aiProcessed tracking."""

    def __init__(self, config: Dict):
        """
        Initialize AI enhancer with configuration.

        Args:
            config: Configuration dictionary from config.json
        """
        self.config = config
        self.ai_config = config.get("ai_enhancement", {})
        self.api_key = self.ai_config.get("api_key", "")

    def enhance_product(
        self,
        product: pd.Series,
        preserve_existing: bool = True,
        force_reprocess: bool = False,
    ) -> pd.Series:
        """
        Enhance a single product with AI-generated content.

        Args:
            product: Product data as Series
            preserve_existing: If True, skip if descriptions already exist
            force_reprocess: If True, process even if already marked as processed

        Returns:
            Enhanced product Series
        """
        result = product.copy()

        # Skip if already processed (unless force_reprocess)
        if not force_reprocess and str(result.get("aiProcessed", "")) == "1":
            return result

        # Skip if descriptions exist and preserve_existing is True
        if preserve_existing:
            has_short = str(result.get("shortDescription", "")) not in [
                "",
                "nan",
                "None",
            ]
            has_full = str(result.get("description", "")) not in ["", "nan", "None"]
            if has_short and has_full:
                return result

        # Call AI API to enhance
        enhancements = self._call_ai_api(result)

        # Apply enhancements
        for field, value in enhancements.items():
            result[field] = value

        # Mark as processed
        result["aiProcessed"] = "1"
        result["aiProcessedDate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return result

    def enhance_dataframe(
        self, df: pd.DataFrame, force_reprocess: bool = False
    ) -> pd.DataFrame:
        """
        Enhance entire DataFrame with AI.

        Args:
            df: DataFrame to enhance
            force_reprocess: If True, reprocess even if already processed

        Returns:
            Enhanced DataFrame
        """
        print("\n" + "=" * 60)
        print("AI ENHANCEMENT")
        print("=" * 60)

        result_df = df.copy()

        # Ensure tracking columns exist
        if "aiProcessed" not in result_df.columns:
            result_df["aiProcessed"] = ""
        if "aiProcessedDate" not in result_df.columns:
            result_df["aiProcessedDate"] = ""

        processed_count = 0
        skipped_count = 0

        for idx, row in result_df.iterrows():
            # Skip if already processed (unless force_reprocess)
            if not force_reprocess and str(row.get("aiProcessed", "")) == "1":
                skipped_count += 1
                continue

            # Enhance product
            enhanced = self.enhance_product(
                row,
                preserve_existing=not force_reprocess,
                force_reprocess=force_reprocess,
            )

            # Update DataFrame
            for col in enhanced.index:
                result_df.at[idx, col] = enhanced[col]

            processed_count += 1

            if processed_count % 10 == 0:
                print(f"  Processed {processed_count} products...")

        print(f"\nAI Enhancement complete:")
        print(f"  Processed: {processed_count}")
        print(f"  Skipped: {skipped_count}")
        print("=" * 60)

        return result_df

    def enhance_dataframe_with_stats(
        self, df: pd.DataFrame, force_reprocess: bool = False
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Enhance DataFrame and return statistics.

        Args:
            df: DataFrame to enhance
            force_reprocess: If True, reprocess even if already processed

        Returns:
            Tuple of (enhanced DataFrame, statistics dict)
        """
        # Count already processed
        already_processed = 0
        if "aiProcessed" in df.columns:
            already_processed = (df["aiProcessed"] == "1").sum()

        # Enhance
        result_df = self.enhance_dataframe(df, force_reprocess)

        # Calculate statistics
        total_processed = (result_df["aiProcessed"] == "1").sum()
        newly_processed = total_processed - (
            0 if force_reprocess else already_processed
        )

        stats = {
            "total_processed": int(total_processed),
            "already_processed": int(already_processed),
            "newly_processed": int(newly_processed),
            "api_calls": int(newly_processed),
        }

        return result_df, stats

    def _call_ai_api(self, product: pd.Series) -> Dict:
        """
        Call AI API to generate enhancements.

        This is a placeholder for actual API integration.
        In production, this would call OpenAI, Anthropic, or similar.

        Args:
            product: Product data

        Returns:
            Dictionary of field -> enhanced value
        """
        # Check if API key is available
        if not self.api_key:
            print("  Warning: No API key configured, skipping AI enhancement")
            return {}

        # Placeholder implementation
        # In production, this would make actual API calls
        enhancements = {}

        # Generate short description if missing
        if str(product.get("shortDescription", "")) in ["", "nan", "None"]:
            name = str(product.get("name", ""))
            manufacturer = str(product.get("manufacturer", ""))
            if name:
                enhancements["shortDescription"] = (
                    f"{name} - Professional quality product"
                )
                if manufacturer and manufacturer not in ["", "nan", "None"]:
                    enhancements["shortDescription"] += f" by {manufacturer}"

        # Generate full description if missing
        if str(product.get("description", "")) in ["", "nan", "None"]:
            name = str(product.get("name", ""))
            if name:
                enhancements["description"] = (
                    f"Detailed description for {name}. High-quality professional equipment suitable for commercial use."
                )

        return enhancements
