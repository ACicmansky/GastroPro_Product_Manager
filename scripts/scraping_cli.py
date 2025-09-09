#!/usr/bin/env python3
"""
CLI interface for the topchladenie.sk scraper
Separated from main scraping.py for better modularity
"""

import time
from src.services.scraper import TopchladenieScraper, FastTopchladenieScraper, save_to_csv, get_scraped_products


def interactive_scraper():
    """Interactive CLI for running the scraper"""
    print("\n=== Topchladenie.sk Product Scraper ===")
    print("1. Fast Threaded Scraper (Recommended)")
    print("2. Original Single-Threaded Scraper")
    print("3. Custom Categories with Threading")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nSelect an option (1-4): ").strip()
            
            if choice == "4":
                print("Goodbye!")
                break
                
            elif choice == "1":
                run_fast_scraper()
                
            elif choice == "2":
                run_original_scraper()
                
            elif choice == "3":
                run_custom_categories()
                
            else:
                run_fast_scraper()
                
        except KeyboardInterrupt:
            print("\n\nScraping interrupted by user.")
            break
        except Exception as e:
            print(f"An error occurred: {str(e)}")


def run_fast_scraper():
    """Run the fast threaded scraper"""
    print("\n🚀 Starting Fast Threaded Scraper...")
    
    try:
        # Get thread count from user
        while True:
            try:
                threads = input("Enter number of threads (default 8, max 16): ").strip()
                if not threads:
                    threads = 8
                else:
                    threads = int(threads)
                    if threads > 16:
                        threads = 16
                        print("Limited to 16 threads for server politeness")
                break
            except ValueError:
                print("Please enter a valid number.")
        
        scraper = FastTopchladenieScraper(max_workers=threads)
        
        print(f"Using {threads} threads for concurrent scraping...")
        start_time = time.time()
        
        df = get_scraped_products(use_fast_scraper=True, progress_callback=lambda x: print(x))
        
        end_time = time.time()
        
        if not df.empty:
            print(f"\n✅ Completed in {end_time - start_time:.2f} seconds")
            print(f"Scraped {len(df)} products with {threads} threads")
            save_to_csv(df)
            print("Data saved to topchladenie_products.csv")
        else:
            print("❌ No products found.")
            
    except Exception as e:
        print(f"❌ Error in fast scraper: {str(e)}")


def run_original_scraper():
    """Run the original single-threaded scraper"""
    print("\n🐌 Starting Original Single-Threaded Scraper...")
    
    try:
        scraper = TopchladenieScraper()
        
        start_time = time.time()
        df = scraper.scrape_all_products()
        end_time = time.time()
        
        if not df.empty:
            print(f"\n✅ Completed in {end_time - start_time:.2f} seconds")
            print(f"Scraped {len(df)} products")
            save_to_csv(df)
            print("Data saved to topchladenie_products.csv")
        else:
            print("❌ No products found.")
            
    except Exception as e:
        print(f"❌ Error in original scraper: {str(e)}")


def run_custom_categories():
    """Run scraper with custom category URLs"""
    print("\n🎯 Custom Categories Scraper...")
    print("Enter category URLs (one per line, empty line to finish):")
    
    custom_categories = []
    while True:
        url = input().strip()
        if not url:
            break
        if url.startswith('http'):
            custom_categories.append(url)
        else:
            print("Please enter a valid URL starting with http")
    
    if custom_categories:
        try:
            scraper = FastTopchladenieScraper()
            
            start_time = time.time()
            df = scraper.scrape_categories_threaded(custom_categories)
            end_time = time.time()
            
            if not df.empty:
                print(f"\n✅ Completed in {end_time - start_time:.2f} seconds")
                print(f"Scraped {len(df)} products from {len(custom_categories)} custom categories")
                save_to_csv(df)
                print("Data saved to topchladenie_products.csv")
            else:
                print("❌ No products found in custom categories.")
                
        except Exception as e:
            print(f"❌ Error in custom categories scraper: {str(e)}")
    else:
        print("No custom categories provided.")


if __name__ == "__main__":
    interactive_scraper()
