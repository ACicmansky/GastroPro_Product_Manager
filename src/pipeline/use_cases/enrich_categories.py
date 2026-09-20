"""Use case: Scoped AI enhancement for specific product categories."""

import logging
import time
from typing import List, Optional

from src.domain.models import PipelineResult
from src.domain.ports.events import EventSinkPort, NullEventSink
from src.domain.ports.gateways import AiEnricherPort
from src.domain.ports.repositories import ProductRepositoryPort

logger = logging.getLogger(__name__)


class EnrichCategoriesUseCase:
    """Executes AI enhancement scoped only to products of specified categories."""

    def __init__(
        self,
        product_repo: ProductRepositoryPort,
        ai_enricher: AiEnricherPort,
    ):
        self.repo = product_repo
        self.ai_enricher = ai_enricher

    def execute(
        self,
        categories: List[str],
        event_sink: Optional[EventSinkPort] = None,
        ai_control=None,
    ) -> PipelineResult:
        """Execute scoped category enrichment."""
        if self.ai_enricher.get_resumable_run():
            raise RuntimeError("Najprv dokončite alebo zrušte prerušené AI spracovanie.")

        start_time = time.time()
        result = PipelineResult()
        events = event_sink or NullEventSink()

        events.emit_progress(f"Loading products for categories ({len(categories)}) from database...")
        df = self.repo.get_all()

        enrichment = self.ai_enricher.enrich(
            df,
            only_categories=set(categories),
            progress_callback=lambda *args: events.emit_ai_progress(
                args[0] if len(args) > 2 else 0,
                args[1] if len(args) > 2 else 0,
                args[-1] if args else "AI processing...",
            ),
            control=ai_control,
            on_chunk_applied=self.repo.upsert,
        )
        result.enrichment_stats = enrichment
        result.product_count = len(enrichment.products)
        result.duration_seconds = time.time() - start_time
        events.emit_progress(
            f"AI pre kategórie hotové. {enrichment.processed} produktov spracovaných v {result.duration_seconds:.1f}s"
        )
        return result
