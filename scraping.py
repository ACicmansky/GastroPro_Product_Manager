# scraping.py
import requests
import pandas as pd
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin
import time
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TopchladenieScraper')

class ScrapingConfig:
    """Configuration class for scraping parameters"""
    
    # Request settings
    REQUEST_DELAY_MIN = 0.5
    REQUEST_TIMEOUT = 30
    
    # Threading settings
    DEFAULT_THREADS = 8
    MAX_THREADS = 16
    
    # CSV settings
    CSV_ENCODING = 'utf-8-sig'
    
    # User agent
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

    ULRS_TO_SKIP_DURING_GET_PRODUCT_URLS = [
        'https://www.topchladenie.sk/e-shop/samostatne-chladnicky',
        'https://www.topchladenie.sk/e-shop/samostatne-chladnicky/bez-mraznicky-vnutri',
        'https://www.topchladenie.sk/e-shop/samostatne-chladnicky/s-mraznickou-vo-vnutri',
        'https://www.topchladenie.sk/e-shop/chladnicky-s-mraznickou',
        'https://www.topchladenie.sk/e-shop/chladnicky-s-mraznickou/s-mraznickou-hore',
        'https://www.topchladenie.sk/e-shop/chladnicky-s-mraznickou/s-mraznickou-dole',
        'https://www.topchladenie.sk/e-shop/americke-chladnicky',
        'https://www.topchladenie.sk/e-shop/mraznicky',
        'https://www.topchladenie.sk/e-shop/mraznicky/pultove',
        'https://www.topchladenie.sk/e-shop/mraznicky/suplikove',
        'https://www.topchladenie.sk/e-shop/vstavane-spotrebice',
        'https://www.topchladenie.sk/e-shop/vstavane-spotrebice/chladnicky-na-vino',
        'https://www.topchladenie.sk/e-shop/vstavane-spotrebice/mraznicky',
        'https://www.topchladenie.sk/e-shop/vstavane-spotrebice/chladnicky',
        'https://www.topchladenie.sk/e-shop/vstavane-spotrebice/kombinovane-chladnicky',
        'https://www.topchladenie.sk/e-shop/domace-vinoteky',
        'https://www.topchladenie.sk/e-shop/domace-vinoteky/temperovane',
        'https://www.topchladenie.sk/e-shop/domace-vinoteky/klimatizovane',
        'https://www.topchladenie.sk/e-shop/humidory',
        'https://www.topchladenie.sk/e-shop/komercne-zariadenia',
        'https://www.topchladenie.sk/e-shop/komercne-zariadenia/gastro-zariadenie',
        'https://www.topchladenie.sk/e-shop/komercne-zariadenia/pekaren',
        'https://www.topchladenie.sk/e-shop/komercne-zariadenia/napojovy-priemysel',
        'https://www.topchladenie.sk/e-shop/prislusenstvo',
        'https://www.topchladenie.sk/e-shop/mystyle',
        'https://www.topchladenie.sk/e-shop/akcie-a-zavy',
    ]
    
    @classmethod
    def get_headers(cls):
        return {'User-Agent': cls.USER_AGENT}


