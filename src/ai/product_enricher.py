"""High-level AI product enrichment coordinator."""

import logging
from typing import Dict, Optional, Callable, Tuple

import pandas as pd

from .api_client import GeminiClient
from .batch_orchestrator import BatchOrchestrator
from .result_parser import ResultParser
from src.domain.models import EnrichmentResult
from src.domain.products.variant_service import get_pair_code
from src.data.database.batch_job_db import BatchJobDB

logger = logging.getLogger(__name__)


class ProductEnricher:
    """Coordinates AI enhancement of product data."""

    def __init__(self, config: Dict, batch_job_db: Optional[BatchJobDB] = None):
        self.client = GeminiClient(config)
        self.parser = ResultParser(
            similarity_threshold=config.get("ai_enhancement", {}).get("similarity_threshold", 85)
        )
        self.orchestrator = BatchOrchestrator(
            client=self.client,
            result_parser=self.parser,
            batch_job_db=batch_job_db,
            config=config,
        )

    def enrich(
        self,
        df: pd.DataFrame,
        force_reprocess: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> EnrichmentResult:
        """Enrich product DataFrame with AI-generated content.

        Args:
            df: Product DataFrame
            force_reprocess: If True, reprocess already-processed products
            progress_callback: Optional progress callback

        Returns:
            EnrichmentResult with updated DataFrame and stats
        """
        if not self.client.is_available:
            logger.warning("AI client not available, skipping enhancement")
            return EnrichmentResult(products=df)

        # Identify variant products (Group 1)
        group1_indices = set()
        if "pairCode" in df.columns:
            all_pair_codes = set(df["pairCode"].dropna().unique())
            all_pair_codes.discard("")

            # Products needing processing
            ai_processed = df.get("aiProcessed", pd.Series([""] * len(df), index=df.index))
            needs = df if force_reprocess else df[ai_processed != "1"]
            for idx, row in needs.iterrows():
                code = str(row.get("code", "")).strip()
                pair_code = str(row.get("pairCode", "")).strip()
                if pair_code or (code and code in all_pair_codes):
                    group1_indices.add(idx)

        # Run batch processing
        updated_df, stats = self.orchestrator.process(
            df,
            group1_indices=group1_indices,
            progress_callback=progress_callback,
            force_reprocess=force_reprocess,
        )

        return EnrichmentResult(
            products=updated_df,
            processed=stats.get("ai_processed", 0),
            skipped=0,
            failed=stats.get("ai_should_process", 0) - stats.get("ai_processed", 0),
        )
