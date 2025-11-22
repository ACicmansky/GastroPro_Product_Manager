"""
Base scraper class with configurable multithreading support.

This module provides an abstract base class for web scrapers with built-in
support for both single-threaded and multi-threaded execution.
"""

import logging
import pandas as pd
import requests
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class ScraperConfig:
    """Configuration for scraping parameters."""

    REQUEST_DELAY_MIN = 0.5
    REQUEST_TIMEOUT = 30
    DEFAULT_THREADS = 8
    MAX_THREADS = 16
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class BaseScraper(ABC):
    """
    Abstract base class for web scrapers with configurable multithreading.

    Subclasses must implement:
    - get_category_links(): Return list of category URLs
    - get_product_urls(category_url): Return list of product URLs in category
    - scrape_product_detail(product_url): Return dict with product data
    """

    def __init__(
        self,
        base_url: str,
        progress_callback: Optional[Callable] = None,
        max_threads: int = 1,
    ):
        """
        Initialize scraper with configuration.

        Args:
            config: Configuration dictionary from config.json
            base_url: Base URL for scraping
            progress_callback: Optional callback for progress updates
            max_threads: Number of threads for parallel scraping (1 = single-threaded)
        """
        self.base_url = base_url
        self.progress_callback = progress_callback
        self.scraper_config = ScraperConfig()

        # Validate and set max_threads
        self.max_threads = min(max(1, max_threads), ScraperConfig.MAX_THREADS)

        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.scraper_config.USER_AGENT})
        self.session.timeout = self.scraper_config.REQUEST_TIMEOUT

        # Lock for thread-safe operations
        self.lock = Lock()

    def _log_progress(self, message: str):
        """Log progress message to terminal and callback."""
        # Log to terminal (visible in console)
        print(message)
        # Log to file
        logger.info(message)
        # Call progress callback if provided
        if self.progress_callback:
            self.progress_callback(message)

    def scrape_products(
        self,
        category_urls: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Scrape products from the website.

        Args:
            category_urls: List of category URLs to scrape (optional)

        Returns:
            DataFrame with scraped products
        """
        print("\\n" + "=" * 60)
        print(f"WEB SCRAPING - {self.base_url}")
        print("=" * 60)
        self._log_progress(f"Starting web scraping... (Threads: {self.max_threads})")

        # Get category links if not provided
        if not category_urls:
            category_urls = self.get_category_links()

        self._log_progress(f"\\nFound {len(category_urls)} categories to scrape")

        # Get all product URLs
        product_urls = []
        for i, category_url in enumerate(category_urls):
            self._log_progress(
                f"\\n[Category {i+1}/{len(category_urls)}] {category_url}"
            )
            urls = self.get_product_urls(category_url)
            product_urls.extend(urls)
            self._log_progress(f"  Found {len(urls)} products in this category")

        unique_urls = list(set(product_urls))

        self._log_progress(f"\\n{'='*60}")
        self._log_progress(f"Total: {len(unique_urls)} unique product URLs to scrape")
        self._log_progress(f"{'='*60}\\n")

        # Choose scraping method based on max_threads
        if self.max_threads == 1:
            products_data = self._scrape_single_threaded(unique_urls)
        else:
            products_data = self._scrape_multi_threaded(unique_urls)

        # Create DataFrame from scraped data
        result_df = pd.DataFrame(products_data)

        # Clean data
        self._log_progress(f"\\nCleaning scraped data...")
        result_df = self._clean_data(result_df)

        print("\\n" + "=" * 60)
        self._log_progress(f"✓ SCRAPING COMPLETE: {len(result_df)} products scraped")
        print("=" * 60 + "\\n")
        return result_df

    def _scrape_single_threaded(self, product_urls: List[str]) -> List[Dict]:
        """
        Scrape products using single-threaded execution.

        Args:
            product_urls: List of product URLs to scrape

        Returns:
            List of product data dictionaries
        """
        products_data = []
        for i, url in enumerate(product_urls):
            self._log_progress(f"[{i+1}/{len(product_urls)}] Scraping: {url}")
            data = self.scrape_product_detail(url)
            if data:
                products_data.append(data)
                self._log_progress(f"  ✓ Success: {data.get('name', 'Unknown')}")
            else:
                self._log_progress(f"  ✗ Skipped (no data)")
            time.sleep(self.scraper_config.REQUEST_DELAY_MIN)

        return products_data

    def _scrape_multi_threaded(self, product_urls: List[str]) -> List[Dict]:
        """
        Scrape products using multi-threaded execution.

        Args:
            product_urls: List of product URLs to scrape

        Returns:
            List of product data dictionaries
        """
        products_data = []
        completed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(self.scrape_product_detail, url): url
                for url in product_urls
            }

            # Process completed tasks
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                completed_count += 1

                try:
                    data = future.result()
                    if data:
                        with self.lock:
                            products_data.append(data)
                        self._log_progress(
                            f"[{completed_count}/{len(product_urls)}] ✓ Success: {data.get('name', 'Unknown')}"
                        )
                    else:
                        self._log_progress(
                            f"[{completed_count}/{len(product_urls)}] ✗ Skipped: {url}"
                        )
                except Exception as e:
                    self._log_progress(
                        f"[{completed_count}/{len(product_urls)}] ✗ Error scraping {url}: {e}"
                    )
                    logger.error(f"Error scraping {url}: {e}")

        return products_data

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean scraped data.

        Args:
            df: Raw scraped DataFrame

        Returns:
            Cleaned DataFrame
        """
        # Fill NaN with empty strings
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].fillna("")

        # Clean line breaks in descriptions
        for col in ["shortDescription", "description"]:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: (
                        x.replace("\\r\\n", "\\n").replace("\\r", "\\n")
                        if isinstance(x, str)
                        else x
                    )
                )

        # Handle duplicate catalog numbers
        if "code" in df.columns:
            duplicates = df[df.duplicated(subset=["code"], keep=False)]
            if not duplicates.empty:
                print(f"  ⚠ Found {len(duplicates)} products with duplicate codes")
                logger.warning(f"Found {len(duplicates)} products with duplicate codes")

                # Update prices for duplicates
                if "price" in df.columns:
                    for code in duplicates["code"].unique():
                        mask = df["code"] == code
                        duplicate_rows = df[mask]

                        if len(duplicate_rows) > 1:
                            first_idx = duplicate_rows.index[0]
                            last_price = duplicate_rows.iloc[-1]["price"]
                            df.at[first_idx, "price"] = last_price
                            print(f"    Updated price for '{code}' to {last_price}")
                            logger.info(f"Updated price for '{code}' to {last_price}")

                # Remove duplicates, keep first
                df = df.drop_duplicates(subset=["code"], keep="first")
                print(f"  ✓ Removed duplicates, kept {len(df)} unique products")
                logger.info(f"Removed duplicates, kept {len(df)} unique products")

        return df

    @abstractmethod
    def get_category_links(self) -> List[str]:
        """
        Get list of category URLs to scrape.

        Returns:
            List of category URLs
        """
        pass

    @abstractmethod
    def get_product_urls(self, category_url: str) -> List[str]:
        """
        Get product URLs from a category page.

        Args:
            category_url: Category page URL

        Returns:
            List of product URLs
        """
        pass

    @abstractmethod
    def scrape_product_detail(self, product_url: str) -> Optional[Dict]:
        """
        Scrape details from a single product page.

        Args:
            product_url: Product page URL

        Returns:
            Dictionary with product data or None if scraping fails
        """
        pass