class TopchladenieScraper:
    """Class for scraping product data from topchladenie.sk website"""
    
    def __init__(self, base_url="https://www.topchladenie.sk", categories_file="categories.json"):
        """Initialize the scraper with base URL and categories mapping file"""
        self.base_url = base_url
        self.categories_file = categories_file
        self.config = ScrapingConfig()
        self.session = requests.Session()
        self.session.headers.update(self.config.get_headers())
        self.session.timeout = self.config.REQUEST_TIMEOUT
        
    def scrape_all_products(self):
        """Main function to scrape all products from the website
        
        Returns:
            pandas.DataFrame: DataFrame containing all scraped products
        """
        logger.info("Starting topchladenie.sk scraping process")
        
        # Get all product URLs
        product_urls = []
        
        # Get category links first
        category_links = self.get_category_links()
        
        # Skip "Akcie a zľavy" category
        category_links = [link for link in category_links if "akcie-a-zlavy" not in link]
        
        logger.info(f"Found {len(category_links)} categories to scrape")
        
        # For each category, get product URLs
        for category_url in category_links:
            try:
                category_product_urls = self.get_product_urls(category_url)
                product_urls.extend(category_product_urls)
                logger.info(f"Found {len(category_product_urls)} products in category {category_url}")
                
                # Respect the website by adding a small delay between requests
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error scraping category {category_url}: {str(e)}")
        
        # Remove duplicates
        product_urls = list(set(product_urls))
        
        logger.info(f"Found {len(product_urls)} unique products")
        
        # Collect all product data first (much faster than repeated DataFrame concat)
        products_data = []
        
        # For each product, extract details
        for i, url in enumerate(product_urls):
            try:
                logger.info(f"Scraping product {i+1}/{len(product_urls)}: {url}")
                product_data = self.extract_product_details(url)
                if product_data:  # Only add if data was extracted successfully
                    product_data['Viditeľný'] = "1"  # Set visibility flag
                    products_data.append(product_data)
                
                # Respect the website by adding a small delay between requests
                time.sleep(self.config.REQUEST_DELAY_MIN)
            except Exception as e:
                logger.error(f"Error extracting data from {url}: {str(e)}")
        
        # Create DataFrame once from all collected data (much faster)
        if products_data:
            df = pd.DataFrame(products_data)
        else:
            # Create empty DataFrame with expected columns if no data
            df = pd.DataFrame(columns=[
                'Kat. číslo', 'Názov tovaru', 'Bežná cena', 'Výrobca',
                'Krátky popis', 'Dlhý popis', 'Obrázky', 'Hlavna kategória', 'Viditeľný'
            ])
        
        logger.info(f"Successfully scraped {len(df)} products")
        return df
    
    def get_category_links(self):
        """Get all category links
        
        Returns:
            list: List of category URLs
        """
        category_links = []
        direct_categories = [
                '/e-shop/samostatne-chladnicky/bez-mraznicky-vnutri',
                '/e-shop/samostatne-chladnicky/s-mraznickou-vo-vnutri',
                '/e-shop/chladnicky-s-mraznickou/s-mraznickou-hore',
                '/e-shop/chladnicky-s-mraznickou/s-mraznickou-dole',
                '/e-shop/americke-chladnicky',
                '/e-shop/mraznicky/pultove',
                '/e-shop/mraznicky/suplikove',
                '/e-shop/vstavane-spotrebice/chladnicky-na-vino',
                '/e-shop/vstavane-spotrebice/mraznicky',
                '/e-shop/vstavane-spotrebice/chladnicky',
                '/e-shop/vstavane-spotrebice/kombinovane-chladnicky',
                '/e-shop/domace-vinoteky/temperovane',
                '/e-shop/domace-vinoteky/klimatizovane',
                '/e-shop/humidory',
                '/e-shop/komercne-zariadenia/gastro-zariadenie',
                '/e-shop/komercne-zariadenia/pekaren',
                '/e-shop/komercne-zariadenia/napojovy-priemysel',
                '/e-shop/prislusenstvo'
            ]
        for cat in direct_categories:
            full_url = urljoin(self.base_url, cat)
            category_links.append(full_url)
        return category_links
    
    def get_product_urls(self, category_url):
        """Get all product URLs from a category page, handling pagination
        
        Args:
            category_url: URL of the category page
            
        Returns:
            list: List of product URLs
        """
        logger.info(f"Finding products in category: {category_url}")
        product_urls = []
        page = 1
        products_found = 0
        max_pages = 20  # Safety limit
        
        while page <= max_pages:
            url = f"{category_url}?page={page}" if page > 1 else category_url
            try:
                logger.info(f"Fetching page {page}: {url}")
                response = self.session.get(url)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try multiple selector strategies to find product links
                selector_strategies = [
                    # Original selectors
                    '.products .product a.image',
                    '.products .product a',
                    # Additional common product selectors
                    '.product-list .item a',
                    '.product-grid .product-item a',
                    '.product-container a',
                    '.product a',
                    '.product-card a',
                    '.item a[href*="/e-shop/"]',
                    'a[href*="/e-shop/"]:not([href*="category"])',
                    'a[href*="/e-shop/"]:not([href*="page"])',
                ]
                
                page_products = []
                for selector in selector_strategies:
                    elements = soup.select(selector)
                    if elements:
                        logger.info(f"Selector '{selector}' found {len(elements)} elements")
                        page_products.extend(elements)
                
                # Process found products
                new_products = 0
                for product in page_products:
                    href = product.get('href')
                    if href and '/e-shop/' in href and not any(x in href for x in ['category', 'stranka', 'page=']):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in product_urls:  # Only add if unique
                            product_urls.append(full_url)
                            new_products += 1
                
                logger.info(f"Found {new_products} new products on page {page}")
                products_found += new_products
                
                # Stop if no new products found on this page
                if new_products == 0:
                    logger.info(f"No new products found on page {page}, stopping pagination")
                    break
                
                # Check for next page using multiple selectors
                has_next = False
                next_selectors = ['a.next', '.pagination a.next', '.pages a[rel="next"]', 
                                '.pagination a:contains("Ďalšia")', '.pagination a:contains("»")']  
                
                for next_selector in next_selectors:
                    next_page = soup.select_one(next_selector)
                    if next_page:
                        has_next = True
                        break
                
                if not has_next and '?page=' not in url:  # Try standard pagination pattern if no next button
                    # Check if page 2 exists by looking for products on that page
                    test_next = f"{category_url}?page={page+1}"
                    test_resp = self.session.get(test_next)
                    test_soup = BeautifulSoup(test_resp.content, 'html.parser')
                    if test_soup.select('.products .product a') or test_soup.select('.product a'):
                        has_next = True
                
                if not has_next:
                    logger.info(f"No next page found after page {page}")
                    break
                
                page += 1
                time.sleep(1.5)  # Add a delay between page requests
                
            except Exception as e:
                logger.error(f"Error processing page {page}: {str(e)}")
                break
        
        unique_urls = list(set(product_urls))  # Ensure no duplicates
        unique_urls = [url for url in unique_urls if url not in self.config.ULRS_TO_SKIP_DURING_GET_PRODUCT_URLS]
        logger.info(f"Found {len(unique_urls)} unique product URLs in category {category_url}")
        return unique_urls
    
    def extract_product_details(self, url):
        """Extract product details from a product page
        
        Args:
            url: URL of the product page
            
        Returns:
            dict: Product data
        """
        product_data = {}
        
        response = self.session.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract product name - first look for h1 tags
        product_name = None
        for selector in ['h1', 'h1[itemprop="name"]', '.product-title', '.product-name']:
            product_name_elem = soup.select_one(selector)
            if product_name_elem and product_name_elem.text.strip():
                product_name = product_name_elem.text.strip()
                break
                
        # If no product name found, try to extract from page title
        if not product_name:
            title_elem = soup.select_one('title')
            if title_elem and title_elem.text.strip():
                product_name = title_elem.text.split('|')[0].strip()
        
        # 1. "Kat. číslo" and "Názov tovaru" - Full product name
        if product_name:
            product_data['Kat. číslo'] = product_data['Názov tovaru'] = product_name
        else:
            return None
        
        # 2. "Bežná cena" - Price
        price_value = 0
        
        # Based on our debugging, we know the actual price is in a p tag with class big red
        price_elem = soup.find('p', class_=['big', 'red'])
        if price_elem and price_elem.get('content'):
            # The content attribute has the raw price
            try:
                price_value = float(price_elem.get('content'))
            except ValueError:
                pass
        
        # If we didn't get the price from the content attribute, try to extract it from the text
        if price_value == 0 and price_elem:
            price_text = price_elem.text.strip()
            # Extract digits and decimal separator
            price_match = re.search(r'(\d+[\s]?\d*[,.]?\d*)\s*€', price_text)
            if price_match:
                try:
                    # Remove spaces, replace comma with dot
                    numeric_price = re.sub(r'[^\d,.]', '', price_match.group(1)).replace(',', '.')
                    price_value = float(numeric_price)
                except ValueError:
                    pass
        
        # If we still don't have a price, try the generic approach
        if price_value == 0:
            # Look for price in the price-wrapper-grid div
            price_wrapper = soup.find('div', class_='price-wrapper-grid')
            if price_wrapper:
                # Find all text with euro symbol
                price_text = price_wrapper.text.strip()
                # Find the main price (usually the second price after "Pôvodne")
                price_matches = re.findall(r'(\d+[\s]?\d*[,.]?\d*)\s*€', price_text)
                if len(price_matches) >= 2:
                    try:
                        # Use the second price (the current price, not the original)
                        numeric_price = re.sub(r'[^\d,.]', '', price_matches[1]).replace(',', '.')
                        price_value = float(numeric_price)
                    except (ValueError, IndexError):
                        pass
                elif price_matches:
                    try:
                        # Just use the first price found
                        numeric_price = re.sub(r'[^\d,.]', '', price_matches[0]).replace(',', '.')
                        price_value = float(numeric_price)
                    except ValueError:
                        pass
        
        # As a last resort, look for any element with a euro symbol
        if price_value == 0:
            for element in soup.find_all(['p', 'div', 'span']):
                if '€' in element.text and not ('DPH' in element.text or 'Pôvodne' in element.text):
                    price_match = re.search(r'(\d+[\s]?\d*[,.]?\d*)\s*€', element.text)
                    if price_match:
                        try:
                            numeric_price = re.sub(r'[^\d,.]', '', price_match.group(1)).replace(',', '.')
                            price_value = float(numeric_price)
                            break
                        except ValueError:
                            continue
        
        # Sanity check for the price
        if price_value > 100000:  # Unrealistically high price
            price_value = 0
            
        product_data['Bežná cena'] = price_value
        
        # 3. "Výrobca" - Set to "Liebherr"
        product_data['Výrobca'] = "Liebherr"
        
        # 4. "Krátky popis" - Short description or parameters
        try:
            short_desc_items = []
            
            # First try to find parameter section with heading (based on debug output)
            param_heading = None
            for heading_text in ['Hlavní parametre', 'Hlavné parametre', 'Parametre', 'Parametre produktu']:
                # Exact match first
                heading = soup.find(['h2', 'h3', 'h4'], string=lambda t: t and t.strip() == heading_text)
                if heading:
                    param_heading = heading
                    break
                    
                # If no exact match, try partial match
                if not param_heading:
                    heading = soup.find(['h2', 'h3', 'h4'], string=lambda t: t and heading_text in t)
                    if heading:
                        param_heading = heading
                        break
            
            if param_heading:
                logger.debug(f"Found parameter heading: {param_heading.text.strip()}")
                # Check if parameters are in a list (we know from debug this is the case)
                param_list = param_heading.find_next('ul')
                if param_list:
                    for li in param_list.find_all('li'):
                        text = li.get_text().strip()
                        if text:
                            short_desc_items.append(text)
                    logger.debug(f"Extracted {len(short_desc_items)} parameters from list")
            
            # If no parameters found via standard heading, try with the actual headings we saw in debug
            if not short_desc_items:
                # Look for any h2/h3/h4 that might contain parameter-like content
                for heading in soup.find_all(['h2', 'h3', 'h4']):
                    heading_text = heading.get_text().strip()
                    if any(keyword in heading_text.lower() for keyword in ['parametre', 'parameter', 'parameter', 'vlastnost', 'detail']):
                        param_list = heading.find_next('ul')
                        if param_list:
                            for li in param_list.find_all('li'):
                                text = li.get_text().strip()
                                if text:
                                    short_desc_items.append(text)
                            if short_desc_items:
                                logger.debug(f"Found parameters under heading: {heading_text}")
                                break
            
            # If still no parameters found through lists, try to extract from structured data
            if not short_desc_items:
                # Try to find any structured parameter data
                structured_data = {}
                # Look for dt/dd pairs (definition lists)
                for dl in soup.find_all('dl'):
                    dts = dl.find_all('dt')
                    dds = dl.find_all('dd')
                    if len(dts) == len(dds):
                        for dt, dd in zip(dts, dds):
                            param = dt.get_text().strip()
                            value = dd.get_text().strip()
                            if param and value:
                                structured_data[param] = value
                
                # Also check for table-based parameters
                for table in soup.find_all('table'):
                    for row in table.find_all('tr'):
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            param = cells[0].get_text().strip()
                            value = cells[1].get_text().strip()
                            if param and value and not param.isspace() and not value.isspace():
                                structured_data[param] = value
                
                # Convert structured data to lines
                for param, value in structured_data.items():
                    short_desc_items.append(f"{param}: {value}")
            
            # If still no parameters found, try direct page scraping as last resort
            if not short_desc_items:
                # Extract parameters from any section with parameter-like text
                for section in soup.find_all(['div', 'section'], class_=lambda c: c and any(kw in str(c).lower() for kw in ['param', 'detail', 'spec', 'info'])):
                    # Extract text lines that look like parameters (X: Y format)
                    text = section.get_text().strip()
                    for line in text.split('\n'):
                        line = line.strip()
                        if ":" in line and len(line) < 100:
                            parts = line.split(":", 1)
                            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                                short_desc_items.append(line)
            
            # Clean up and format the parameters
            clean_items = []
            for item in short_desc_items:
                # Replace excessive whitespace
                item = re.sub(r'\s+', ' ', item).strip()
                # Skip duplicates
                if item and item not in clean_items:
                    clean_items.append(item)
            
            product_data['Krátky popis'] = '\n'.join(clean_items) if clean_items else ""
            logger.info(f"Extracted short description with {len(clean_items)} parameters")
            
        except Exception as e:
            logger.error(f"Error extracting short description for {url}: {str(e)}")
            product_data['Krátky popis'] = ""
        
        # 5. "Dlhý popis" - Equipment section
        try:
            # Find section with class containing 'article_module'
            long_desc_parts = []
            
            # Look for section with class containing 'article_module'
            article_section = soup.find('section', class_=lambda x: x and 'article_module' in x)
            
            if article_section:
                logger.info("Found article_module section for long description")
                
                # Get all sections that contain h3 headings
                all_sections = article_section.find_all('section')
                inner_sections = [section for section in all_sections if section.find('h3')]
                
                logger.info(f"Found {len(inner_sections)} content sections to process")
                
                # Track processed headings to avoid duplicates
                processed_headings = set()
                
                for section in inner_sections:
                    # Extract h3 heading
                    h3_heading = section.find('h3')
                    if h3_heading:
                        heading_text = h3_heading.get_text(strip=True)
                        if heading_text:
                            # Skip if we've already processed this heading
                            if heading_text in processed_headings:
                                logger.info(f"Skipping duplicate heading: {heading_text}")
                                continue
                            
                            # Mark this heading as processed
                            processed_headings.add(heading_text)
                            long_desc_parts.append(heading_text)
                            logger.info(f"Found section heading: {heading_text}")
                    
                    # Try to extract content - handle both structured and direct text cases
                    if h3_heading:
                        content_extracted = False
                        
                        # Case 1: Try to find next div with p tags (structured content)
                        next_div = h3_heading.find_next_sibling('div')
                        if next_div:
                            # Find all p tags within this div
                            paragraphs = next_div.find_all('p')
                            paragraph_texts = []
                            
                            for p in paragraphs:
                                p_text = p.get_text(strip=True)
                                if p_text:
                                    # Replace &nbsp; (\xa0) with regular space
                                    p_text = p_text.replace('\xa0', ' ')
                                    # Also replace HTML entity
                                    p_text = p_text.replace('&nbsp;', ' ')
                                    paragraph_texts.append(p_text)
                            
                            # Join all paragraphs from this section
                            if paragraph_texts:
                                section_content = ' '.join(paragraph_texts)
                                long_desc_parts.append(section_content)
                                logger.info(f"Extracted structured content for {heading_text}: {len(section_content)} characters")
                                content_extracted = True
                        
                        # Case 2: If no structured content found, look for direct text content after h3
                        if not content_extracted:
                            # Get all text content from the section, excluding the h3 heading text
                            section_text = section.get_text(strip=True)
                            if section_text and section_text != heading_text:
                                # Remove the heading text from the beginning if present
                                if section_text.startswith(heading_text):
                                    direct_content = section_text[len(heading_text):].strip()
                                else:
                                    direct_content = section_text
                                
                                if direct_content:
                                    # Clean up the text
                                    direct_content = direct_content.replace('\xa0', ' ')
                                    direct_content = direct_content.replace('&nbsp;', ' ')
                                    long_desc_parts.append(direct_content)
                                    logger.info(f"Extracted direct content for {heading_text}: {len(direct_content)} characters")
                                    content_extracted = True
                        
                        # Log if no content was found for this section
                        if not content_extracted:
                            logger.warning(f"No content found for section: {heading_text}")
                
                # Join all parts with double newlines between sections
                product_data['Dlhý popis'] = '\n\n'.join(long_desc_parts) if long_desc_parts else ""                
                soup = BeautifulSoup(product_data['Dlhý popis'], "html.parser")
                product_data['Dlhý popis'] = soup.get_text()
                
                if long_desc_parts:
                    logger.info(f"Successfully extracted long description with {len(long_desc_parts)} sections")
                else:
                    logger.warning("No content found in article_module sections")
            else:
                logger.warning("No article_module section found for long description")
                product_data['Dlhý popis'] = ""
        except Exception as e:
            logger.error(f"Error extracting long description: {str(e)}")
            product_data['Dlhý popis'] = ""
        
        # 6. "Obrázky" - Image URLs
        try:
            image_urls = []
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Based on debug output, we know product gallery has id='productGallery'
            gallery = soup.find('div', id='productGallery')
            
            if gallery:
                # From debug output, we know the a tags contain links to full size images
                # Look for the /pFull/ links which are the full-size versions
                for img_link in gallery.find_all('a'):
                    href = img_link.get('href')
                    if href and '/data/sharedfiles/obrazky/produkty/pFull/' in href:
                        # Make sure it's an absolute URL
                        image_url = href if href.startswith(('http://', 'https://')) else urljoin(self.base_url, href)
                        image_urls.append(image_url)
                
                # If no pFull images found, use any image links
                if not image_urls:
                    for img_link in gallery.find_all('a'):
                        href = img_link.get('href')
                        if href and any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                            image_url = href if href.startswith(('http://', 'https://')) else urljoin(self.base_url, href)
                            image_urls.append(image_url)
                
                # If still no images found, look for img tags
                if not image_urls:
                    for img in gallery.find_all('img'):
                        src = img.get('src')
                        if src:
                            # Try to convert thumbnail URLs to full size
                            if '/pShow/' in src:
                                full_src = src.replace('/pShow/', '/pFull/')
                                image_url = full_src if full_src.startswith(('http://', 'https://')) else urljoin(self.base_url, full_src)
                            else:
                                image_url = src if src.startswith(('http://', 'https://')) else urljoin(self.base_url, src)
                            image_urls.append(image_url)
            
            # If no gallery found or no images found in gallery, use generic approach
            if not image_urls:
                # Check for product images anywhere on the page
                for img in soup.find_all('img'):
                    src = img.get('src')
                    # Check if it's likely a product image (has "produkt" in path or is large)
                    if src and ('/produkt' in src.lower() or '/obrazky/' in src.lower()):
                        # Try to get the full size version if it's a thumbnail
                        if '/pShow/' in src:
                            full_src = src.replace('/pShow/', '/pFull/')
                            image_url = full_src if full_src.startswith(('http://', 'https://')) else urljoin(self.base_url, full_src)
                        else:
                            image_url = src if src.startswith(('http://', 'https://')) else urljoin(self.base_url, src)
                        image_urls.append(image_url)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in image_urls:
                if url not in seen and url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    seen.add(url)
                    unique_urls.append(url)
            
            product_data['Obrázky'] = ','.join(unique_urls) if unique_urls else ""
            
            # Debug logging for image extraction
            logger.info(f"Extracted {len(unique_urls)} image URLs for product {url}")
        except Exception as e:
            logger.error(f"Error extracting product images from {url}: {str(e)}")
            product_data['Obrázky'] = ""
        
        # 7. "Hlavna kategória" - Last category link
        category_div = soup.find('div', class_='category')
        if category_div:
            category_links = category_div.find_all('a')
            if category_links:
                last_category_link = category_links[-1]
                category_url = last_category_link.get('href')
                if category_url == '/e-shop/mystyle':
                    product_data = None
                    return product_data

                # Use full category path for mapping
                if category_url:
                    mapped_category = self.map_category(category_url)
                    product_data['Hlavna kategória'] = mapped_category
                else:
                    product_data['Hlavna kategória'] = ""
            else:
                product_data['Hlavna kategória'] = ""
        else:
            product_data = None
        
        return product_data
    
    def map_category(self, category_url):
        """Map the category using categories.json
        
        Args:
            category_url: Original category URL from the website
            
        Returns:
            str: Mapped category name
        """
        try:
            # Check if categories.json exists and load mappings
            if os.path.exists(self.categories_file):
                with open(self.categories_file, 'r', encoding='utf-8') as f:
                    category_mappings = json.load(f)
                
                # Look for a matching category in the mappings
                for mapping in category_mappings:
                    if mapping['oldCategory'] == category_url:
                        return mapping['newCategory']
                
                # Try without domain part
                if category_url.startswith('http'):
                    category_path = '/' + category_url.split('/', 3)[-1]
                    for mapping in category_mappings:
                        if mapping['oldCategory'] == category_path:
                            return mapping['newCategory']
            
            return category_url
        
        except Exception as e:
            logger.error(f"Error mapping category: {str(e)}")
            return category_url


