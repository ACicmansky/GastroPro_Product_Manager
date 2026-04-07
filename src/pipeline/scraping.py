"""Scraping orchestration — coordinates web scrapers."""

import logging
from typing import Dict, Optional, Callable

import pandas as pd

from src.scrapers.mebella_scraper import MebellaScraper
from src.scrapers.topchladenie_scraper import TopchladenieScraper

logger = logging.getLogger(__name__)


class ScrapingOrchestrator:
    """Orchestrates web scraping from multiple sources."""

    def __init__(self, config: Dict):
        self.config = config

    def scrape(
        self,
        scrape_mebella: bool = False,
        scrape_topchladenie: bool = False,
        topchladenie_csv_path: str = "",
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Run enabled scrapers and return source-tagged DataFrames.

        Returns:
            Dict of source_name -> DataFrame
        """
        results = {}

        if scrape_mebella:
            if progress_callback:
                progress_callback("Scraping Mebella products...")
            try:
                scraper = MebellaScraper(progress_callback=progress_callback)
                df = scraper.scrape_products()
                if df is not None and not df.empty:
                    df["source"] = "web_scraping"
                    results["mebella"] = df
                    logger.info(f"Scraped {len(df)} products from Mebella")
            except Exception as e:
                logger.error(f"Mebella scraping failed: {e}")

        if scrape_topchladenie:
            if progress_callback:
                progress_callback("Scraping Topchladenie products...")
            try:
                scraper = TopchladenieScraper(
                    config=self.config,
                    progress_callback=progress_callback,
                )
                if topchladenie_csv_path:
                    df = pd.read_csv(topchladenie_csv_path, sep=";", encoding="utf-8")
                else:
                    df = scraper.scrape_products()
                if df is not None and not df.empty:
                    df["source"] = "web_scraping"
                    results["topchladenie"] = df
                    logger.info(f"Scraped {len(df)} products from Topchladenie")
            except Exception as e:
                logger.error(f"Topchladenie scraping failed: {e}")

        return results
