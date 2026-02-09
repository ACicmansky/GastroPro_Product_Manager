import requests
import pandas as pd
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from tqdm import tqdm
from ..utils.config_loader import CategoryMappingManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TopchladenieScraper")


class ScrapingConfig:
    """Configuration class for scraping parameters"""

    REQUEST_DELAY_MIN = 0.5
    REQUEST_TIMEOUT = 30
    DEFAULT_THREADS = 8
    MAX_THREADS = 16
    CSV_ENCODING = "utf-8-sig"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ULRS_TO_SKIP_DURING_GET_PRODUCT_URLS = [
        "https://www.topchladenie.sk/e-shop/samostatne-chladnicky",
        "https://www.topchladenie.sk/e-shop/samostatne-chladnicky/bez-mraznicky-vnutri",
        "https://www.topchladenie.sk/e-shop/samostatne-chladnicky/s-mraznickou-vo-vnutri",
        "https://www.topchladenie.sk/e-shop/chladnicky-s-mraznickou",
        "https://www.topchladenie.sk/e-shop/chladnicky-s-mraznickou/s-mraznickou-hore",
        "https://www.topchladenie.sk/e-shop/chladnicky-s-mraznickou/s-mraznickou-dole",
        "https://www.topchladenie.sk/e-shop/americke-chladnicky",
        "https://www.topchladenie.sk/e-shop/mraznicky",
        "https://www.topchladenie.sk/e-shop/mraznicky/pultove",
        "https://www.topchladenie.sk/e-shop/mraznicky/suplikove",
        "https://www.topchladenie.sk/e-shop/vstavane-spotrebice",
        "https://www.topchladenie.sk/e-shop/vstavane-spotrebice/chladnicky-na-vino",
        "https://www.topchladenie.sk/e-shop/vstavane-spotrebice/mraznicky",
        "https://www.topchladenie.sk/e-shop/vstavane-spotrebice/chladnicky",
        "https://www.topchladenie.sk/e-shop/vstavane-spotrebice/kombinovane-chladnicky",
        "https://www.topchladenie.sk/e-shop/domace-vinoteky",
        "https://www.topchladenie.sk/e-shop/domace-vinoteky/temperovane",
        "https://www.topchladenie.sk/e-shop/domace-vinoteky/klimatizovane",
        "https://www.topchladenie.sk/e-shop/humidory",
        "https://www.topchladenie.sk/e-shop/komercne-zariadenia",
        "https://www.topchladenie.sk/e-shop/komercne-zariadenia/gastro-zariadenie",
        "https://www.topchladenie.sk/e-shop/komercne-zariadenia/pekaren",
        "https://www.topchladenie.sk/e-shop/komercne-zariadenia/napojovy-priemysel",
        "https://www.topchladenie.sk/e-shop/prislusenstvo",
        "https://www.topchladenie.sk/e-shop/mystyle",
        "https://www.topchladenie.sk/e-shop/akcie-a-zavy",
    ]

    @classmethod
    def get_headers(cls):
        return {"User-Agent": cls.USER_AGENT}


