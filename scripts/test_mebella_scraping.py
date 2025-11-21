import logging
import sys
import os
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.scrapers.mebella_scraper import MebellaScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_scraper():
    config = {}  # No specific config needed for now
    scraper = MebellaScraper(config)

    logger.info("Testing get_category_links...")
    cat_links = scraper.get_category_links()
    logger.info(f"Category links: {cat_links}")

    logger.info("Testing get_product_urls (page 1 only)...")

    test_product_url = "https://mebella.pl/en/produkt/bea-big-dining/"
    logger.info(f"Testing scrape_product_detail for {test_product_url}...")
    product_data = scraper.scrape_product_detail(test_product_url)

    if product_data:
        logger.info("Product Data:")
        logger.info(json.dumps(product_data, indent=2, ensure_ascii=False))
    else:
        logger.error("Failed to scrape product data.")

    logger.info("Fetching products from first category link...")

    response = scraper.session.get(cat_links[0])
    if response.status_code == 200:
        logger.info("Successfully accessed category page.")
    else:
        logger.error(f"Failed to access category page: {response.status_code}")


if __name__ == "__main__":
    test_scraper()