class FastTopchladenieScraper(TopchladenieScraper):
    """Enhanced scraper with threading support for faster processing"""
    
    def __init__(self, base_url="https://www.topchladenie.sk", categories_file="categories.json", max_workers=8):
        """Initialize the fast scraper with threading capabilities
        
        Args:
            base_url: Base URL for the website
            categories_file: Categories mapping file
            max_workers: Number of concurrent threads (default: 8)
        """
        super().__init__(base_url, categories_file)
        self.max_workers = max_workers
        self.progress_lock = Lock()
        self.results = []
        
    def scrape_products_threaded(self, product_urls, show_progress=True):
        """Scrape multiple products using threading
        
        Args:
            product_urls: List of product URLs to scrape
            show_progress: Whether to show progress bar
            
        Returns:
            pandas.DataFrame: DataFrame with scraped products
        """
        logger.info(f"Starting threaded scraping of {len(product_urls)} products with {self.max_workers} workers")
        
        # Initialize results list
        self.results = []
        
        # Create progress bar if requested
        if show_progress:
            pbar = tqdm(total=len(product_urls), desc="Scraping products", unit="product")
        
        # Use ThreadPoolExecutor for concurrent processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_url = {executor.submit(self._scrape_single_product_safe, url): url for url in product_urls}
            
            # Process completed tasks
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    product_data = future.result()
                    if product_data:
                        with self.progress_lock:
                            self.results.append(product_data)
                    
                    if show_progress:
                        pbar.update(1)
                        pbar.set_postfix({
                            'Success': len(self.results),
                            'Total': len(product_urls)
                        })
                        
                except Exception as e:
                    logger.error(f"Failed to scrape {url}: {str(e)}")
                    if show_progress:
                        pbar.update(1)
        
        if show_progress:
            pbar.close()
        
        # Convert results to DataFrame
        if self.results:
            df = pd.DataFrame(self.results)
            df['Viditeľný'] = "1"
            logger.info(f"Successfully scraped {len(self.results)} products")
            return df
        else:
            logger.warning("No products were successfully scraped")
            return pd.DataFrame()
    
    def _scrape_single_product_safe(self, url):
        """Safely scrape a single product with error handling and rate limiting
        
        Args:
            url: Product URL to scrape
            
        Returns:
            dict: Product data or None if failed
        """
        try:
            # Add small random delay to avoid overwhelming the server
            time.sleep(0.1 + (hash(url) % 5) * 0.1)  # 0.1-0.6 second delay
            
            # Use the existing extract_product_details method
            product_data = self.extract_product_details(url)
            return product_data
            
        except Exception as e:
            logger.error(f"Error scraping product {url}: {str(e)}")
            return None
    
    def scrape_categories_threaded(self, category_urls=None, show_progress=True):
        """Scrape all products from categories using threading
        
        Args:
            category_urls: List of category URLs (if None, uses get_category_links())
            show_progress: Whether to show progress bar
            
        Returns:
            pandas.DataFrame: DataFrame with all scraped products
        """
        if category_urls is None:
            category_urls = self.get_category_links()
        
        logger.info(f"Collecting product URLs from {len(category_urls)} categories")
        
        # Collect all product URLs first
        all_product_urls = []
        for category_url in category_urls:
            try:
                product_urls = self.get_product_urls(category_url)
                all_product_urls.extend(product_urls)
                logger.info(f"Found {len(product_urls)} products in category: {category_url}")
            except Exception as e:
                logger.error(f"Error getting products from category {category_url}: {str(e)}")
        
        # Remove duplicates
        unique_product_urls = list(set(all_product_urls))
        unique_product_urls = [url for url in unique_product_urls if url not in self.config.ULRS_TO_SKIP_DURING_GET_PRODUCT_URLS]
        logger.info(f"Total unique products to scrape: {len(unique_product_urls)}")
        
        # Scrape all products using threading
        return self.scrape_products_threaded(unique_product_urls, show_progress)
    
    def scrape_all_products(self):
        """Override parent method to use threading
        
        Returns:
            pandas.DataFrame: DataFrame containing all scraped products
        """
        return self.scrape_categories_threaded()


