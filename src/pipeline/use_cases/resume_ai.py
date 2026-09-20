"""Use case: Resume an interrupted AI enhancement run."""

import logging
import time
from typing import Optional

from src.domain.models import PipelineResult
from src.domain.ports.events import EventSinkPort, NullEventSink
from src.domain.ports.gateways import AiEnricherPort
from src.domain.ports.repositories import ProductRepositoryPort

logger = logging.getLogger(__name__)


class ResumeAiUseCase:
    """Resumes an interrupted or paused AI enhancement run from database state."""

    def __init__(
        self,
        product_repo: ProductRepositoryPort,
        ai_enricher: AiEnricherPort,
    ):
        self.repo = product_repo
        self.ai_enricher = ai_enricher

    def execute(
        self,
        event_sink: Optional[EventSinkPort] = None,
        ai_control=None,
    ) -> PipelineResult:
        """Execute the AI resume process."""
        start_time = time.time()
        result = PipelineResult()
        events = event_sink or NullEventSink()

        events.emit_progress("Loading current catalog from database for AI resume...")
        df = self.repo.get_all()

        enrichment = self.ai_enricher.resume(
            df,
            progress_callback=lambda *args: events.emit_ai_progress(
                args[0] if len(args) > 2 else 0,
                args[1] if len(args) > 2 else 0,
                args[-1] if args else "AI resume...",
            ),
            control=ai_control,
            on_chunk_applied=self.repo.upsert,
        )
        result.enrichment_stats = enrichment
        result.product_count = len(enrichment.products)
        result.duration_seconds = time.time() - start_time
        events.emit_progress(
            f"AI resume complete. {enrichment.processed} produktov spracovanych v {result.duration_seconds:.1f}s"
        )
        return result
