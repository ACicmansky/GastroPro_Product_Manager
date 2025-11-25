import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class MebellaScraper(BaseScraper):
    """Scraper for Mebella.pl (Table Bases)."""

    def __init__(
        self,
        base_url: str = "https://mebella.pl",
        progress_callback=None,
        max_threads: int = 8,
        cache_dir: str = "cache/mebella_urls",
    ):
        super().__init__(base_url, progress_callback, max_threads)
        self.cache_dir = cache_dir
        # Mebella requires browser-like headers to bypass 403
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "Cookie": "pll_language=en; wp-wpml_current_language=en",
            }
        )

    def _get_cache_path(self, category_url: str) -> str:
        """Generates a cache file path for a given category URL."""
        import hashlib
        import os

        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        url_hash = hashlib.md5(category_url.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.json")

    def _load_cached_urls(self, category_url: str) -> Optional[List[str]]:
        """Loads cached URLs if they exist and are fresh (less than 24h old)."""
        import json
        import os
        import time

        cache_path = self._get_cache_path(category_url)
        if os.path.exists(cache_path):
            try:
                # Check file age (24 hours = 86400 seconds)
                if time.time() - os.path.getmtime(cache_path) < 604800:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        logger.info(
                            f"Loaded {len(data)} URLs from cache for {category_url}"
                        )
                        return data
            except Exception as e:
                logger.warning(f"Failed to load cache for {category_url}: {e}")
        return None

    def _save_cached_urls(self, category_url: str, urls: List[str]):
        """Saves URLs to cache."""
        import json

        try:
            cache_path = self._get_cache_path(category_url)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(urls, f)
            logger.info(f"Saved {len(urls)} URLs to cache for {category_url}")
        except Exception as e:
            logger.warning(f"Failed to save cache for {category_url}: {e}")

    def get_category_links(self) -> List[str]:
        """
        Returns the main category link.
        Since we are targeting a specific category, we just return the base URL.
        """
        print("\nGetting category links...")
        category_links = []
        direct_categories = [
            "/en/product-category/table-bases/gerro-en/",
            "/en/product-category/table-bases/bow-en/",
            "/en/product-category/table-bases/conti-new-en/",
            "/en/product-category/table-bases/bea-en/",
            "/en/product-category/table-bases/unique-en/",
            "/en/product-category/table-bases/pod-en/",
            "/en/product-category/table-bases/plus-en/",
            "/en/product-category/table-bases/flat-en/",
            "/en/product-category/table-bases/oval-en/",
            "/en/product-category/table-bases/yeti-en/",
            "/en/product-category/table-bases/inox-en/",
            "/en/product-category/table-bases/brass-en/",
        ]

        for category in direct_categories:
            category_links.append(urljoin(self.base_url, category))
        return category_links

    def get_product_urls(self, category_url: str, use_cache: bool = True) -> List[str]:
        """
        Extracts product URLs from the category page using Playwright to handle AJAX pagination.
        """
        # Check cache first
        if use_cache:
            cached_urls = self._load_cached_urls(category_url)
            if cached_urls:
                return cached_urls

        from playwright.sync_api import sync_playwright

        product_urls = []
        logger.info(f"Scraping category page with Playwright: {category_url}")

        try:
            with sync_playwright() as p:
                # Launch browser (headless)
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Set headers to mimic real browser
                page.set_extra_http_headers(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                )

                # Navigate to category page
                page.goto(category_url, timeout=60000)

                # Handle cookie consent if it appears (optional but good practice)
                try:
                    page.click("button#cookie_action_close_header", timeout=2000)
                except:
                    pass

                last_product_count = 0
                no_change_count = 0
                max_no_change = 3  # Stop after 3 attempts with no new products

                while True:
                    # Scroll to bottom to trigger any lazy loading
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)  # Wait for scroll event

                    # Try to click "Load More" button if it exists (some themes have it)
                    load_more_selectors = [
                        "a.post-load-more",
                        ".woocommerce-pagination a.next",
                        ".load-more",
                    ]
                    clicked = False
                    for selector in load_more_selectors:
                        if page.is_visible(selector):
                            try:
                                page.click(selector)
                                page.wait_for_timeout(3000)
                                clicked = True
                                break
                            except:
                                pass

                    if not clicked:
                        # If no button, just wait a bit more for infinite scroll
                        page.wait_for_timeout(2000)

                    # Count products
                    # Selector: div.product_title a
                    links = page.query_selector_all("div.product_title a")
                    if not links:
                        links = page.query_selector_all("a[href*='/produkt/']")

                    current_count = len(links)
                    logger.info(f"Current product count: {current_count}")

                    if current_count > last_product_count:
                        last_product_count = current_count
                        no_change_count = 0
                    else:
                        no_change_count += 1
                        logger.info(
                            f"No new products found. Attempt {no_change_count}/{max_no_change}"
                        )

                        # Try scrolling up a bit and back down to trigger scroll events
                        if no_change_count < max_no_change:
                            page.evaluate("window.scrollBy(0, -500)")
                            page.wait_for_timeout(500)
                            page.evaluate(
                                "window.scrollTo(0, document.body.scrollHeight)"
                            )
                            page.wait_for_timeout(2000)

                    if no_change_count >= max_no_change:
                        logger.info("Reached end of product list.")
                        break

                # Extract all product links after full load
                links = page.query_selector_all("div.product_title a")
                if not links:
                    # Fallback selector
                    links = page.query_selector_all("a[href*='/produkt/']")

                for link in links:
                    href = link.get_attribute("href")
                    if href and "/produkt/" in href:
                        full_url = urljoin(self.base_url, href)
                        if full_url not in product_urls:
                            product_urls.append(full_url)

                browser.close()

            logger.info(f"Found {len(product_urls)} products in total.")

            # Save to cache
            if product_urls:
                self._save_cached_urls(category_url, product_urls)

        except Exception as e:
            logger.error(f"Error scraping category page with Playwright: {e}")
            # Fallback to requests if Playwright fails completely
            return self._get_product_urls_fallback(category_url)

        return product_urls

    def _get_product_urls_fallback(self, category_url: str) -> List[str]:
        """
        Fallback method using requests (only gets first page).
        """
        product_urls = []
        try:
            response = self.session.get(category_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            links = soup.select("div.product_title a")
            if not links:
                links = soup.select("a[href*='/produkt/']")

            for link in links:
                href = link.get("href")
                if href and "/produkt/" in href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in product_urls:
                        product_urls.append(full_url)
        except Exception as e:
            logger.error(f"Fallback scraping failed: {e}")

        return product_urls

    def scrape_product_detail(self, url: str) -> Optional[Dict]:
        """
        Scrapes detailed information from a product page.
        """
        try:
            logger.info(f"Scraping product: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # 1. Product Name
            name = None
            # Try title tag
            title_tag = soup.find("title")
            if title_tag:
                name = (
                    title_tag.get_text(strip=True)
                    .replace(" – Mebella", "")
                    .replace(" &#8211; Mebella", "")
                    .strip()
                )

            # Try SKU span if title tag fails: <span class="sku">BEA BIG DINING</span>
            if not name:
                sku_span = soup.select_one("span.sku")
                if sku_span:
                    name = sku_span.get_text(strip=True)

            if not name:
                logger.warning(f"Could not find product name for {url}")
                return None

            # 2. Category
            category_name = f"Table Bases > {name.split()[0].capitalize}"

            # 3. Description
            description = ""
            desc_div = soup.select_one(
                "div.elementor-widget-woocommerce-product-content"
            )
            if desc_div:
                description = desc_div.get_text(separator="\n", strip=True)

            # 4. Images
            images = []
            # Main image
            main_img = soup.select_one("div.woocommerce-product-gallery__image a")
            if main_img and main_img.get("href"):
                images.append(main_img.get("href"))

            # Gallery images (if any additional ones exist, usually in thumbnails)
            # The snippet showed thumbnails with data-large_image
            thumbnails = soup.select("div.woocommerce-product-gallery__image")
            for thumb in thumbnails:
                a_tag = thumb.find("a")
                if a_tag and a_tag.get("href"):
                    img_url = a_tag.get("href")
                    if img_url not in images:
                        images.append(img_url)

            # 5. Attributes
            # The page uses Elementor with 50/50 columns for attributes.
            # Structure: section.elementor-inner-section -> div.elementor-container -> 2x div.elementor-col-50
            attributes = {}

            # Find all inner sections
            inner_sections = soup.select("section.elementor-inner-section")
            for section in inner_sections:
                # Check for two 50% columns
                cols = section.select("div.elementor-col-50")
                if len(cols) == 2:
                    # Extract text from both columns
                    key_col = cols[0].get_text(strip=True)
                    val_col = cols[1].get_text(strip=True)

                    # Basic validation to ensure it looks like an attribute pair
                    # Keys usually end with ':' or are short phrases
                    if key_col and val_col and len(key_col) < 50:
                        # Clean key (remove trailing colon)
                        key = key_col.rstrip(":")
                        attributes[key] = val_col

            # 6. Parse "Size" section (h, a, b)
            # Look for text widgets containing "h:", "a:", "b:"
            # Pattern: <p>h: <strong>720 mm</strong></p>
            text_widgets = soup.select("div.elementor-widget-text-editor")
            for widget in text_widgets:
                text = widget.get_text(strip=True)
                # Use regex to extract values
                # h: 720 mm
                h_match = re.search(r"h:\s*(\d+)", text, re.IGNORECASE)
                if h_match:
                    attributes["Height"] = h_match.group(1)

                # a: 570 mm
                a_match = re.search(r"a:\s*(\d+)", text, re.IGNORECASE)
                if a_match:
                    attributes["Width"] = a_match.group(1)

                # b: 570 mm
                b_match = re.search(r"b:\s*(\d+)", text, re.IGNORECASE)
                if b_match:
                    attributes["Depth"] = b_match.group(1)

            # 7. Fallback to CSS classes if Elementor parsing fails
            if not attributes:
                product_div = soup.select_one("div.type-product")
                if product_div and product_div.get("class"):
                    for cls in product_div.get("class"):
                        if cls.startswith("pa_"):
                            clean_cls = cls[3:]
                            if clean_cls.endswith("-en"):
                                clean_cls = clean_cls[:-3]
                            parts = clean_cls.split("-")
                            if len(parts) >= 2:
                                key = " ".join(parts[:-1]).capitalize()
                                val = parts[-1].capitalize()
                                attributes[key] = val

            # Construct the result dictionary mapped to new_output_columns
            result = {
                "code": name,
                "pairCode": "",
                "name": name,
                "shortDescription": description,
                "manufacturer": "Mebella",
                "defaultCategory": category_name,
                "categoryText": category_name,
                "availabilityInStock": "1",  # Assume in stock if scraped
            }

            # Map dimensions
            if "Height" in attributes:
                suffix = ""
                if attributes["Height"] == "600":
                    suffix = " COFFEE"
                elif attributes["Height"] == "720":
                    suffix = " DINING"
                elif attributes["Height"] == "1060":
                    suffix = " BAR"
                result["variant:Výška (mm)"] = f"{attributes['Height']}{suffix}"
                result["height"] = attributes["Height"]
            if "Width" in attributes:
                result["width"] = attributes["Width"]
            if "Depth" in attributes:
                result["depth"] = attributes["Depth"]

            # Map images
            if images:
                result["image"] = images[0]
                for i, img in enumerate(images[1:], start=2):
                    if i <= 8:
                        result[f"image{i}"] = img

            if attributes:
                # Combine all attributes into description
                attr_lines = []
                for k, v in attributes.items():
                    attr_lines.append(f"{k}: {v}")
                result["description"] = "\n".join(attr_lines)

            return result

        except Exception as e:
            logger.error(f"Error scraping product {url}: {e}")
            return None
