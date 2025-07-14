# debug_scraper.py - A tool to debug website structure and content extraction
import requests
from bs4 import BeautifulSoup
import json
import os
import sys

def debug_page_structure(url):
    """Analyze and debug the structure of a webpage"""
    print(f"Analyzing URL: {url}")
    
    try:
        # Fetch the page with standard headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Connection': 'keep-alive'
        }
        
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('Content-Type', 'Unknown')}")
        print(f"Encoding: {response.encoding}")
        
        # Check if the page loaded successfully
        if response.status_code != 200:
            print(f"Error: Failed to load page with status code {response.status_code}")
            return
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Basic page structure
        print("\n=== BASIC PAGE STRUCTURE ===")
        print(f"Title: {soup.title.string if soup.title else 'No title found'}")
        print(f"Meta description: {soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else 'No meta description found'}")
        
        # Extract product details for Liebherr products
        print("\n=== PRODUCT DETAILS ===")
        
        # 1. Product name
        product_name_candidates = [
            soup.find('h1'),
            soup.find('h1', attrs={'itemprop': 'name'}),
            soup.select_one('.product-title'),
            soup.select_one('.product-name')
        ]
        
        product_name = None
        for candidate in product_name_candidates:
            if candidate and candidate.text.strip():
                product_name = candidate.text.strip()
                print(f"Product name: {product_name}")
                print(f"Source: {candidate.name} {dict(candidate.attrs) if candidate.attrs else ''}")
                break
        
        if not product_name:
            print("Product name not found")
        
        # 2. Price
        price_candidates = [
            soup.select_one('.price'),
            soup.select_one('p.price'),
            soup.select_one('.prices .price'),
            soup.select_one('.product-detail .price')
        ]
        
        price = None
        for candidate in price_candidates:
            if candidate and candidate.text.strip():
                price = candidate.text.strip()
                print(f"Price: {price}")
                print(f"Source: {candidate.name} {dict(candidate.attrs) if candidate.attrs else ''}")
                break
                
        if not price:
            print("Price not found in standard elements")
            # Look for any element containing currency symbol
            for elem in soup.find_all(['p', 'div', 'span']):
                if '€' in elem.text:
                    print(f"Possible price text: {elem.text.strip()}")
                    print(f"Source: {elem.name} {dict(elem.attrs) if elem.attrs else ''}")
        
        # 3. Short description / parameters
        print("\n=== PRODUCT PARAMETERS ===")
        params_heading = soup.find(['h2', 'h3'], string=lambda t: t and ('Hlavní parametre' in t or 'Hlavné parametre' in t or 'Parametre' in t))
        
        if params_heading:
            print(f"Parameters heading found: {params_heading.text}")
            print(f"Source: {params_heading.name} {dict(params_heading.attrs) if params_heading.attrs else ''}")
            
            # Look for list items
            params_list = params_heading.find_next('ul')
            if params_list:
                print("Parameters found in list:")
                for li in params_list.find_all('li'):
                    print(f"  - {li.text.strip()}")
            else:
                print("No parameter list found, showing next sibling elements:")
                next_elem = params_heading.next_sibling
                count = 0
                while next_elem and count < 5:
                    if hasattr(next_elem, 'name') and next_elem.name:
                        print(f"  Element: {next_elem.name} - {next_elem.text.strip() if hasattr(next_elem, 'text') else 'No text'}")
                    count += 1
                    next_elem = next_elem.next_sibling
        else:
            print("Parameters heading not found")
        
        # 4. Images
        print("\n=== PRODUCT IMAGES ===")
        gallery = soup.select_one('#productGallery, .product-gallery, .gallery')
        
        if gallery:
            print(f"Gallery found: {gallery.name} {dict(gallery.attrs) if gallery.attrs else ''}")
            
            # Check for links with image extensions
            image_links = [a['href'] for a in gallery.find_all('a') if a.get('href') and any(ext in a['href'].lower() for ext in ['.jpg', '.jpeg', '.png', '.gif'])]
            if image_links:
                print(f"Found {len(image_links)} image links:")
                for url in image_links[:3]:  # Show first 3 only
                    print(f"  {url}")
                if len(image_links) > 3:
                    print(f"  ... and {len(image_links) - 3} more")
            
            # Check for img tags
            images = [img['src'] for img in gallery.find_all('img') if img.get('src')]
            if images:
                print(f"Found {len(images)} image sources:")
                for url in images[:3]:  # Show first 3 only
                    print(f"  {url}")
                if len(images) > 3:
                    print(f"  ... and {len(images) - 3} more")
        else:
            print("No product gallery found")
            
            # Check for other image containers
            product_images = soup.select('.product-image, .main-image, img[itemprop="image"]')
            if product_images:
                print(f"Found {len(product_images)} product images:")
                for img in product_images[:3]:
                    print(f"  {img.get('src')}")
                    print(f"  Source: {img.name} {dict(img.attrs) if img.attrs else ''}")
                if len(product_images) > 3:
                    print(f"  ... and {len(product_images) - 3} more")
        
        # 5. Full HTML structure dump (truncated)
        print("\n=== PAGE STRUCTURE SUMMARY ===")
        page_structure = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'section']):
            if tag.name.startswith('h') or (tag.get('id') or tag.get('class')):
                if tag.name.startswith('h'):
                    indent = int(tag.name[1]) - 1  # h1 = 0 indent, h2 = 1 indent, etc.
                    text = tag.text.strip()
                    if text:
                        page_structure.append("  " * indent + f"{tag.name}: {text[:50]}")
                elif tag.get('id'):
                    page_structure.append(f"{tag.name}#{tag.get('id')}")
                elif tag.get('class'):
                    page_structure.append(f"{tag.name}.{'.'.join(tag.get('class'))}")
        
        # Print first 50 structure items
        for item in page_structure[:50]:
            print(item)
        if len(page_structure) > 50:
            print(f"... and {len(page_structure) - 50} more elements")
        
    except Exception as e:
        print(f"Error during page analysis: {str(e)}")


if __name__ == "__main__":
    # Use provided URL or default test URL
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.topchladenie.sk/e-shop/liebherr-cbnsdc-765i-prime"
    debug_page_structure(url)
