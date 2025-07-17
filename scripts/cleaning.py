# cleaning.py
# Script to read both feeds and clean them of extra data
# Only keeps specified fields for each feed

import os
import sys
import requests
import xml.etree.ElementTree as ET
import pandas as pd

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config

# Direct implementation of fetch_xml_feed to ensure proper error handling
def fetch_feed(url):
    """Fetch XML feed from URL and return the root element"""
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



def process_gastromarket(root, output_file):
    """Process GastroMarket feed and extract MENO and KATEGORIA_KOMPLET tags"""
    if root is None:
        return
    
    # Find all PRODUKT elements
    products = root.findall('.//PRODUKT')
    print(f"Found {len(products)} products in GastroMarket feed")
    
    # Create a list to hold the cleaned data
    cleaned_data = []
    
    # Extract required fields
    for product in products:
        category_element = product.find('KATEGORIA_KOMPLET')
        
        category = category_element.text.strip() if category_element is not None and category_element.text else ""
        
        if category and not any(item.get('category') == category for item in cleaned_data):
            cleaned_data.append({
                'category': category
            })
    
    # Convert to DataFrame and save as CSV
    df = pd.DataFrame(cleaned_data)
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Saved {len(df)} GastroMarket products to {output_file}")

def process_forgastro(root, output_file):
    """Process Forgastro feed and extract product_name and category tags"""
    if root is None:
        return
    
    # Find all product elements
    products = root.findall('.//product')
    print(f"Found {len(products)} products in Forgastro feed")
    
    # Create a list to hold the cleaned data
    cleaned_data = []
    
    # Extract required fields
    for product in products:
        category_element = product.find('category')
        
        category = category_element.text.strip() if category_element is not None and category_element.text else ""
        
        if category and not any(item.get('category') == category for item in cleaned_data):
            cleaned_data.append({
                'category': category
            })
    
    # Convert to DataFrame and save as CSV
    df = pd.DataFrame(cleaned_data)
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Saved {len(df)} Forgastro products to {output_file}")

def process_csv_file(input_file, output_file):
    """Process main CSV file and extract name and category columns"""
    try:
        print(f"Processing CSV file: {input_file}")
        df = pd.read_csv(input_file, encoding='cp1250', sep=';')
        
        # Check if required columns exist
        if "Názov tovaru" not in df.columns or "Hlavna kategória" not in df.columns:
            print(f"Error: Required columns not found in {input_file}")
            print(f"Available columns: {df.columns.tolist()}")
            return False
        
        # Extract required columns
        filtered_df = df[["Hlavna kategória"]].drop_duplicates().copy()
        
        # Rename columns to match our standard format
        filtered_df.rename(columns={"Hlavna kategória": "category"}, inplace=True)
        
        # Save to CSV
        filtered_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved {len(filtered_df)} rows to {output_file}")
        return True
        
    except Exception as e:
        print(f"Error processing CSV file {input_file}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to process both feeds and generate clean CSV files"""
    # Load configuration
    try:
        config = load_config()
        print("Config loaded successfully")
    except Exception as e:
        print(f"Error loading config: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Check if feeds are configured
    if 'xml_feeds' not in config or 'gastromarket' not in config['xml_feeds'] or 'forgastro' not in config['xml_feeds']:
        print("Required feed configurations not found")
        return
    
    # Process GastroMarket feed
    gastromarket_config = config['xml_feeds']['gastromarket']
    gastromarket_url = gastromarket_config['url']
    gastromarket_output = "scripts/gastromarket.csv"
    
    # Fetch XML directly from URL
    gastromarket_root = fetch_feed(gastromarket_url)
    
    # Process GastroMarket data and save to CSV
    process_gastromarket(gastromarket_root, gastromarket_output)
    
    # Process Forgastro feed
    forgastro_config = config['xml_feeds']['forgastro']
    forgastro_url = forgastro_config['url']
    forgastro_output = "scripts/forgastro.csv"
    
    # Fetch XML directly from URL
    forgastro_root = fetch_feed(forgastro_url)
    
    # Process Forgastro data and save to CSV
    process_forgastro(forgastro_root, forgastro_output)
    
    # Check if main CSV file exists and process it
    main_csv_file = "scripts/additional categories export.csv"
    filtered_output = "scripts/gastropro additional.csv"
    csv_processed = False
    
    if os.path.exists(main_csv_file):
        print(f"\nFound main CSV file: {main_csv_file}")
        csv_processed = process_csv_file(main_csv_file, filtered_output)
    
    print("\nCleaning process completed successfully!")
    print(f"Output files: {gastromarket_output}, {forgastro_output}")
    
    if csv_processed:
        print(f", {filtered_output}")
    else:
        print(f"\nNote: {main_csv_file} was not found or could not be processed.")
    

if __name__ == "__main__":
    main()
