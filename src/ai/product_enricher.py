"""High-level AI product enrichment coordinator."""

import logging
from typing import Dict, Optional, Callable, Tuple

import pandas as pd

from .api_client import GeminiClient
from .batch_orchestrator import BatchOrchestrator
from .prompts import load_category_parameters
from .result_parser import ResultParser
from .run_control import RunControl
from src.domain.models import EnrichmentResult
from src.domain.products.variant_service import get_pair_code
from src.data.database.batch_job_db import BatchJobDB
from src.data.database.run_db import RunDB

logger = logging.getLogger(__name__)


class ProductEnricher:
    """Coordinates AI enhancement of product data."""

    def __init__(self, config: Dict, batch_job_db: Optional[BatchJobDB] = None):
        self.client = GeminiClient(config)
        category_params = load_category_parameters()
        self.parser = ResultParser(
            similarity_threshold=config.get("ai_enhancement", {}).get("similarity_threshold", 85),
            allowed_params={f for filters in category_params.values() for f in filters},
        )
        self.run_db = RunDB(batch_job_db.db_path) if batch_job_db else None
        self.orchestrator = BatchOrchestrator(
            client=self.client,
            result_parser=self.parser,
            batch_job_db=batch_job_db,
            run_db=self.run_db,
            config=config,
        )

    @staticmethod
    def _group1_indices(df: pd.DataFrame) -> set:
        """Variant products (paired by pairCode) get the dimension-free prompt."""
        group1_indices = set()
        if "pairCode" in df.columns:
            all_pair_codes = set(df["pairCode"].dropna().unique())
            all_pair_codes.discard("")
            for idx, row in df.iterrows():
                code = str(row.get("code", "")).strip()
                pair_code = str(row.get("pairCode", "")).strip()
                if pair_code or (code and code in all_pair_codes):
                    group1_indices.add(idx)
        return group1_indices

    def get_resumable_run(self) -> Optional[dict]:
        """Latest run in running/paused/interrupted state, or None."""
        return self.run_db.get_resumable_run() if self.run_db else None

    def enrich(
        self,
        df: pd.DataFrame,
        force_reprocess: bool = False,
        progress_callback: Optional[Callable] = None,
        control: Optional[RunControl] = None,
        on_chunk_applied: Optional[Callable] = None,
    ) -> EnrichmentResult:
        """Enrich product DataFrame with AI-generated content.

        Args:
            df: Product DataFrame
            force_reprocess: If True, reprocess already-processed products
            progress_callback: Optional progress callback
            control: Optional RunControl for pause/cancel
            on_chunk_applied: Optional callback(rows_df) fired after each chunk is applied

        Returns:
            EnrichmentResult with updated DataFrame and stats
        """
        if not self.client.is_available:
            logger.warning("AI client not available, skipping enhancement")
            return EnrichmentResult(products=df)

        group1_indices = self._group1_indices(df)
        updated_df, stats = self.orchestrator.process(
            df,
            group1_indices=group1_indices,
            progress_callback=progress_callback,
            force_reprocess=force_reprocess,
            control=control,
            on_chunk_applied=on_chunk_applied,
        )

        return EnrichmentResult(
            products=updated_df,
            processed=stats.get("ai_processed", 0),
            failed=stats.get("ai_should_process", 0) - stats.get("ai_processed", 0),
        )

    def resume(
        self,
        df: pd.DataFrame,
        progress_callback: Optional[Callable] = None,
        control: Optional[RunControl] = None,
        on_chunk_applied: Optional[Callable] = None,
    ) -> EnrichmentResult:
        """Continue the latest resumable run (paused/interrupted). No-op if none exists."""
        if not self.run_db:
            raise RuntimeError("ProductEnricher has no run tracking database configured")
        resumable = self.run_db.get_resumable_run()
        if not resumable:
            return EnrichmentResult(products=df)

        group1_indices = self._group1_indices(df)
        updated_df, stats = self.orchestrator.resume(
            df, resumable["id"], group1_indices,
            progress_callback=progress_callback, control=control, on_chunk_applied=on_chunk_applied,
        )
        return EnrichmentResult(
            products=updated_df,
            processed=stats.get("ai_processed", 0),
            failed=stats.get("ai_should_process", 0) - stats.get("ai_processed", 0),
        )

    def fill_missing_params(
        self,
        df: pd.DataFrame,
        progress_callback: Optional[Callable] = None,
        model: Optional[str] = None,
    ) -> EnrichmentResult:
        """Second pass: web-grounded re-ask for filter params still missing.

        `model` escalates the pass to a stronger model (tiered enhancement).
        """
        if not self.client.is_available:
            logger.warning("AI client not available, skipping missing-params pass")
            return EnrichmentResult(products=df)

        updated_df, stats = self.orchestrator.process_missing_params(
            df, progress_callback=progress_callback, model=model
        )
        return EnrichmentResult(
            products=updated_df,
            processed=stats.get("ai_processed", 0),
            failed=stats.get("ai_should_process", 0) - stats.get("ai_processed", 0),
        )
