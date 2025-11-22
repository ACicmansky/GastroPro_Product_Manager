"""
Scraper for TopChladenie.sk.
"""

import logging
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class TopchladenieScraper(BaseScraper):
    """
    Scraper for TopChladenie.sk outputting to new 138-column format.
    """

    def __init__(
        self,
        config: Dict,
        base_url: str = "https://www.topchladenie.sk",
        progress_callback=None,
        max_threads: int = 1,
    ):
        self.config = config
        super().__init__(base_url, progress_callback, max_threads)

    def get_category_links(self) -> List[str]:
        """
        Get list of category URLs to scrape.

        Returns:
            List of category URLs
        """
        print("\\nGetting category links...")

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

        print(f"\\n✓ Loaded {len(category_links)} categories\\n")
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

    def scrape_product_detail(self, product_url: str) -> Optional[Dict]:
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
                    short_desc = "\\n".join(
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
                        section_text = section_text.replace("\\xa0", " ").replace(
                            "&nbsp;", " "
                        )
                        if section_text:
                            long_desc_parts.append(section_text)

            product_data["description"] = "\\n\\n".join(long_desc_parts)

            # Images - split into 8 columns immediately
            image_urls = []
            gallery = soup.find("div", id="productGallery")
            if gallery:
                for img_link in gallery.find_all("a"):
                    href = img_link.get("href")
                    if href and (
                        "/data/sharedfiles/obrazky/produkty/pFull/" in href
                        or "/data/sharedfiles/obrazky/pFull/" in href
                    ):
                        image_urls.append(urljoin(self.base_url, href))

            # Split images into 8 columns
            unique_images = list(dict.fromkeys(image_urls))[
                :8
            ]  # Max 8 images, preserve order
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
