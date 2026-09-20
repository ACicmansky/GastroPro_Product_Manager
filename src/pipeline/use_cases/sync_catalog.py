"""Use case: Full product catalog synchronization across files, feeds, scrapers, AI, and DB."""

import logging
import time
from typing import Dict, Optional

import pandas as pd

from src.domain.categories.category_service import CategoryService
from src.domain.models import PipelineOptions, PipelineResult
from src.domain.ports.events import EventSinkPort, NullEventSink
from src.domain.ports.gateways import (
    AiEnricherPort,
    ExcelIOPort,
    FeedGatewayPort,
    ScraperGatewayPort,
)
from src.domain.ports.repositories import ProductRepositoryPort
from src.domain.ports.resolution import AutoSkipResolution, UserResolutionPort
from src.domain.pricing.pricing_service import PricingService
from src.domain.products.feed_specs import apply_feed_specs
from src.domain.products.merger import ProductMerger
from src.domain.transform.output_transformer import OutputTransformer

logger = logging.getLogger(__name__)


class DefaultFeedGateway:
    """Default adapter for XML feed fetching and parsing."""

    def fetch_and_parse(self, feed_name: str, url: str, config: dict) -> Optional[pd.DataFrame]:
        from src.data.parsers import fetch_and_parse

        return fetch_and_parse(feed_name, url, config)


class DefaultExcelIO:
    """Default adapter for Excel reading and writing."""

    def load_xlsx(self, file_path: str) -> pd.DataFrame:
        from src.data.excel import load_xlsx

        return load_xlsx(file_path)

    def write_xlsx(self, df: pd.DataFrame, file_path: str) -> None:
        from src.data.excel import write_xlsx

        write_xlsx(df, file_path)


