# categories.py
# Script to load GastroMarket and Forgastro feeds and display all unique category fields
# with the number of products for each category

import os
import sys
import traceback
import requests
from collections import Counter
import xml.etree.ElementTree as ET
from datetime import datetime

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config

# Direct implementation of fetch_xml_feed to ensure we see all errors
def fetch_feed(url):
    print(f"Fetching XML feed from {url}...")
    try:
        response = requests.get(url, timeout=60)
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            return None
            
        # Try to parse the XML
        try:
            root = ET.fromstring(response.content)
            return root
        except ET.ParseError as e:
            print(f"XML parsing error: {e}")
            print(f"First 500 chars of content: {response.content[:500]}")
            return None
            
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return None



def process_feed(feed_name, config, output_lines):
    """Process a single feed and return category counts"""
    if feed_name not in config.get('xml_feeds', {}):
        print(f"{feed_name} feed not found in configuration")
        return Counter()
    
    feed_config = config['xml_feeds'][feed_name]
    url = feed_config['url']
    root_element = feed_config['root_element']
    mapping = feed_config['mapping']
    
    print(f"Processing {feed_name} feed with root element: {root_element}")
    
    # Fetch XML from URL
    try:
        print(f"Fetching {feed_name} from URL...")
        root = fetch_feed(url)
    except Exception as e:
        print(f"Error fetching {feed_name} feed: {e}")
        traceback.print_exc()
        return Counter()
    
    if root is None:
        print(f"Failed to get XML data for {feed_name} from any source")
        return Counter()
    
    try:
        # Extract all products
        products = root.findall(f".//{root_element}")
        product_count = len(products)
        print(f"Found {product_count} products in {feed_name} feed")
        
        if product_count == 0:
            print(f"No products found with element tag '{root_element}'")
            print(f"Available root tags: {[elem.tag for elem in root[:5]]}...")
            return Counter()
        
        # Determine the category field name based on feed
        category_field = 'KATEGORIA_KOMPLET' if feed_name == 'gastromarket' else 'category'
        
        # Extract and count categories
        category_counts = Counter()
        for i, product in enumerate(products):
            if i == 0:  # Print first product's tags for debugging
                print(f"First {feed_name} product tags: {[elem.tag for elem in product]}")
                
            category_element = product.find(category_field)
            if category_element is not None and category_element.text:
                category = category_element.text.strip()
                category_counts[category] += 1
        
        if not category_counts:
            print(f"No categories found in {feed_name} products")
            return Counter()
        
        # Sort categories by name and add to output
        sorted_categories = sorted(category_counts.items())
        output_lines.append(f"\n{feed_name.upper()}:")
        
        for category, count in sorted_categories:
            line = f"{category}, {count}"
            output_lines.append(line)
            
        output_lines.append(f"\n{feed_name}: {len(sorted_categories)} categories, {sum(category_counts.values())} products\n")
        
        return category_counts
        
    except Exception as e:
        print(f"Error processing {feed_name} feed: {e}")
        traceback.print_exc()
        return Counter()

def main():
    # Load configuration
    try:
        config = load_config()
        print("Config loaded successfully")
    except Exception as e:
        print(f"Error loading config: {e}")
        traceback.print_exc()
        return
    
    # Output lines to be saved to file
    output_lines = ["CATEGORY ANALYSIS REPORT\n", f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
    
    # Process each feed
    gastromarket_counts = process_feed('gastromarket', config, output_lines)
    forgastro_counts = process_feed('forgastro', config, output_lines)
    
    # Add summary of all feeds
    total_categories = len(gastromarket_counts) + len(forgastro_counts)
    total_products = sum(gastromarket_counts.values()) + sum(forgastro_counts.values())
    output_lines.append(f"\nGRAND TOTAL: {total_categories} categories, {total_products} products")
    
    # Save to file
    output_file = "scripts/categories.txt"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        print(f"\nResults saved to {output_file}")
    except Exception as e:
        print(f"Error saving to file: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
    print("\nCategory analysis complete! Results have been saved to categories.txt")
