"""Main pipeline — coordinates the entire data flow."""

import logging
import time
from typing import Callable, Dict, Optional

import pandas as pd

from src.domain.models import PipelineOptions, PipelineResult, MergeStats
from src.domain.products.merger import ProductMerger
from src.domain.categories.category_service import CategoryService
from src.domain.categories.category_filter import CategoryFilter
from src.domain.pricing.pricing_service import PricingService
from src.domain.transform.output_transformer import OutputTransformer
from src.data.database.product_db import ProductDB
from src.data.database.batch_job_db import BatchJobDB
from src.data.loaders.loader_factory import DataLoaderFactory
from src.data.parsers.xml_parser_factory import XMLParserFactory
from src.data.writers.xlsx_writer import write_xlsx
from src.ai.product_enricher import ProductEnricher
from .scraping import ScrapingOrchestrator

logger = logging.getLogger(__name__)


class Pipeline:
    """Orchestrates the complete product data processing pipeline.

    Linear flow:
    1. Load existing data from DB
    2. Load main file (XLSX)
    3. Parse XML feeds
    4. Scrape (if enabled)
    5. Merge all sources
    6. Map categories (with callback for unknowns)
    7. Apply pricing (with callback for unmapped)
    8. AI enhancement (if enabled)
    9. Transform to output format
    10. Save to DB
    11. Write output file
    """

    def __init__(self, config: Dict):
        self.config = config
        db_path = config.get("db_path", "data/products.db")

        self.db = ProductDB(db_path)
        self.batch_job_db = BatchJobDB(db_path)
        self.merger = ProductMerger()
        self.category_service = CategoryService()
        self.transformer = OutputTransformer(config)
        self.enricher = ProductEnricher(config, batch_job_db=self.batch_job_db)
        self.pricing_service = PricingService()
        self.scraping = ScrapingOrchestrator(config)

    def run(
        self,
        options: PipelineOptions,
        on_progress: Optional[Callable] = None,
        on_unknown_category: Optional[Callable] = None,
        on_unmapped_price: Optional[Callable] = None,
    ) -> PipelineResult:
        """Execute the full pipeline.

        Args:
            options: Typed pipeline options
            on_progress: Progress callback (message: str)
            on_unknown_category: Callback for unmapped categories
            on_unmapped_price: Callback for unmapped prices

        Returns:
            PipelineResult with stats and output path
        """
        start_time = time.time()
        result = PipelineResult()

        def progress(msg: str):
            if on_progress:
                on_progress(msg)
            logger.info(msg)

        # 1. Load existing data from DB
        progress("Loading existing data from database...")
        db_df = self.db.get_all()

        # 2. Load main file
        main_df = pd.DataFrame()
        if options.main_file_path:
            progress(f"Loading main data file: {options.main_file_path}")
            main_df = DataLoaderFactory.load(options.main_file_path)

        # If we have DB data but no main file, use DB as main
        if main_df.empty and not db_df.empty:
            main_df = db_df

        # 3. Parse XML feeds
        feed_dfs = {}
        xml_feeds = self.config.get("xml_feeds", {})
        for feed_name, feed_config in xml_feeds.items():
            url = feed_config.get("url", "")
            if not url:
                continue
            progress(f"Parsing XML feed: {feed_name}")
            feed_df = XMLParserFactory.fetch_and_parse(feed_name, url, self.config)
            if feed_df is not None and not feed_df.empty:
                feed_dfs[feed_name] = feed_df

        # 4. Scrape (if enabled)
        if options.enable_scraping:
            progress("Starting web scraping...")
            scraped = self.scraping.scrape(
                scrape_mebella=options.scrape_mebella,
                scrape_topchladenie=options.scrape_topchladenie,
                topchladenie_csv_path=options.topchladenie_csv_path,
                progress_callback=lambda msg: progress(msg),
            )
            feed_dfs.update(scraped)

        # 5. Merge all sources
        progress("Merging product data...")
        merge_result = self.merger.merge(
            main_df=main_df,
            feed_dfs=feed_dfs,
            selected_categories=options.selected_categories or None,
            preserve_edits=options.preserve_client_edits,
        )
        merged_df = merge_result.products
        result.merge_stats = merge_result.stats

        # 6. Map categories
        if on_unknown_category:
            self.category_service.set_interactive_callback(on_unknown_category)
        progress("Mapping categories...")
        for idx, row in merged_df.iterrows():
            old_cat = str(row.get("defaultCategory", ""))
            if old_cat:
                new_cat = self.category_service.map_or_ask(old_cat, str(row.get("name", "")))
                merged_df.at[idx, "defaultCategory"] = new_cat
                merged_df.at[idx, "categoryText"] = new_cat

        # 7. Apply pricing
        if options.enable_price_mapping:
            progress("Applying price mappings...")
            merged_df = self.pricing_service.apply_mappings(merged_df)
            unmapped = self.pricing_service.identify_unmapped(merged_df)
            if unmapped and on_unmapped_price:
                on_unmapped_price(unmapped)

        # 8. AI enhancement
        if options.enable_ai_enhancement:
            progress("Starting AI enhancement...")
            enrichment = self.enricher.enrich(
                merged_df,
                force_reprocess=options.force_ai_reprocess,
                progress_callback=lambda *args: progress(args[-1] if args else "AI processing..."),
            )
            merged_df = enrichment.products
            result.enrichment_stats = enrichment

        # 9. Transform to output format
        progress("Transforming to output format...")
        output_df = self.transformer.transform(merged_df)

        # 10. Save to DB
        progress("Saving to database...")
        self.db.backup()
        self.db.upsert(merged_df)

        # 11. Write output file
        if options.output_path:
            progress(f"Writing output to: {options.output_path}")
            write_xlsx(output_df, options.output_path)
            result.output_path = options.output_path

        result.product_count = len(output_df)
        result.duration_seconds = time.time() - start_time

        progress(f"Pipeline complete. {result.product_count} products processed in {result.duration_seconds:.1f}s")
        return result

    def load_main_data(self, file_path: str) -> pd.DataFrame:
        """Load main data file. Convenience method."""
        return DataLoaderFactory.load(file_path)

    def parse_xml(self, feed_name: str, xml_content: str) -> pd.DataFrame:
        """Parse an XML feed. Convenience method for testing."""
        result = XMLParserFactory.parse(feed_name, xml_content, self.config)
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
