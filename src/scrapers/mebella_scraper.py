import logging
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.scraper_new_format import ScraperNewFormat, ScraperConfig

logger = logging.getLogger(__name__)


class MebellaScraper(ScraperNewFormat):
    """
    Scraper for Mebella.pl (Table Bases).
    """

    def __init__(
        self,
        config: Dict,
        base_url: str = "https://mebella.pl/en/product-category/table-bases/",
        progress_callback=None,
    ):
        super().__init__(config, base_url, progress_callback)
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

    def get_category_links(self) -> List[str]:
        """
        Returns the main category link.
        Since we are targeting a specific category, we just return the base URL.
        """
        return [self.base_url]

    def get_product_urls(self, category_url: str) -> List[str]:
        """
        Extracts product URLs from the category page, handling pagination.
        """
        product_urls = []
        page = 1

        while True:
            # Construct URL for the current page
            if page == 1:
                url = category_url
            else:
                url = f"{category_url}page/{page}/"

            logger.info(f"Scraping category page: {url}")

            try:
                response = self.session.get(url)
                if response.status_code == 404:
                    logger.info("Reached end of pagination (404).")
                    break

                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")

                # Find product links
                # Based on analysis: div.product_title a
                links = soup.select("div.product_title a")
                if not links:
                    # Fallback: try finding any link with /produkt/ in href
                    links = soup.select("a[href*='/produkt/']")

                new_urls = []
                for link in links:
                    href = link.get("href")
                    if href and "/produkt/" in href:
                        full_url = urljoin(self.base_url, href)
                        if full_url not in product_urls and full_url not in new_urls:
                            new_urls.append(full_url)

                if not new_urls:
                    logger.info("No more products found on this page.")
                    break

                product_urls.extend(new_urls)
                logger.info(
                    f"Found {len(new_urls)} products on page {page}. Total: {len(product_urls)}"
                )

                page += 1

            except Exception as e:
                logger.error(f"Error scraping category page {url}: {e}")
                break

        return product_urls

    def scrape_product_detail(
        self, url: str, category_name: str = "Table Bases"
    ) -> Optional[Dict]:
        """
        Scrapes detailed information from a product page.
        """
        try:
            logger.info(f"Scraping product: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # 1. Product Name
            # Try SKU span first as it seems most complete: <span class="sku">BEA BIG DINING</span>
            name = None
            sku_span = soup.select_one("span.sku")
            if sku_span:
                name = sku_span.get_text(strip=True)

            if not name:
                # Fallback to title tag
                title_tag = soup.find("title")
                if title_tag:
                    name = (
                        title_tag.get_text(strip=True)
                        .replace(" – Mebella", "")
                        .replace(" &#8211; Mebella", "")
                    )

            if not name:
                logger.warning(f"Could not find product name for {url}")
                return None

            # 2. Price
            # Prices seem to be hidden or "On Request". Default to 0.
            price = 0.0
            # Attempt to find price if it exists
            price_elem = soup.select_one(".woocommerce-Price-amount")
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Clean price text (remove currency, replace comma with dot)
                price_text = re.sub(r"[^\d.,]", "", price_text).replace(",", ".")
                try:
                    price = float(price_text)
                except ValueError:
                    pass

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

            # Fallback to CSS classes if Elementor parsing fails (though Elementor seems to be the primary source now)
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
                "name": name,
                "price": price,
                "shortDescription": description,
                "manufacturer": "Mebella",
                "defaultCategory": category_name,
                "currency": "EUR",
                "vat": "23",  # Default VAT
                "unit": "ks",
                "availabilityInStock": "1",  # Assume in stock if scraped
            }

            # Map dimensions
            if "Height" in attributes:
                result["height"] = attributes["Height"]
            if "Width" in attributes:
                result["width"] = attributes["Width"]
            if "Depth" in attributes:
                result["depth"] = attributes["Depth"]

            # Map images
            if images:
                result["defaultImage"] = images[0]
                for i, img in enumerate(images[1:], start=2):
                    if i <= 7:
                        result[f"image{i}"] = img

            # Combine all attributes into description
            if attributes:
                attr_lines = []
                for k, v in attributes.items():
                    attr_lines.append(f"{k}: {v}")

                # Combine original description with attributes
                if result["shortDescription"]:
                    result["description"] = (
                        result["shortDescription"] + "\n\n" + "\n".join(attr_lines)
                    )
                else:
                    result["description"] = "\n".join(attr_lines)

            return result

        except Exception as e:
            logger.error(f"Error scraping product {url}: {e}")
            return None
