"""Main pipeline facade and composition root for Hexagonal Architecture."""

import logging
from typing import Callable, Dict, Optional

import pandas as pd

from src.ai.product_enricher import ProductEnricher
from src.data.database.product_db import ProductDB
from src.data.database.run_db import RunDB
from src.data.excel import load_xlsx, write_xlsx
from src.data.parsers import parse as parse_xml_feed
from src.domain.categories.category_service import CategoryService
from src.domain.models import PipelineOptions, PipelineResult
from src.domain.ports.events import CallbackEventSink, EventSinkPort
from src.domain.ports.gateways import (
    AiEnricherPort,
    ExcelIOPort,
    FeedGatewayPort,
    ScraperGatewayPort,
)
from src.domain.ports.repositories import ProductRepositoryPort, RunRepositoryPort
from src.domain.ports.resolution import CallbackResolution, UserResolutionPort
from src.domain.pricing.pricing_service import PricingService
from src.domain.products.merger import ProductMerger
from src.domain.transform.output_transformer import OutputTransformer
from src.pipeline.scraping import ScrapingOrchestrator
from src.pipeline.use_cases import (
    EnrichCategoriesUseCase,
    ExportCatalogUseCase,
    ResumeAiUseCase,
    SyncCatalogUseCase,
)

logger = logging.getLogger(__name__)


