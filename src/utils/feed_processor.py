# src/utils/feed_processor.py
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
import html
import unicodedata
from bs4 import BeautifulSoup
from decimal import Decimal
from .category_mapper import map_category
from .config_loader import load_category_mappings

def fetch_xml_feed(url: str) -> ET.Element:
    """Downloads XML feed from the given URL and returns the root element."""
    try:
        print(f"Attempting to fetch XML feed from URL: {url}")
        response = requests.get(url, timeout=30)
        
        print(f"Response status code: {response.status_code}")
        print(f"Response content type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"Response size: {len(response.content)} bytes")
        
        content_preview = response.content[:200].decode('utf-8', errors='replace')
        print(f"Content preview: {content_preview}")
        
        response.raise_for_status()
        
        try:
            root = ET.fromstring(response.content)
            print(f"Successfully parsed XML, root tag: {root.tag}")
            return root
        except ET.ParseError as xml_error:
            print(f"XML parsing error: {xml_error}")
            raise xml_error
            
    except requests.exceptions.RequestException as e:
        print(f"Request error for {url}: {e}")
        raise e

def process_gastromarket_text(description, category, category_mappings=None):
    """
    Process text content from gastromarket feed.
    Returns a tuple of (processed_description, processed_category)
    """
    processed_description = ""
    processed_category = ""
    
    if description and isinstance(description, str):
        description = unicodedata.normalize('NFKC', description)
        description = ''.join(char for char in description if ord(char) >= 32 or char in '\n\r\t')
        description = re.sub(r'[▪•●\-■□✓✔]', '###BULLET###', description)
        description = re.sub(r'(^|\s)-\s', '\1###BULLET###', description)
        
        if '###BULLET###' in description:
            parts = description.split('###BULLET###')
            cleaned_parts = []
            for part in parts:
                if part.strip():
                    clean_part = re.sub(r'[^\w\s]*', '', part.strip(), count=1)
                    clean_part = re.sub(r'[\x00-\x1F\x7F-\x9F\u2028\u2029\ufeff]', '', clean_part)
                    clean_part = re.sub(r'\s+', ' ', clean_part).strip()
                    if clean_part:
                        cleaned_parts.append(clean_part)
            processed_description = '\n'.join(cleaned_parts)
        else:
            processed_description = re.sub(r'\s+', ' ', description).strip()
    
    if category and isinstance(category, str):
        if category_mappings:
            mapped_category = map_category(category, category_mappings)
            if mapped_category != category:
                return processed_description, mapped_category
    
    return processed_description, processed_category

def process_forgastro_category(category, category_mappings=None):
    """Process ForGastro category text."""
    if not category or not isinstance(category, str):
        return category
    if category_mappings:
        return map_category(category, category_mappings)
    return category

def process_forgastro_html(html_content):
    """
    Process HTML content from forgastro feed.
    Returns a tuple of (long_desc, params_text)
    """
    if not html_content or not isinstance(html_content, str):
        return "", ""
    
    try:
        decoded_html = html.unescape(html_content)
        popis_pattern = re.compile(r'\{tab title="popis"\}(.*?)(?:\{tab title|\{/tabs\}|$)', re.DOTALL)
        parametre_pattern = re.compile(r'\{tab title="parametre"\}(.*?)(?:\{tab title|\{/tabs\}|$)', re.DOTALL)
        
        popis_match = popis_pattern.search(decoded_html)
        parametre_match = parametre_pattern.search(decoded_html)
        
        popis_content = popis_match.group(1) if popis_match else ""
        parametre_content = parametre_match.group(1) if parametre_match else ""
        
        popis_text = BeautifulSoup(popis_content, 'html.parser').get_text(separator=' ', strip=True) if popis_content else ""
        
        params_text = ""
        if parametre_content:
            soup_params = BeautifulSoup(parametre_content, 'html.parser')
            tables = soup_params.find_all('table')
            if tables:
                param_lines = []
                for row in tables[0].find_all('tr')[1:]:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= 2:
                        param_name = cols[0].get_text(strip=True)
                        param_value = cols[1].get_text(strip=True)
                        if param_value:
                            param_lines.append(f"{param_name} {param_value}")
                params_text = "\n".join(param_lines)
            else:
                params_text = soup_params.get_text(separator=' ', strip=True)
        
        return popis_text, params_text
    except Exception as e:
        print(f"Error processing HTML content: {e}")
        return "", ""

def parse_xml_feed(root: ET.Element, root_element_tag: str, mapping: dict, feed_name: str = None) -> pd.DataFrame:
    """Parses XML root element and transforms it into a Pandas DataFrame."""
    if root is None:
        return pd.DataFrame()
    
    category_mappings = load_category_mappings()
    data = []
    for item in root.findall(f".//{root_element_tag}"):
        row = {}
        product_desc_html = ""
        
        for xml_key, csv_column in mapping.items():
            if '/' in xml_key:
                elements = item.findall(xml_key)
                row[csv_column] = ", ".join([el.text.strip() for el in elements if el.text])
            else:
                element = item.find(xml_key)
                element_text = element.text.strip() if element is not None and element.text is not None else ""
                if xml_key == "product_desc" and feed_name == "forgastro":
                    product_desc_html = element_text
                else:
                    row[csv_column] = element_text

        if feed_name == "forgastro":
            if "Hlavna kategória" in row and row["Hlavna kategória"]:
                row["Hlavna kategória"] = process_forgastro_category(row["Hlavna kategória"], category_mappings)
            if product_desc_html:
                long_desc, params_text = process_forgastro_html(product_desc_html)
                if "Dlhý popis" in mapping.values():
                    row["Dlhý popis"] = long_desc
                if "Krátky popis" in mapping.values() and params_text:
                    current_short = row.get("Krátky popis", "")
                    row["Krátky popis"] = f"{current_short.strip()}\n{params_text}" if current_short.strip() else params_text
        elif feed_name == "gastromarket":
            description = row.get("Krátky popis", "")
            category = row.get("Hlavna kategória", "")
            processed_desc, processed_cat = process_gastromarket_text(description, category, category_mappings)
            if processed_desc:
                row["Krátky popis"] = processed_desc
            if processed_cat:
                row["Hlavna kategória"] = processed_cat

        row["Bežná cena"] = str(Decimal(row["Bežná cena"]) * Decimal('1.23'))
        row["Viditeľný"] = "1"
        data.append(row)
    
    df = pd.DataFrame(data)
    missing_cols = set(mapping.values()) - set(df.columns)
    for col in missing_cols:
        df[col] = ""
        
    return df[list(mapping.values()) + ["Viditeľný"]]
