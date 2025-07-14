#!/usr/bin/env python3
"""
Performance test comparing single-threaded vs multi-threaded scraping
"""

import time
import pandas as pd
from scraping import TopchladenieScraper, FastTopchladenieScraper

def test_performance_comparison():
    """Test performance difference between single-threaded and multi-threaded scrapers"""
    
    print("=== Threading Performance Test ===\n")
    
    # Test URLs - a small sample for quick comparison
    test_urls = [
        "https://www.topchladenie.sk/e-shop/liebherr-cbnsdc-765i-prime",
        "https://www.topchladenie.sk/e-shop/liebherr-zkes-453",
        "https://www.topchladenie.sk/e-shop/liebherr-kgn-52vd03-pure",
        "https://www.topchladenie.sk/e-shop/liebherr-cbnbda-572i-plus",
        "https://www.topchladenie.sk/e-shop/liebherr-cbnc-5723-plus"
    ]
    
    print(f"Testing with {len(test_urls)} products\n")
    
    # Test 1: Original single-threaded scraper
    print("🔄 Testing Original Single-Threaded Scraper...")
    original_scraper = TopchladenieScraper()
    
    start_time = time.time()
    original_results = []
    
    for i, url in enumerate(test_urls):
        print(f"  Processing {i+1}/{len(test_urls)}: {url.split('/')[-1]}")
        try:
            product_data = original_scraper.extract_product_details(url)
            original_results.append(product_data)
        except Exception as e:
            print(f"    Error: {str(e)}")
        
        # Small delay to be polite to the server
        time.sleep(0.5)
    
    original_time = time.time() - start_time
    original_df = pd.DataFrame(original_results) if original_results else pd.DataFrame()
    
    print(f"✅ Original scraper completed in {original_time:.2f} seconds")
    print(f"   Successfully scraped {len(original_results)} products\n")
    
    # Test 2: New multi-threaded scraper
    print("⚡ Testing New Multi-Threaded Scraper...")
    
    # Test with different thread counts
    thread_counts = [2, 4, 8]
    
    for threads in thread_counts:
        print(f"  Testing with {threads} threads...")
        fast_scraper = FastTopchladenieScraper(max_workers=threads)
        
        start_time = time.time()
        threaded_df = fast_scraper.scrape_products_threaded(test_urls, show_progress=True)
        threaded_time = time.time() - start_time
        
        speedup = original_time / threaded_time if threaded_time > 0 else 0
        
        print(f"    ✅ Completed in {threaded_time:.2f} seconds")
        print(f"    📈 Speedup: {speedup:.2f}x faster")
        print(f"    📊 Successfully scraped {len(threaded_df)} products")
        print()
    
    # Results summary
    print("=" * 50)
    print("🎯 PERFORMANCE SUMMARY")
    print("=" * 50)
    print(f"Original (single-threaded): {original_time:.2f} seconds")
    
    # Test optimal configuration
    optimal_scraper = FastTopchladenieScraper(max_workers=8)
    start_time = time.time()
    optimal_df = optimal_scraper.scrape_products_threaded(test_urls, show_progress=False)
    optimal_time = time.time() - start_time
    optimal_speedup = original_time / optimal_time if optimal_time > 0 else 0
    
    print(f"Threaded (8 workers):       {optimal_time:.2f} seconds")
    print(f"Performance improvement:     {optimal_speedup:.2f}x faster")
    print(f"Time saved:                  {original_time - optimal_time:.2f} seconds")
    
    # Data quality check
    print("\n📋 DATA QUALITY CHECK")
    print("-" * 30)
    if not original_df.empty and not optimal_df.empty:
        print(f"Original data shape: {original_df.shape}")
        print(f"Threaded data shape: {optimal_df.shape}")
        
        # Check if we got the same products
        if len(original_df) == len(optimal_df):
            print("✅ Same number of products scraped")
        else:
            print("⚠️  Different number of products scraped")
            
        # Check data completeness
        original_complete = original_df.dropna().shape[0]
        threaded_complete = optimal_df.dropna().shape[0]
        print(f"Original complete records: {original_complete}/{len(original_df)}")
        print(f"Threaded complete records: {threaded_complete}/{len(optimal_df)}")
    
    print("\n🎉 Threading performance test completed!")
    print(f"💡 Recommendation: Use FastTopchladenieScraper with 8 threads for optimal performance")

if __name__ == "__main__":
    try:
        test_performance_comparison()
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
