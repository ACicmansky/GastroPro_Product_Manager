"""
Web Scraper for new 138-column format.
Scrapes TopChladenie.sk and outputs DataFrame compatible with new pipeline.

Based on src/services/scraper.py but adapted for new format.
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Dict, List, Optional, Callable
import re

logger = logging.getLogger(__name__)


class ScraperConfig:
    """Configuration for scraping parameters."""

    REQUEST_DELAY_MIN = 0.5
    REQUEST_TIMEOUT = 30
    DEFAULT_THREADS = 8
    MAX_THREADS = 16
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class ScraperNewFormat:
    """
    Scraper for TopChladenie.sk outputting to new 138-column format.
    """

    def __init__(
        self,
        config: Dict,
        base_url: str = "https://www.topchladenie.sk",
        progress_callback: Optional[Callable] = None,
    ):
        """
        Initialize scraper with configuration.

        Args:
            config: Configuration dictionary from config.json
            base_url: Base URL for scraping
            progress_callback: Optional callback for progress updates
        """
        self.config = config
        self.base_url = base_url
        self.progress_callback = progress_callback
        self.scraper_config = ScraperConfig()

        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.scraper_config.USER_AGENT})
        self.session.timeout = self.scraper_config.REQUEST_TIMEOUT

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
        self, category_urls: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Scrape products from TopChladenie.sk (single-threaded).

        Args:
            category_urls: List of category URLs to scrape (optional)

        Returns:
            DataFrame with scraped products in new 138-column format
        """
        print("\n" + "=" * 60)
        print("WEB SCRAPING - TOPCHLADENIE.SK")
        print("=" * 60)
        self._log_progress("Starting web scraping process...")

        # Get category links
        if not category_urls:
            category_urls = self.get_category_links()

        self._log_progress(f"\nFound {len(category_urls)} categories to scrape")

        # Get all product URLs
        product_urls = []
        for i, category_url in enumerate(category_urls):
            self._log_progress(
                f"\n[Category {i+1}/{len(category_urls)}] {category_url}"
            )
            urls = self.get_product_urls(category_url)
            product_urls.extend(urls)
            self._log_progress(f"  Found {len(urls)} products in this category")

        unique_urls = list(set(product_urls))
        self._log_progress(f"\n{'='*60}")
        self._log_progress(f"Total: {len(unique_urls)} unique product URLs to scrape")
        self._log_progress(f"{'='*60}\n")

        # Scrape each product
        products_data = []
        for i, url in enumerate(unique_urls):
            self._log_progress(f"[{i+1}/{len(unique_urls)}] Scraping: {url}")
            data = self.scrape_product_detail(url)
            if data:
                products_data.append(data)
                self._log_progress(f"  ✓ Success: {data.get('name', 'Unknown')}")
            else:
                self._log_progress(f"  ✗ Skipped (no data)")
            time.sleep(self.scraper_config.REQUEST_DELAY_MIN)

        # Create DataFrame from scraped data (already in new format)
        result_df = pd.DataFrame(products_data)

        # Clean data
        self._log_progress(f"\nCleaning scraped data...")
        result_df = self._clean_data(result_df)

        print("\n" + "=" * 60)
        self._log_progress(f"✓ SCRAPING COMPLETE: {len(result_df)} products scraped")
        print("=" * 60 + "\n")
        return result_df

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean scraped data.

        Args:
            df: Raw scraped DataFrame (already in new format)

        Returns:
            Cleaned DataFrame
        """
        # Fill NaN with empty strings
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].fillna("")

        # Clean line breaks in descriptions (NEW FORMAT column names)
        for col in ["shortDescription", "description"]:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: (
                        x.replace("\r\n", "\n").replace("\r", "\n")
                        if isinstance(x, str)
                        else x
                    )
                )

        # Handle duplicate catalog numbers (NEW FORMAT: "code" column)
        if "code" in df.columns:
            duplicates = df[df.duplicated(subset=["code"], keep=False)]
            if not duplicates.empty:
                print(f"  ⚠ Found {len(duplicates)} products with duplicate codes")
                logger.warning(f"Found {len(duplicates)} products with duplicate codes")

                # Update prices for duplicates (NEW FORMAT: "price" column)
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

    def get_category_links(self) -> List[str]:
        """
        Get list of category URLs to scrape.

        Returns:
            List of category URLs
        """
        print("\nGetting category links...")

        category_links = []
        direct_categories = [
            "/e-shop/samostatne-chladnicky/bez-mraznicky-vnutri",
            "/e-shop/samostatne-chladnicky/s-mraznickou-vo-vnutri",
            "/e-shop/chladnicky-s-mraznickou/s-mraznickou-hore",
            "/e-shop/chladnicky-s-mraznickou/s-mraznickou-dole",
            "/e-shop/americke-chladnicky",
            "/e-shop/mraznicky/pultove",
            "/e-shop/mraznicky/suplikove",
            "/e-shop/vstavane-spotrebice/chladnicky-na-vino",
            "/e-shop/vstavane-spotrebice/mraznicky",
            "/e-shop/vstavane-spotrebice/chladnicky",
            "/e-shop/vstavane-spotrebice/kombinovane-chladnicky",
            "/e-shop/domace-vinoteky/temperovane",
            "/e-shop/domace-vinoteky/klimatizovane",
            "/e-shop/humidory",
            "/e-shop/komercne-zariadenia/gastro-zariadenie",
            "/e-shop/komercne-zariadenia/pekaren",
            "/e-shop/komercne-zariadenia/napojovy-priemysel",
            "/e-shop/prislusenstvo",
        ]

        for cat in direct_categories:
            full_url = urljoin(self.base_url, cat)
            category_links.append(full_url)
            print(f"  - {cat}")

        print(f"\n✓ Loaded {len(category_links)} categories\n")
        return category_links

    def get_product_urls(self, category_url: str) -> List[str]:
        """
        Get product URLs from a category page with pagination.

        Args:
            category_url: Category page URL

        Returns:
            List of product URLs
        """
        print(f"  Discovering products...")
        product_urls = []
        page = 1
        max_pages = 20  # Safety limit

        while page <= max_pages:
            url = f"{category_url}?page={page}" if page > 1 else category_url

            try:
                print(f"    Page {page}...", end=" ")
                response = self.session.get(url)
                soup = BeautifulSoup(response.content, "html.parser")

                # Find product links
                page_products = soup.select(
                    'a[href*="/e-shop/"]:not([href*="category"])'
                )

                if not page_products:
                    print("no products, stopping")
                    break

                new_products_found = False
                for product in page_products:
                    href = product.get("href")
                    if href:
                        full_url = urljoin(self.base_url, href)
                        if full_url not in product_urls:
                            product_urls.append(full_url)
                            new_products_found = True

                if not new_products_found:
                    print("no new products, stopping")
                    break

                print(
                    f"found {len([p for p in page_products if p.get('href')])} products"
                )

                # Check for next page link
                next_page_link = soup.select_one("a.next")
                if not next_page_link:
                    break

                page += 1
                time.sleep(self.scraper_config.REQUEST_DELAY_MIN)

            except Exception as e:
                print(f"error: {e}")
                logger.error(f"Error processing page {page} of {category_url}: {e}")
                break

        return list(set(product_urls))

    def scrape_product_detail(self, product_url: str) -> Dict:
        """
        Scrape details from a single product page.

        Args:
            product_url: Product page URL

        Returns:
            Dictionary with product data in NEW FORMAT (English column names)
        """
        try:
            response = self.session.get(product_url)
            soup = BeautifulSoup(response.content, "html.parser")

            # Product name
            product_name = (
                soup.select_one('h1[itemprop="name"]').text.strip()
                if soup.select_one('h1[itemprop="name"]')
                else ""
            )

            if not product_name:
                return None

            # Initialize product data with NEW FORMAT column names
            product_data = {}
            product_data["code"] = product_name
            product_data["name"] = product_name

            # Price
            price_elem = soup.find("p", class_=["big", "red"])
            price = (
                float(price_elem["content"])
                if price_elem and price_elem.get("content")
                else 0.0
            )
            product_data["price"] = str(price)

            # Manufacturer
            product_data["manufacturer"] = "Liebherr"

            # Short description from parameters
            params_heading = soup.find("h2", string="Hlavní parametre")
            short_desc = ""
            if params_heading:
                params_list = params_heading.find_next("ul")
                if params_list:
                    short_desc = "\n".join(
                        [li.get_text(strip=True) for li in params_list.find_all("li")]
                    )
            product_data["shortDescription"] = short_desc

            # Long description from article sections
            long_desc_parts = []
            article_section = soup.find(
                "section", class_=lambda x: x and "article_module" in x
            )
            if article_section:
                for section in article_section.find_all("section"):
                    inner_section = section.findChild("section")
                    if inner_section:
                        # Get h3 text
                        h3_text = inner_section.h3.get_text(strip=True)
                        # Get the rest of the text (excluding h3)
                        section_text = (
                            inner_section.get_text(strip=True)
                            .replace(h3_text, "", 1)
                            .strip()
                        )
                        # Clean up whitespace characters
                        section_text = section_text.replace("\xa0", " ").replace(
                            "&nbsp;", " "
                        )
                        if section_text:
                            long_desc_parts.append(section_text)

            product_data["description"] = "\n\n".join(long_desc_parts)

            # Images - split into 8 columns immediately
            image_urls = []
            gallery = soup.find("div", id="productGallery")
            if gallery:
                for img_link in gallery.find_all("a"):
                    href = img_link.get("href")
                    if href and "/data/sharedfiles/obrazky/produkty/pFull/" in href:
                        image_urls.append(urljoin(self.base_url, href))

            # Split images into 8 columns
            unique_images = list(set(image_urls))[:8]  # Max 8 images
            image_columns = [
                "defaultImage",
                "image",
                "image2",
                "image3",
                "image4",
                "image5",
                "image6",
                "image7",
            ]
            for i, col_name in enumerate(image_columns):
                product_data[col_name] = (
                    unique_images[i] if i < len(unique_images) else ""
                )

            # Category - with transformation
            category_div = soup.find("div", class_="category")
            if category_div:
                category_links = category_div.find_all("a")
                if category_links:
                    last_category_link = category_links[-1]
                    category_url = last_category_link.get("href")

                    # Skip mystyle products
                    if category_url == "/e-shop/mystyle":
                        return None

                    # Save raw category URL - let category mapper handle transformation
                    # This ensures proper mapping through categories.json and correct format
                    product_data["defaultCategory"] = category_url
                    product_data["categoryText"] = category_url
                else:
                    product_data["defaultCategory"] = ""
                    product_data["categoryText"] = ""
            else:
                return None

            product_data["active"] = "1"

            return product_data

        except Exception as e:
            logger.error(f"Error extracting details from {product_url}: {e}")
            return None


# For backward compatibility with old scraper
class EnhancedScraperNewFormat(ScraperNewFormat):
    """
    Enhanced version with multi-threading support.
    """

    def __init__(
        self,
        config: Dict,
        base_url: str = "https://www.topchladenie.sk",
        progress_callback: Optional[Callable] = None,
        max_threads: int = 8,
    ):
        super().__init__(config, base_url, progress_callback)
        self.max_threads = min(max_threads, ScraperConfig.MAX_THREADS)
        self.lock = Lock()

    def scrape_products(
        self,
        category_urls: Optional[List[str]] = None,
        max_products: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Scrape products in parallel using thread pool.

        Args:
            category_urls: List of category URLs to scrape
            max_products: Maximum number of products to scrape

        Returns:
            DataFrame with scraped products in new format
        """
        print("\n" + "=" * 60)
        print("WEB SCRAPING - TOPCHLADENIE.SK (MULTI-THREADED)")
        print("=" * 60)
        self._log_progress(
            f"Starting parallel scraping with {self.max_threads} threads..."
        )

        # Get category links
        if not category_urls:
            category_urls = self.get_category_links()

        self._log_progress(f"\nFound {len(category_urls)} categories to scrape")
        self._log_progress(f"\n{'='*60}")
        self._log_progress("PHASE 1: Discovering Products (Parallel)")
        self._log_progress(f"{'='*60}\n")

        # Step 1: Get all product URLs in parallel
        all_product_urls = []
        completed_categories = 0
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_url = {
                executor.submit(self.get_product_urls, url): url
                for url in category_urls
            }

            for future in as_completed(future_to_url):
                try:
                    urls = future.result()
                    all_product_urls.extend(urls)
                    completed_categories += 1
                    self._log_progress(
                        f"[{completed_categories}/{len(category_urls)}] Discovered {len(urls)} products | Total: {len(all_product_urls)}"
                    )
                except Exception as e:
                    completed_categories += 1
                    print(f"  ✗ Error in category: {e}")
                    logger.error(f"Error getting product URLs: {e}")

        unique_urls = list(set(all_product_urls))
        self._log_progress(f"\n{'='*60}")
        self._log_progress(
            f"✓ Discovery complete: {len(unique_urls)} unique product URLs"
        )
        self._log_progress(f"{'='*60}\n")

        # Apply max_products limit if specified
        if max_products:
            unique_urls = unique_urls[:max_products]
            self._log_progress(f"⚠ Limited to {max_products} products for testing\n")

        # Step 2: Scrape product details in parallel
        self._log_progress(f"{'='*60}")
        self._log_progress("PHASE 2: Scraping Product Details (Parallel)")
        self._log_progress(f"{'='*60}\n")

        scraped_products = []
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_product = {
                executor.submit(self.scrape_product_detail, url): url
                for url in unique_urls
            }

            for future in as_completed(future_to_product):
                try:
                    product_data = future.result()
                    if product_data:
                        with self.lock:
                            scraped_products.append(product_data)
                            progress_pct = (
                                len(scraped_products) / len(unique_urls)
                            ) * 100
                            self._log_progress(
                                f"[{len(scraped_products)}/{len(unique_urls)}] {progress_pct:.1f}% | "
                                f"Latest: {product_data.get('name', 'Unknown')[:50]}..."
                            )
                except Exception as e:
                    print(f"  ✗ Error scraping product: {e}")
                    logger.error(f"Error scraping product: {e}")

        # Create DataFrame (already in new format)
        result_df = pd.DataFrame(scraped_products)

        # Clean data
        self._log_progress(f"\nCleaning scraped data...")
        result_df = self._clean_data(result_df)

        print("\n" + "=" * 60)
        self._log_progress(
            f"✓ PARALLEL SCRAPING COMPLETE: {len(result_df)} products scraped"
        )
        print("=" * 60 + "\n")
        return result_df