class TopchladenieScraper:
    """Base class for scraping product data from topchladenie.sk."""

    def __init__(
        self,
        base_url="https://www.topchladenie.sk",
        progress_callback=None,
        category_manager=None,
        category_mapping_callback=None,
    ):
        self.base_url = base_url
        self.config = ScrapingConfig()
        self.session = requests.Session()
        self.session.headers.update(self.config.get_headers())
        self.session.timeout = self.config.REQUEST_TIMEOUT
        self.progress_callback = progress_callback
        self.category_manager = (
            category_manager
            if category_manager is not None
            else CategoryMappingManager()
        )
        self.category_mapping_callback = category_mapping_callback

    def _log_progress(self, message):
        if self.progress_callback:
            self.progress_callback(message)

    def get_category_links(self):
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
        return category_links

    def get_product_urls(self, category_url):
        logger.info(f"Finding products in category: {category_url}")
        product_urls = []
        page = 1
        max_pages = 20  # Safety limit
        while page <= max_pages:
            url = f"{category_url}?page={page}" if page > 1 else category_url
            try:
                logger.info(f"Fetching page {page}: {url}")
                response = self.session.get(url)
                soup = BeautifulSoup(response.content, "html.parser")
                page_products = soup.select(
                    'a[href*="/e-shop/"]:not([href*="category"])'
                )

                if not page_products:
                    logger.info(
                        f"No products found on page {page}, stopping pagination."
                    )
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
                    logger.info(f"No new products on page {page}, stopping.")
                    break

                next_page_link = soup.select_one("a.next")
                if not next_page_link:
                    break

                page += 1
                time.sleep(self.config.REQUEST_DELAY_MIN)
            except Exception as e:
                logger.error(f"Error processing page {page} of {category_url}: {e}")
                break
        return list(set(product_urls))

    def extract_product_details(self, url):
        product_data = {}
        try:
            response = self.session.get(url)
            soup = BeautifulSoup(response.content, "html.parser")

            product_name = (
                soup.select_one('h1[itemprop="name"]').text.strip()
                if soup.select_one('h1[itemprop="name"]')
                else ""
            )
            if not product_name:
                return None

            # Sanitize product name to prevent CSV injection
            if product_name and product_name.startswith(("=", "+", "-", "@")):
                product_name = "'" + product_name

            product_data["Kat. číslo"] = product_data["Názov tovaru"] = product_name
            self.current_product_name = product_name  # Store for callback context

            price_elem = soup.find("p", class_=["big", "red"])
            price = (
                float(price_elem["content"])
                if price_elem and price_elem.get("content")
                else 0.0
            )
            product_data["Bežná cena"] = price

            product_data["Výrobca"] = "Liebherr"

            params_heading = soup.find("h2", string="Hlavní parametre")
            short_desc = ""
            if params_heading:
                params_list = params_heading.find_next("ul")
                if params_list:
                    short_desc = "\n".join(
                        [li.get_text(strip=True) for li in params_list.find_all("li")]
                    )
            product_data["Krátky popis"] = short_desc

            long_desc_parts = []
            article_section = soup.find(
                "section", class_=lambda x: x and "article_module" in x
            )
            if article_section:
                for section in article_section.find_all("section"):
                    h3 = section.find("h3")
                    if h3:
                        heading_text = h3.get_text(strip=True)
                        long_desc_parts.append(heading_text)
                        content_div = section.getText(strip=True)
                        if content_div.startswith(heading_text):
                            direct_content = content_div[len(heading_text) :].strip()
                        else:
                            direct_content = content_div

                        direct_content = direct_content.replace("\xa0", " ").replace(
                            "&nbsp;", " "
                        )
                        if direct_content:
                            long_desc_parts.append(direct_content)
            product_data["Dlhý popis"] = "\n\n".join(long_desc_parts)

            image_urls = []
            gallery = soup.find("div", id="productGallery")
            if gallery:
                for img_link in gallery.find_all("a"):
                    href = img_link.get("href")
                    if href and "/data/sharedfiles/obrazky/produkty/pFull/" in href:
                        image_urls.append(urljoin(self.base_url, href))
            product_data["Obrázky"] = ",".join(list(set(image_urls)))

            category_div = soup.find("div", class_="category")
            if category_div:
                category_links = category_div.find_all("a")
                if category_links:
                    last_category_link = category_links[-1]
                    category_url = last_category_link.get("href")
                    if category_url == "/e-shop/mystyle":
                        return None
                    product_data["Hlavna kategória"] = self.map_category(category_url)
                else:
                    product_data["Hlavna kategória"] = ""
            else:
                return None

            product_data["Viditeľný"] = "1"
            return product_data
        except Exception as e:
            logger.error(f"Error extracting details from {url}: {e}")
            return None

    def map_category(self, category_url):
        # Check if mapping exists in manager's cache
        mapped_category = self.category_manager.find_mapping(category_url)
        if mapped_category:
            return mapped_category

        # No mapping found - use interactive callback if provided
        if self.category_mapping_callback:
            logger.info(
                f"Requesting interactive mapping for category URL: {category_url}"
            )
            product_name = getattr(self, "current_product_name", None)
            new_category = self.category_mapping_callback(category_url, product_name)
            if new_category and new_category != category_url:
                # Add to manager's cache immediately
                self.category_manager.add_mapping(category_url, new_category)
                return new_category

        logger.warning(f"No mapping found for category URL: {category_url}")
        return category_url

    def scrape_all_products(self):
        self._log_progress("Starting scraping process...")
        category_links = self.get_category_links()
        self._log_progress(f"Found {len(category_links)} categories to scrape.")
        product_urls = []
        for i, link in enumerate(category_links):
            self._log_progress(f"Scraping category {i+1}/{len(category_links)}: {link}")
            product_urls.extend(self.get_product_urls(link))
        unique_urls = list(set(product_urls))
        self._log_progress(f"Found {len(unique_urls)} unique product URLs.")
        products_data = []
        for i, url in enumerate(unique_urls):
            self._log_progress(f"Scraping product {i+1}/{len(unique_urls)}: {url}")
            data = self.extract_product_details(url)
            if data:
                products_data.append(data)
            time.sleep(self.config.REQUEST_DELAY_MIN)
        return pd.DataFrame(products_data)


