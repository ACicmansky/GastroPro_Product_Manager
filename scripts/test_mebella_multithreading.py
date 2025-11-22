"""
Demo script showing single vs multi-threaded MebellaScraper execution.
"""

import sys
import os
import logging
import json
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.scrapers.mebella_scraper import MebellaScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_scraper(max_threads: int):
    """Test scraper with specified thread count."""
    logger.info(f"\\n{'='*60}")
    logger.info(f"Testing with max_threads={max_threads}")
    logger.info(f"{'='*60}")

    scraper = MebellaScraper(max_threads=max_threads)

    # Test with a small number of products
    test_urls = [
        "https://mebella.pl/en/produkt/bea-big-dining/",
        "https://mebella.pl/en/produkt/yeti-bar/",
        "https://mebella.pl/en/produkt/cone-round/",
    ]

    logger.info(f"Scraping {len(test_urls)} products...")
    start_time = time.time()

    results = []
    for url in test_urls:
        data = scraper.scrape_product_detail(url)
        if data:
            results.append(data)

    elapsed = time.time() - start_time

    logger.info(f"\\nCompleted in {elapsed:.2f} seconds")
    logger.info(f"Successfully scraped {len(results)} products")
    logger.info(f"Average: {elapsed/len(results):.2f} seconds/product\\n")

    return elapsed, results


if __name__ == "__main__":
    print("\\n" + "=" * 60)
    print("MEBELLA SCRAPER - MULTITHREADING DEMO")
    print("=" * 60)

    # Test single-threaded
    single_time, single_results = test_scraper(max_threads=1)

    # Test multi-threaded
    multi_time, multi_results = test_scraper(max_threads=4)

    # Show speedup
    speedup = single_time / multi_time if multi_time > 0 else 0

    print("\\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Single-threaded: {single_time:.2f}s")
    print(f"Multi-threaded (4 threads): {multi_time:.2f}s")
    print(f"Speedup: {speedup:.2f}x")
    print("=" * 60)

    # Show a sample product
    if multi_results:
        print("\\nSample product data:")
        print(json.dumps(multi_results[0], indent=2, ensure_ascii=False))