def save_to_csv(df, output_file='topchladenie_products.csv'):
    """Save the DataFrame to a CSV file
    
    Args:
        df: DataFrame to save
        output_file: Output file name
    """
    try:
        # Clean up the data before saving
        for col in df.columns:
            if df[col].dtype == 'object':
                # Convert any None values to empty string
                df[col] = df[col].fillna('')
                
                # Clean up newlines in string values to make them consistent
                if col in ['Krátky popis', 'Dlhý popis']:
                    df[col] = df[col].apply(lambda x: x.replace('\r\n', '\n').replace('\r', '\n') if isinstance(x, str) else x)
        
        # Save with UTF-8 BOM for better compatibility with Excel
        df.to_csv(output_file, index=False, encoding='utf-8-sig', sep=';', lineterminator='\n')
        logger.info(f"Data saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving data to CSV: {str(e)}")


def get_scraped_products(include_scraping=True):
    """Get products scraped from topchladenie.sk
    
    This function is called from the main application during export to include
    scraped products in the final output.
    
    Args:
        include_scraping: Boolean flag to control whether to include scraped products
    
    Returns:
        pandas.DataFrame: DataFrame with scraped products or empty DataFrame if scraping disabled
    """
    if not include_scraping:
        return pd.DataFrame()
        
    try:
        logger.info("Starting to scrape products from topchladenie.sk")
        scraper = FastTopchladenieScraper()
        products_df = scraper.scrape_all_products()
        logger.info(f"Successfully scraped {len(products_df)} products")
        return products_df
    except Exception as e:
        logger.error(f"Error during scraping process: {str(e)}")
        # Return empty DataFrame on error to avoid breaking the main application flow
        return pd.DataFrame()