class Pipeline:
    """Facade and composition root coordinating application use cases and driven ports.

    Acts as the primary entry point while delegating execution to focused use cases:
    - SyncCatalogUseCase: Full linear catalog ingestion & synchronization.
    - ExportCatalogUseCase: Direct SQLite database to 138-column Excel export.
    - ResumeAiUseCase: Resuming paused/interrupted AI enhancement runs.
    - EnrichCategoriesUseCase: Category-scoped AI parameter re-runs.
    """

    def __init__(
        self,
        config: Dict,
        product_repo: Optional[ProductRepositoryPort] = None,
        run_repo: Optional[RunRepositoryPort] = None,
        merger: Optional[ProductMerger] = None,
        category_service: Optional[CategoryService] = None,
        transformer: Optional[OutputTransformer] = None,
        enricher: Optional[AiEnricherPort] = None,
        pricing_service: Optional[PricingService] = None,
        scraping: Optional[ScraperGatewayPort] = None,
        feed_gateway: Optional[FeedGatewayPort] = None,
        excel_io: Optional[ExcelIOPort] = None,
    ):
        self.config = config
        db_path = config.get("db_path", "data/products.db")

        # Injected or default concrete adapters
        self.db = product_repo or ProductDB(db_path)
        self.run_db = run_repo or RunDB(db_path)
        self.merger = merger or ProductMerger()
        self.category_service = category_service or CategoryService()
        self.transformer = transformer or OutputTransformer(config)
        self.pricing_service = pricing_service or PricingService()
        self.enricher = enricher or ProductEnricher(config, run_db=self.run_db)
        self.scraping = scraping or ScrapingOrchestrator(config)
        self.feed_gateway = feed_gateway
        self.excel_io = excel_io

        # Initialize Use Cases
        self.sync_use_case = SyncCatalogUseCase(
            product_repo=self.db,
            merger=self.merger,
            category_service=self.category_service,
            transformer=self.transformer,
            pricing_service=self.pricing_service,
            feed_gateway=self.feed_gateway,
            scraper_gateway=self.scraping,
            ai_enricher=self.enricher,
            excel_io=self.excel_io,
            config=self.config,
        )

        self.export_use_case = ExportCatalogUseCase(
            product_repo=self.db,
            transformer=self.transformer,
            excel_io=self.excel_io,
        )

        self.resume_ai_use_case = ResumeAiUseCase(
            product_repo=self.db,
            ai_enricher=self.enricher,
        )

        self.enrich_categories_use_case = EnrichCategoriesUseCase(
            product_repo=self.db,
            ai_enricher=self.enricher,
        )

    def run(
        self,
        options: PipelineOptions,
        on_progress: Optional[Callable] = None,
        on_unknown_category: Optional[Callable] = None,
        on_unmapped_price: Optional[Callable] = None,
        ai_control=None,
        on_stage: Optional[Callable] = None,
        on_ai_progress: Optional[Callable] = None,
        event_sink: Optional[EventSinkPort] = None,
        user_resolution: Optional[UserResolutionPort] = None,
    ) -> PipelineResult:
        """Execute the full pipeline via SyncCatalogUseCase."""
        events = event_sink or CallbackEventSink(
            on_progress=on_progress,
            on_stage=on_stage,
            on_ai_progress=on_ai_progress,
        )
        resolver = user_resolution or CallbackResolution(
            on_category=on_unknown_category,
            on_price=on_unmapped_price,
        )

        return self.sync_use_case.execute(
            options=options,
            event_sink=events,
            user_resolution=resolver,
            ai_control=ai_control,
        )

    def get_resumable_ai_run(self) -> Optional[dict]:
        """Latest paused/interrupted AI run, or None."""
        return self.enricher.get_resumable_run()

    def run_ai_resume(
        self,
        on_progress: Optional[Callable] = None,
        ai_control=None,
        on_ai_progress: Optional[Callable] = None,
        event_sink: Optional[EventSinkPort] = None,
    ) -> PipelineResult:
        """Continue an interrupted AI run against current DB data."""
        events = event_sink or CallbackEventSink(
            on_progress=on_progress,
            on_ai_progress=on_ai_progress,
        )
        return self.resume_ai_use_case.execute(
            event_sink=events,
            ai_control=ai_control,
        )

    def run_ai_for_categories(
        self,
        categories: list,
        on_progress: Optional[Callable] = None,
        ai_control=None,
        on_ai_progress: Optional[Callable] = None,
        event_sink: Optional[EventSinkPort] = None,
    ) -> PipelineResult:
        """Re-run AI enhancement for products of the given categories only."""
        events = event_sink or CallbackEventSink(
            on_progress=on_progress,
            on_ai_progress=on_ai_progress,
        )
        return self.enrich_categories_use_case.execute(
            categories=categories,
            event_sink=events,
            ai_control=ai_control,
        )

    def export_from_db(
        self,
        output_path: str,
        selected_categories: Optional[list] = None,
        on_progress: Optional[Callable] = None,
        event_sink: Optional[EventSinkPort] = None,
    ) -> PipelineResult:
        """Export current products from database directly to the final Excel format."""
        events = event_sink or CallbackEventSink(on_progress=on_progress)
        return self.export_use_case.execute(
            output_path=output_path,
            selected_categories=selected_categories,
            event_sink=events,
        )

    # --- Step convenience methods for tests & script backward-compatibility ---

    def load_main_data(self, file_path: str) -> pd.DataFrame:
        """Load main data file. Convenience method."""
        return load_xlsx(file_path)

    def parse_xml(self, feed_name: str, xml_content: str) -> pd.DataFrame:
        """Parse an XML feed. Convenience method for testing."""
        result = parse_xml_feed(feed_name, xml_content, self.config)
        return result if result is not None else pd.DataFrame()

    def map_categories(self, df: pd.DataFrame, ask_interactive: bool = False) -> pd.DataFrame:
        """Map category fields in-place. Convenience method for testing."""
        df = df.copy()
        for idx, row in df.iterrows():
            old_cat = str(row.get("defaultCategory", ""))
            if old_cat:
                new_cat = self.category_service.map(old_cat)
                df.at[idx, "defaultCategory"] = new_cat
                df.at[idx, "categoryText"] = new_cat
        return df

    def apply_transformation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply output format transformation. Convenience method."""
        return self.transformer.transform(df)

    def save_output(self, df: pd.DataFrame, file_path: str) -> None:
        """Save DataFrame to xlsx. Convenience method."""
        write_xlsx(df, file_path)