class SyncCatalogUseCase:
    """Coordinates end-to-end catalog synchronization."""

    def __init__(
        self,
        product_repo: ProductRepositoryPort,
        merger: ProductMerger,
        category_service: CategoryService,
        transformer: OutputTransformer,
        pricing_service: PricingService,
        feed_gateway: Optional[FeedGatewayPort] = None,
        scraper_gateway: Optional[ScraperGatewayPort] = None,
        ai_enricher: Optional[AiEnricherPort] = None,
        excel_io: Optional[ExcelIOPort] = None,
        config: Optional[Dict] = None,
    ):
        self.repo = product_repo
        self.merger = merger
        self.category_service = category_service
        self.transformer = transformer
        self.pricing_service = pricing_service
        self.feed_gateway = feed_gateway or DefaultFeedGateway()
        self.scraper_gateway = scraper_gateway
        self.ai_enricher = ai_enricher
        self.excel_io = excel_io or DefaultExcelIO()
        self.config = config or {}

    def execute(
        self,
        options: PipelineOptions,
        event_sink: Optional[EventSinkPort] = None,
        user_resolution: Optional[UserResolutionPort] = None,
        ai_control=None,
    ) -> PipelineResult:
        """Execute the full catalog sync."""
        start_time = time.time()
        result = PipelineResult()
        events = event_sink or NullEventSink()
        resolver = user_resolution or AutoSkipResolution()

        logger.info("Starting SyncCatalogUseCase with options: %s", options)

        # 1. Load existing data from DB
        events.emit_stage("load")
        events.emit_progress("Loading existing data from database...")
        db_df = self.repo.get_all()

        # 2. Load main file
        main_df = pd.DataFrame()
        if options.main_file_path:
            events.emit_progress(f"Loading main data file: {options.main_file_path}")
            main_df = self.excel_io.load_xlsx(options.main_file_path)

        # If DB data exists but main file is empty, use DB as main
        if main_df.empty and not db_df.empty:
            main_df = db_df

        # Register live categories from input file and core DB products
        live_categories = set()
        if not db_df.empty and "defaultCategory" in db_df.columns:
            core_mask = (db_df["source"] == "core") if "source" in db_df.columns else slice(None)
            live_categories.update(
                str(c).strip()
                for c in db_df.loc[core_mask, "defaultCategory"].dropna().unique()
                if str(c).strip() and str(c).strip().lower() != "nan"
            )
        if not main_df.empty and "defaultCategory" in main_df.columns:
            live_categories.update(
                str(c).strip()
                for c in main_df["defaultCategory"].dropna().unique()
                if str(c).strip() and str(c).strip().lower() != "nan"
            )
        if live_categories:
            self.category_service.set_file_categories(live_categories)
        self.category_service.set_force_file_categories(options.force_file_categories)

        # 3. Parse XML feeds
        events.emit_stage("feeds")
        feed_dfs = {}
        xml_feeds = self.config.get("xml_feeds", {})
        for feed_name, feed_config in xml_feeds.items():
            url = feed_config.get("url", "")
            if not url:
                continue
            if options.enabled_feeds is not None and feed_name not in options.enabled_feeds:
                continue
            events.emit_progress(f"Parsing XML feed: {feed_name}")
            feed_df = self.feed_gateway.fetch_and_parse(feed_name, url, self.config)
            if feed_df is not None and not feed_df.empty:
                feed_dfs[feed_name] = feed_df
                events.emit_progress(f"Feed '{feed_name}': {len(feed_df)} products")
            else:
                warning = (
                    f"Feed '{feed_name}' nevrátil žiadne produkty (chyba sťahovania?). "
                    f"Produkty z tohto zdroja zostanú nezmenené."
                )
                result.warnings.append(warning)
                events.emit_progress(f"VAROVANIE: {warning}")

        # 4. Scrape (if enabled)
        if options.enable_scraping and self.scraper_gateway:
            events.emit_stage("scrape")
            events.emit_progress("Starting web scraping...")
            scraped = self.scraper_gateway.scrape(
                scrape_mebella=options.scrape_mebella,
                scrape_topchladenie=options.scrape_topchladenie,
                topchladenie_csv_path=options.topchladenie_csv_path,
                progress_callback=events.emit_progress,
            )
            feed_dfs.update(scraped)

            # Mebella table bases carry no price — map with price resolution
            if options.enable_price_mapping and "mebella" in feed_dfs:
                feed_dfs["mebella"] = self._map_prices(feed_dfs["mebella"], events, resolver)

        # 5. Merge all sources
        events.emit_stage("merge")
        events.emit_progress("Merging product data...")
        merge_result = self.merger.merge(
            main_df=main_df,
            feed_dfs=feed_dfs,
            selected_categories=options.selected_categories or None,
            preserve_edits=options.preserve_client_edits,
        )
        merged_df = merge_result.products
        result.merge_stats = merge_result.stats
        stats = merge_result.stats
        events.emit_progress(
            f"Merge: created={stats.created} updated={stats.updated} "
            f"kept={stats.kept} removed={stats.removed} -> {len(merged_df)} products"
        )

        # 6. Map categories
        events.emit_stage("categories")
        events.emit_progress("Mapping categories...")
        self.category_service.set_interactive_callback(resolver.resolve_category)
        for idx, row in merged_df.iterrows():
            old_cat = str(row.get("defaultCategory", ""))
            if old_cat:
                new_cat = self.category_service.map_or_ask(
                    old_cat,
                    str(row.get("name", "")),
                )
                merged_df.at[idx, "defaultCategory"] = new_cat
                merged_df.at[idx, "categoryText"] = new_cat

        # 8. AI enhancement
        if options.enable_ai_enhancement and self.ai_enricher:
            events.emit_stage("ai")
            events.emit_progress("Starting AI enhancement...")
            enrichment = self.ai_enricher.enrich(
                merged_df,
                force_reprocess=options.force_ai_reprocess,
                progress_callback=lambda *args: events.emit_ai_progress(
                    args[0] if len(args) > 2 else 0,
                    args[1] if len(args) > 2 else 0,
                    args[-1] if args else "AI processing...",
                ),
                control=ai_control,
                on_chunk_applied=self.repo.upsert,
            )
            merged_df = enrichment.products
            result.enrichment_stats = enrichment

        # 8b. Structured feed specs override AI-extracted dims/weight
        merged_df = apply_feed_specs(merged_df)

        # 9. Transform to output format
        events.emit_stage("export")
        events.emit_progress("Transforming to output format...")
        output_df = self.transformer.transform(merged_df)

        # 10. Save to DB
        events.emit_progress("Saving to database...")
        self.repo.backup()
        self.repo.upsert(merged_df)

        # 11. Write output file
        if options.output_path:
            events.emit_progress(f"Writing output to: {options.output_path}")
            self.excel_io.write_xlsx(output_df, options.output_path)
            result.output_path = options.output_path

        result.product_count = len(output_df)
        result.duration_seconds = time.time() - start_time
        events.emit_progress(
            f"Pipeline complete. {result.product_count} products processed in {result.duration_seconds:.1f}s"
        )
        return result

    def _map_prices(
        self,
        df: pd.DataFrame,
        events: EventSinkPort,
        resolver: UserResolutionPort,
    ) -> pd.DataFrame:
        """Fill prices from known mappings; ask per product for unknown ones."""
        events.emit_progress("Applying price mappings...")
        df = self.pricing_service.apply_mappings(df)

        unmapped = [
            idx
            for idx, row in df.iterrows()
            if str(row.get("code", "")).strip() and str(row.get("price", "")).strip() in ("", "0", "nan", "None")
        ]
        for done, idx in enumerate(unmapped):
            row = df.loc[idx]
            code = str(row.get("code", "")).strip()
            remaining = len(unmapped) - done
            events.emit_progress(f"Cena nenájdená pre: {code}, vyžaduje sa vstup (ostáva {remaining})...")
            product_data = {
                "code": code,
                "width": row.get("width"),
                "depth": row.get("depth"),
                "height": row.get("height"),
                "image_url": row.get("image"),
                "remaining_count": remaining,
            }
            new_price = resolver.resolve_price(product_data, self.pricing_service.as_dataframe())
            if new_price:
                df.at[idx, "price"] = new_price
                dimension = f"{row.get('width')}x{row.get('depth')}x{row.get('height')}"
                self.pricing_service.add_mapping(code, new_price, dimension)
                events.emit_progress(f"Nová cena uložená pre: {code}")
        return df