class FastTopchladenieScraper(TopchladenieScraper):
    """Multi-threaded scraper for topchladenie.sk"""

    def __init__(
        self,
        base_url="https://www.topchladenie.sk",
        max_workers=8,
        progress_callback=None,
        category_manager=None,
        category_mapping_callback=None,
    ):
        super().__init__(
            base_url,
            progress_callback=progress_callback,
            category_manager=category_manager,
            category_mapping_callback=category_mapping_callback,
        )
        self.max_workers = min(max_workers, ScrapingConfig.MAX_THREADS)
        self.lock = Lock()

    def scrape_all_products(self):
        self._log_progress("Starting fast scraping...")
        category_links = self.get_category_links()
        self._log_progress(f"Found {len(category_links)} categories.")

        all_product_urls = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            with tqdm(total=len(category_links), desc="Discovering Products") as pbar:
                future_to_url = {
                    executor.submit(self.get_product_urls, url): url
                    for url in category_links
                }
                for future in as_completed(future_to_url):
                    try:
                        urls = future.result()
                        all_product_urls.extend(urls)
                        pbar.update(1)
                    except Exception as e:
                        logger.error(f"Error getting product URLs: {e}")

        unique_urls = list(set(all_product_urls))
        self._log_progress(f"Found {len(unique_urls)} unique product URLs to scrape.")

        scraped_products = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            with tqdm(total=len(unique_urls), desc="Scraping Products") as pbar:
                future_to_product = {
                    executor.submit(self.extract_product_details, url): url
                    for url in unique_urls
                }
                for future in as_completed(future_to_product):
                    try:
                        product_data = future.result()
                        if product_data:
                            with self.lock:
                                scraped_products.append(product_data)
                    except Exception as e:
                        logger.error(f"Error scraping product task: {e}")
                    pbar.update(1)
                    self._log_progress(f"Scraping progress: {pbar.n}/{pbar.total}")

        return pd.DataFrame(scraped_products)


def get_scraped_products(
    progress_callback=None,
    use_fast_scraper=True,
    category_manager=None,
    category_mapping_callback=None,
) -> pd.DataFrame:
    try:
        logger.info("Starting to scrape products from topchladenie.sk")
        if use_fast_scraper:
            scraper = FastTopchladenieScraper(
                progress_callback=progress_callback,
                category_manager=category_manager,
                category_mapping_callback=category_mapping_callback,
            )
        else:
            scraper = TopchladenieScraper(
                progress_callback=progress_callback,
                category_manager=category_manager,
                category_mapping_callback=category_mapping_callback,
            )
        products_df = clean_data(scraper.scrape_all_products())
        logger.info(f"Successfully scraped {len(products_df)} products")
        return products_df
    except Exception as e:
        logger.error(f"Error during scraping process: {e}")
        return pd.DataFrame()


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("")

        if col in ["Krátky popis", "Dlhý popis"]:
            df[col] = df[col].apply(
                lambda x: (
                    x.replace("\r\n", "\n").replace("\r", "\n")
                    if isinstance(x, str)
                    else x
                )
            )

    # Handle duplicate catalog numbers by updating prices
    if "Kat. číslo" in df.columns:
        duplicates = df[df.duplicated(subset=["Kat. číslo"], keep=False)]
        if not duplicates.empty:
            logger.warning(
                f"Found {len(duplicates)} products with duplicate catalog numbers"
            )
            logger.warning(
                f"Duplicate catalog numbers: {duplicates['Kat. číslo'].unique().tolist()}"
            )

            # For each duplicate catalog number, update the first occurrence's price with the last occurrence's price
            if "Bežná cena" in df.columns:
                for kat_cislo in duplicates["Kat. číslo"].unique():
                    # Get all rows with this catalog number
                    mask = df["Kat. číslo"] == kat_cislo
                    duplicate_rows = df[mask]

                    if len(duplicate_rows) > 1:
                        # Get the first index (original product)
                        first_idx = duplicate_rows.index[0]
                        # Get the last price (from the most recent duplicate)
                        last_price = duplicate_rows.iloc[-1]["Bežná cena"]

                        # Update the first occurrence's price
                        df.at[first_idx, "Bežná cena"] = last_price
                        logger.info(f"Updated price for '{kat_cislo}' to {last_price}")

            # Now remove duplicate entries, keeping only the first occurrence
            df = df.drop_duplicates(subset=["Kat. číslo"], keep="first")
            logger.info(f"Removed duplicates, kept {len(df)} unique products")

    return df
