#!/usr/bin/env python3
"""CLI interface for the topchladenie.sk scraper."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrapers.topchladenie_scraper import TopchladenieScraper

OUTPUT_CSV = "topchladenie_products.csv"


def load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent / "config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def ask_thread_count() -> int:
    while True:
        raw = input("Enter number of threads (default 8, max 16): ").strip()
        if not raw:
            return 8
        try:
            return int(raw)  # BaseScraper clamps to [1, 16]
        except ValueError:
            print("Please enter a valid number.")


def run_scraper(max_threads: int, category_urls=None):
    scraper = TopchladenieScraper(config=load_config(), max_threads=max_threads)

    start_time = time.time()
    df = scraper.scrape_products(category_urls=category_urls)
    elapsed = time.time() - start_time

    if df.empty:
        print("❌ No products found.")
        return

    print(f"\n✅ Completed in {elapsed:.2f} seconds")
    print(f"Scraped {len(df)} products with {max_threads} thread(s)")
    df.to_csv(OUTPUT_CSV, sep=";", index=False, encoding="utf-8")
    print(f"Data saved to {OUTPUT_CSV}")


def run_custom_categories():
    print("\n🎯 Custom Categories Scraper...")
    print("Enter category URLs (one per line, empty line to finish):")

    custom_categories = []
    while True:
        url = input().strip()
        if not url:
            break
        if url.startswith("http"):
            custom_categories.append(url)
        else:
            print("Please enter a valid URL starting with http")

    if not custom_categories:
        print("No custom categories provided.")
        return

    run_scraper(ask_thread_count(), category_urls=custom_categories)


def interactive_scraper():
    print("\n=== Topchladenie.sk Product Scraper ===")
    print("1. Threaded Scraper (Recommended)")
    print("2. Single-Threaded Scraper")
    print("3. Custom Categories with Threading")
    print("4. Exit")

    while True:
        try:
            choice = input("\nSelect an option (1-4): ").strip()

            if choice == "4":
                print("Goodbye!")
                break
            elif choice == "2":
                run_scraper(max_threads=1)
            elif choice == "3":
                run_custom_categories()
            else:
                run_scraper(ask_thread_count())

        except KeyboardInterrupt:
            print("\n\nScraping interrupted by user.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    interactive_scraper()
