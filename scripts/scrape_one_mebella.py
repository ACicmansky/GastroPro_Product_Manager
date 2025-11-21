import logging
import sys
import os
import json

# Add project root to path to allow importing src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.scrapers.mebella_scraper import MebellaScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding="utf-8")


def scrape_single_product():
    # Target URL - BEA BIG DINING (English)
    url = "https://mebella.pl/en/produkt/bea-big-dining/"

    logger.info(f"Initializing MebellaScraper...")
    scraper = MebellaScraper(config={})

    logger.info(f"Scraping product: {url}")

    # TEST FIX: Add language cookie explicitly in headers
    scraper.session.headers.update(
        {"Cookie": "pll_language=en; wp-wpml_current_language=en"}
    )

    # Save HTML for inspection
    try:
        response = scraper.session.get(url)
        with open("bea_debug.html", "wb") as f:
            f.write(response.content)
        logger.info("Saved bea_debug.html")
    except Exception as e:
        logger.error(f"Error saving HTML: {e}")

    # Save HTML for inspection
    try:
        response = scraper.session.get(url)
        with open("bea_debug.html", "wb") as f:
            f.write(response.content)
        logger.info("Saved bea_debug.html")
    except Exception as e:
        logger.error(f"Error saving HTML: {e}")

    product_data = scraper.scrape_product_detail(url)

    if product_data:
        logger.info("Successfully scraped product data:")
        print(json.dumps(product_data, indent=2, ensure_ascii=False))
    else:
        logger.error("Failed to scrape product data (returned None).")


if __name__ == "__main__":
    scrape_single_product()
