"""
Test script for Mebella pagination using Playwright.
"""

import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.scrapers.mebella_scraper import MebellaScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_pagination():
    scraper = MebellaScraper()
    category_url = "https://mebella.pl/en/product-category/table-bases/flat-en/"

    logger.info(f"Testing pagination for: {category_url}")
    product_urls = scraper.get_product_urls(category_url)

    logger.info(f"Found {len(product_urls)} product URLs:")
    for url in product_urls:
        logger.info(f"  - {url}")


if __name__ == "__main__":
    test_pagination()