def merge_with_existing_data(original_df, scraped_df):
    """Merge scraped products with existing data
    
    Args:
        original_df: DataFrame with original products
        scraped_df: DataFrame with scraped products
        
    Returns:
        pandas.DataFrame: Merged DataFrame
    """
    if scraped_df.empty:
        return original_df
        
    # Ensure all columns from original_df exist in scraped_df
    for col in original_df.columns:
        if col not in scraped_df.columns:
            scraped_df[col] = ""
    
    # Merge DataFrames
    merged_df = pd.concat([original_df, scraped_df], ignore_index=True)
    
    # Log the merge stats
    logger.info(f"Merged {len(original_df)} original products with {len(scraped_df)} scraped products")
    logger.info(f"Total products after merge: {len(merged_df)}")
    
    return merged_df


if __name__ == "__main__":
    print("Starting topchladenie.sk scraper...")
    
    # Ask user about scraper type
    print("\nChoose scraper type:")
    print("1. Fast scraper with threading (recommended)")
    print("2. Original single-threaded scraper")
    
    scraper_choice = input("Enter choice (1 or 2, default=1): ").strip() or "1"
    
    if scraper_choice == "1":
        # Get number of threads
        max_workers = input("Enter number of threads (default=8, max=16): ").strip()
        try:
            max_workers = min(int(max_workers), 16) if max_workers else 8
        except ValueError:
            max_workers = 8
        
        scraper = FastTopchladenieScraper(max_workers=max_workers)
        print(f"Using fast scraper with {max_workers} threads")
    else:
        scraper = TopchladenieScraper()
        print("Using original single-threaded scraper")
    
    print("Initializing scraper...")
    print("Beginning to scrape products...\n")
    
    try:
        # Test with a single product first
        print("Testing with a single product page...")
        test_url = "https://www.topchladenie.sk/e-shop/liebherr-wpbli-5231-grandcru-selection"
        print(f"Retrieving data from: {test_url}")
        
        product_data = scraper.extract_product_details(test_url)
        
        # Display formatted product information
        print("\n" + "=" * 50)
        print("PRODUCT INFORMATION")
        print("=" * 50)
        
        # Display basic info
        basic_fields = ['Kat. číslo', 'Názov tovaru', 'Bežná cena', 'Výrobca', 'Hlavna kategória']
        max_key_length = max(len(key) for key in basic_fields)
        
        for key in basic_fields:
            if key in product_data:
                print(f"{key.ljust(max_key_length)} : {product_data[key]}")
        
        # Handle short description with proper formatting
        print("\nSHORT DESCRIPTION / PARAMETERS")
        print("-" * 50)
        if product_data.get('Krátky popis'):
            params = product_data['Krátky popis'].split('\n')
            for param in params:
                print(f"• {param.strip()}")
        else:
            print("[No parameters found]")
        
        # Handle long description with proper formatting
        print("\nLONG DESCRIPTION")
        print("-" * 50)
        if product_data.get('Dlhý popis'):
            print(product_data['Dlhý popis'])
            print(f"\n[Total length: {len(product_data['Dlhý popis'])} characters]")
        else:
            print("[No long description found]")
            
        # Handle images with proper formatting
        print("\nPRODUCT IMAGES")
        print("-" * 50)
        if product_data.get('Obrázky'):
            image_urls = product_data['Obrázky'].split(';')
            for i, url in enumerate(image_urls, 1):
                print(f"{i}. {url}")
            print(f"\n[Total images: {len(image_urls)}]")
        else:
            print("[No images found]")
        
        print("\n" + "=" * 45)
        
        # Create a DataFrame with this single test product
        columns = ['Kat. číslo', 'Názov tovaru', 'Bežná cena', 'Výrobca', 
                  'Krátky popis', 'Dlhý popis', 'Obrázky', 'Hlavna kategória', 'Viditeľný']
        test_df = pd.DataFrame([product_data], columns=columns)
        
        # Save test product to CSV
        save_to_csv(test_df)
        print("Data saved to topchladenie_products.csv")
        
        # Ask about full scraping
        print("\nWould you like to continue with full scraping?")
        if isinstance(scraper, FastTopchladenieScraper):
            print(f"(Using {scraper.max_workers} threads - this will be much faster!)")
        else:
            print("(Using single-threaded scraper - this could take a while)")
            
        response = input("Enter 'y' for full scrape, 'c' to provide custom category URLs, or any other key to exit: ")
        
        if response.lower() == 'y':
            print("Starting full scrape of all products...")
            start_time = time.time()
            products_df = scraper.scrape_all_products()
            end_time = time.time()
            
            if not products_df.empty:
                print(f"\nCompleted in {end_time - start_time:.2f} seconds")
                print(f"Scraped {len(products_df)} products")
                save_to_csv(products_df)
                print("Full data saved to topchladenie_products.csv")
            else:
                print("No products found during full scraping.")
                
        elif response.lower() == 'c':
            print("\nEnter category URLs (one per line, empty line to finish):")
            custom_categories = []
            while True:
                url = input().strip()
                if not url:
                    break
                if url.startswith('/'):
                    url = scraper.base_url + url
                custom_categories.append(url)
            
            if custom_categories:
                print(f"\nScraping {len(custom_categories)} custom categories...")
                start_time = time.time()
                
                if isinstance(scraper, FastTopchladenieScraper):
                    products_df = scraper.scrape_categories_threaded(custom_categories)
                else:
                    # Collect product URLs
                    product_urls = []
                    for category_url in custom_categories:
                        category_product_urls = scraper.get_product_urls(category_url)
                        product_urls.extend(category_product_urls)
                    
                    product_urls = list(set(product_urls))
                    print(f"Found {len(product_urls)} unique product URLs")
                    
                    # Create DataFrame and scrape sequentially
                    df = pd.DataFrame(columns=columns)
                    for i, url in enumerate(product_urls):
                        print(f"Processing product {i+1}/{len(product_urls)}: {url}")
                        try:
                            product_data = scraper.extract_product_details(url)
                            if product_data is not None:
                                df = pd.concat([df, pd.DataFrame([product_data])], ignore_index=True)
                        except Exception as e:
                            print(f"Error processing {url}: {str(e)}")
                        time.sleep(1)
                    
                    df['Viditeľný'] = "1"
                    products_df = df
                
                end_time = time.time()
                
                if not products_df.empty:
                    print(f"\nCompleted in {end_time - start_time:.2f} seconds")
                    print(f"Scraped {len(products_df)} products from custom categories")
                    save_to_csv(products_df)
                    print("Data saved to topchladenie_products.csv")
                else:
                    print("No products found in custom categories.")
            else:
                print("No custom categories provided.")
        
        print("\nScraping completed!")
            
    except Exception as e:
        import traceback
        print(f"Scraping failed with error: {str(e)}")
        print("Traceback:")
        traceback.print_exc()

