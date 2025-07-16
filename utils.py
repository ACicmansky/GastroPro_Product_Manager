# utils.py
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import json
import re
import html
from bs4 import BeautifulSoup
import unicodedata
import os

def load_config(config_path: str = 'config.json') -> dict:
    """Loads configuration from a JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Konfiguračný súbor '{config_path}' nebol nájdený.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Chyba pri parsovaní súboru '{config_path}'. Skontrolujte syntax JSON.") from e


def load_category_mappings(mappings_path: str = 'categories.json') -> list:
    """Loads category mappings from a JSON file.
    
    Returns:
        list: List containing category mappings, or an empty list if file not found.
    """
    try:
        if os.path.exists(mappings_path):
            with open(mappings_path, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
                print(f"Loaded {len(mappings)} category mappings from {mappings_path}")
                return mappings
        else:
            print(f"Category mappings file '{mappings_path}' not found, using default category processing")
            return []
    except Exception as e:
        print(f"Error loading category mappings: {e}")
        return []


def load_csv_data(file_path: str) -> pd.DataFrame:
    """Loads CSV data from the given path into a Pandas DataFrame, considering semicolon as separator and comma as decimal point."""
    encodings = ['cp1250', 'latin1', 'utf-8-sig']
    for encoding in encodings:
        try:
            return pd.read_csv(
                file_path,
                sep=';',
                decimal=',',
                encoding=encoding,
                on_bad_lines='skip'
            )
        except UnicodeDecodeError:
            continue
    raise Exception(f"Nepodarilo sa načítať CSV súbor s kódovaním {encodings}.")    

def fetch_xml_feed(url: str) -> ET.Element:
    """Downloads XML feed from the given URL and returns the root element."""
    try:
        print(f"Attempting to fetch XML feed from URL: {url}")
        response = requests.get(url, timeout=30)
        
        # Print response status and information for debugging
        print(f"Response status code: {response.status_code}")
        print(f"Response content type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"Response size: {len(response.content)} bytes")
        
        # Show first 200 characters of response to check if it looks like XML
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
    Process text content from gastromarket feed:
    1. Split description on delimiters (▪, -) and format as multiline
    2. Apply category mapping from categories.json if available
    3. Otherwise replace | with / in category path as fallback
    
    Returns a tuple of (processed_description, processed_category)
    """
    processed_description = ""
    processed_category = ""
    
    # Process description
    if description and isinstance(description, str):
        print(f"Processing gastromarket description: {len(description)} characters")
        print(f"Preview: {description[:100]}...")
        
        # Normalize unicode characters (like special bullet points)
        description = unicodedata.normalize('NFKC', description)
        
        # Strip all non-printable and control characters first
        description = ''.join(char for char in description if ord(char) >= 32 or char in '\n\r\t')
        
        # Split on common delimiters
        # First replace the bullet points with a standard marker
        description = re.sub(r'[▪•●\-■□✓✔]', '###BULLET###', description)
        # Replace dash at beginning of line or after space
        description = re.sub(r'(^|\s)-\s', '\1###BULLET###', description)
        
        # Split by the marker and clean up
        if '###BULLET###' in description:
            parts = description.split('###BULLET###')
            # Clean parts - remove leading/trailing whitespace and any non-standard characters
            cleaned_parts = []
            for part in parts:
                if part.strip():
                    # Remove any special characters at the beginning of each line
                    clean_part = re.sub(r'^[^\w\s]*', '', part.strip())
                    # Remove control chars and odd unicode characters
                    clean_part = re.sub(r'[\x00-\x1F\x7F-\x9F\u2028\u2029\ufeff]', '', clean_part)
                    # Also replace multiple spaces with single space
                    clean_part = re.sub(r'\s+', ' ', clean_part).strip()
                    if clean_part:
                        cleaned_parts.append(clean_part)
                        
            processed_description = '\n'.join(cleaned_parts)
            print(f"Split description into {len(cleaned_parts)} lines")
        else:
            # If no bullets found, still clean the text
            processed_description = re.sub(r'\s+', ' ', description).strip()
    else:
        processed_description = ""
    
    # Process category with mapping if available
    if category and isinstance(category, str):
        # First try to find a mapping in the category mappings file
        if category_mappings:
            mapped_category = map_category(category, category_mappings)
            if mapped_category != category:
                return processed_description, mapped_category
        
        # If no mapping found or no mappings provided, use default processing
        if " | " in category:
            processed_category = category.replace(" | ", "/")
            print(f"No mapping found for Gastromarket category '{category}', using default replacement: '{processed_category}'")
        else:
            processed_category = category
    else:
        processed_category = ""
    
    return processed_description, processed_category


def map_category(category, category_mappings):
    """Map a category using the provided mappings.
    
    Args:
        category (str): The original category text
        category_mappings (list): List of category mappings
        
    Returns:
        str: Mapped category or original if no mapping found
    """
    if not category or not isinstance(category, str) or not category_mappings:
        return category
    
    # Try to find a mapping for this category
    for mapping in category_mappings:
        if mapping.get("oldCategory") == category:
            print(f"Mapped category '{category}' to '{mapping['newCategory']}'")
            return mapping["newCategory"]
    
    print(f"No mapping found for category '{category}', using original")
    return category


def map_dataframe_categories(df, category_mappings):
    """Map categories in a DataFrame based on the provided mappings.
    
    Args:
        df (pd.DataFrame): DataFrame containing a 'Hlavna kategória' column
        category_mappings (list): List of category mappings
        
    Returns:
        pd.DataFrame: DataFrame with mapped categories
    """
    if df is None or not isinstance(df, pd.DataFrame) or 'Hlavna kategória' not in df.columns or not category_mappings:
        return df
    
    # Create a copy of the DataFrame to avoid modifying the original
    mapped_df = df.copy()
    
    # Count how many categories were mapped
    mapped_count = 0
    total_count = 0
    
    # Map each category in the DataFrame
    for idx, row in mapped_df.iterrows():
        if pd.notna(row['Hlavna kategória']):
            total_count += 1
            original = row['Hlavna kategória']
            mapped = map_category(original, category_mappings)
            if mapped != original:
                mapped_count += 1
                mapped_df.at[idx, 'Hlavna kategória'] = mapped
    
    print(f"Mapped {mapped_count} out of {total_count} categories in input CSV file")
    return mapped_df


def process_forgastro_category(category, category_mappings=None):
    """Process ForGastro category text.
    
    Args:
        category (str): The category text
        category_mappings (list, optional): List of category mappings
        
    Returns:
        str: Processed category
    """
    if not category or not isinstance(category, str):
        return category
    
    # Try to find a mapping for this category using the common mapping function
    if category_mappings:
        return map_category(category, category_mappings)
    
        
    return category


def process_forgastro_html(html_content):
    """
    Process HTML content from forgastro feed:
    1. Decode HTML entities
    2. Extract content from {tab title="popis"} and {tab title="parametre"}
    3. Parse with BeautifulSoup and extract text
    
    Returns a tuple of (long_desc, params_text)
    """
    if not html_content or not isinstance(html_content, str):
        print("HTML content is empty or not a string")
        return ("", "")
    
    print(f"Processing HTML content: {len(html_content)} characters")
    print(f"Preview of HTML content: {html_content[:150]}...")
    
    # Step 1: Decode HTML entities
    try:
        decoded_html = html.unescape(html_content)
        print("Successfully decoded HTML entities")
        
        # Step 2: Extract content from specific tabs
        # Format 1: {tab title="popis"} ... {tab title} or {/tabs}
        popis_pattern1 = re.compile(r'\{tab title="popis"\}(.*?)(?:\{tab title|\{/tabs\}|$)', re.DOTALL)
        parametre_pattern1 = re.compile(r'\{tab title="parametre"\}(.*?)(?:\{tab title|\{/tabs\}|$)', re.DOTALL)
        
        popis_match = popis_pattern1.search(decoded_html)
        parametre_match = parametre_pattern1.search(decoded_html)
        
        print(f"Found popis tab: {popis_match is not None}")
        print(f"Found parametre tab: {parametre_match is not None}")
        
        popis_content = popis_match.group(1) if popis_match else ""
        parametre_content = parametre_match.group(1) if parametre_match else ""
        
        # If no matches are found, try to check if there are other patterns
        if not popis_match and not parametre_match:
            print(f"No standard tabs found, checking for alternative patterns")
            # Look for any HTML tables or structured content
            soup_check = BeautifulSoup(decoded_html, 'html.parser')
            tables = soup_check.find_all('table')
            print(f"Found {len(tables)} HTML tables")
        
        # Step 3: Parse with BeautifulSoup
        if popis_content:
            soup_popis = BeautifulSoup(popis_content, 'html.parser')
            popis_text = soup_popis.get_text(separator=' ', strip=True)
            print(f"Extracted popis text: {len(popis_text)} characters")
            print(f"Sample of popis text: {popis_text[:100]}...")
        else:
            popis_text = ""
            print("No popis content found")
            
        if parametre_content:
            soup_params = BeautifulSoup(parametre_content, 'html.parser')
            
            # Look for tables in the parameters section
            tables = soup_params.find_all('table')
            if tables:
                print(f"Found {len(tables)} tables in parameters section")
                # Process the first table (assuming it's the parameters table)
                param_table = tables[0]
                rows = param_table.find_all('tr')
                
                # Build formatted parameter text
                param_lines = []
                
                # Skip header row (first row) which contains 'Parameter' and 'Hodnota'
                for row_idx, row in enumerate(rows):
                    if row_idx == 0:  # Skip header row
                        print("Skipping header row in parameters table")
                        continue
                        
                    # Extract columns
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= 2:
                        param_name = cols[0].get_text(strip=True)
                        param_value = cols[1].get_text(strip=True)
                        if param_value == "":
                            continue
                        
                        param_line = f"{param_name} {param_value}"
                        param_lines.append(param_line)
                        print(f"Added parameter: {param_line}")
                
                # Join parameters with line breaks
                params_text = "\n".join(param_lines)
            else:
                # Fallback to regular text extraction if no table is found
                params_text = soup_params.get_text(separator=' ', strip=True)
                
            print(f"Extracted parametre text: {len(params_text)} characters")
            print(f"Sample of parametre text: {params_text[:100]}...")
        else:
            params_text = ""
            print("No parametre content found")
        
        return (popis_text, params_text)
    except Exception as e:
        print(f"Error processing HTML content: {e}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        print(traceback.format_exc())
        return ("", "")

def parse_xml_feed(root: ET.Element, root_element_tag: str, mapping: dict, feed_name: str = None) -> pd.DataFrame:
    """
    Parses XML root element and transforms it into a Pandas DataFrame
    according to the provided mapping and root element tag of the product.
    
    Args:
        root: XML root element
        root_element_tag: Tag name of products in the feed
        mapping: Dictionary mapping XML keys to CSV column names
        feed_name: Name of the feed for specialized processing
    """
    if root is None:
        return pd.DataFrame()
        
    # List to store each item's data
    items = []
    
    # Load category mappings - now it's a simple array of mappings, not grouped by feed
    category_mappings = load_category_mappings()

    data = []
    # Find all elements that represent a single product
    for item in root.findall(f".//{root_element_tag}"):
        row = {}
        
        # Special processing for forgastro product descriptions
        product_desc_html = None
        product_s_desc = None
        
        for xml_key, csv_column in mapping.items():
            # If the key is compound (e.g., "images/item/url"), use findall and join values
            if '/' in xml_key:
                elements = item.findall(xml_key)
                if elements:
                    # Join all found URL addresses into one string separated by commas
                    row[csv_column] = ", ".join([el.text.strip() for el in elements if el.text])
                else:
                    row[csv_column] = None
            else:
                element = item.find(xml_key)
                element_text = element.text.strip() if element is not None and element.text is not None else None
                
                # Store HTML content for specialized processing later
                if xml_key == "product_desc" and feed_name == "forgastro":
                    product_desc_html = element_text
                    # Don't add to row yet, we'll process it specially
                elif xml_key == "product_s_desc" and feed_name == "forgastro":
                    product_s_desc = element_text
                    row[csv_column] = element_text
                else:
                    row[csv_column] = element_text
                    
        # Apply feed-specific processing based on feed name
        if feed_name == "forgastro":
            # Process category mapping for forgastro
            if "Hlavna kategória" in row and row["Hlavna kategória"]:
                row["Hlavna kategória"] = process_forgastro_category(row["Hlavna kategória"], category_mappings)
                
            # Process HTML content if available
            if product_desc_html:
                # Forgastro-specific HTML processing
                long_desc, params_text = process_forgastro_html(product_desc_html)
                
                # Map content to appropriate columns
                if "Dlhý popis" in mapping.values():
                    row["Dlhý popis"] = long_desc
                    
                # Append parameter text to short description if it exists
                if "Krátky popis" in mapping.values() and params_text:
                    current_short = row.get("Krátky popis", "")
                    if current_short and current_short.strip():
                        # Add a blank line between description and parameters for better formatting
                        row["Krátky popis"] = f"{current_short.strip()}\n{params_text}"
                    else:
                        row["Krátky popis"] = params_text
        elif feed_name == "gastromarket":
            # Process Gastromarket description and category using universal category mappings
            description = row.get("Krátky popis", "")
            category = row.get("Hlavna kategória", "")
            processed_desc, processed_cat = process_gastromarket_text(description, category, category_mappings)
            
            # Update fields with processed values
            if processed_desc:
                row["Krátky popis"] = processed_desc
            if processed_cat:
                row["Hlavna kategória"] = processed_cat
            
        # Set 'Viditeľný' field to '1' for all feed products
        row["Viditeľný"] = "1"        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Ensure that DataFrame has all columns defined in mapping
    missing_cols = set(mapping.values()) - set(df.columns)
    for col in missing_cols:
        df[col] = None
        
    # Return DataFrame with only columns defined in mapping
    return df[list(mapping.values()) + ["Viditeľný"]]

def merge_dataframes(main_df: pd.DataFrame, feed_dfs: list, final_cols: list) -> pd.DataFrame:
    """
    Merges data from the main DataFrame and a list of DataFrames from feeds.
    Priority: Gastropro CSV (main_df) > Feed1 > Feed2 > etc.
    
    Universal solution to handle any columns regardless of presence in feeds.
    Joins on 'Kat. číslo' (catalog number) as the primary key.
    """
    # Start with a copy of the main dataframe, ensuring all final columns exist
    merged_df = main_df.copy()
    
    # First make sure the main dataframe has all necessary columns for the final output
    for col in final_cols:
        if col not in merged_df.columns:
            merged_df[col] = ""  # Add missing columns with empty string
    
    # Define the join column
    #join_column = "Kat. číslo"  # Catalog number as primary key for joining
    join_column = "Názov tovaru"  # Product name as primary key for joining
            
    # Process feeds in order of priority (lower index = higher priority)
    for i, df_from_feed in enumerate(feed_dfs):
        # Skip empty dataframes
        if df_from_feed.empty:
            print(f"Feed {i+1} is empty, skipping.")
            continue
        
        # No join needed if feed has no data
        if len(df_from_feed) == 0:
            print(f"Feed {i+1} has no rows, skipping.")
            continue
            
        try:
            # Check if we can join by catalog number
            if join_column in df_from_feed.columns and join_column in merged_df.columns:
                # Standard join on catalog number
                feed_suffix = f'_feed{i+1}'
                
                # First clean up any NaN values in the join column
                merged_df[join_column] = merged_df[join_column].fillna("")
                df_from_feed[join_column] = df_from_feed[join_column].fillna("")
                
                # Debug the join values to see what might match
                print(f"Join column '{join_column}' sample values in main DF: {merged_df[join_column].unique()[:5]}")
                print(f"Join column '{join_column}' sample values in feed: {df_from_feed[join_column].unique()[:5]}")
                
                # Use outer join to include ALL products from both sources
                # 'outer' will include rows that appear in EITHER DataFrame
                temp_df = pd.merge(merged_df, df_from_feed, on=join_column, how="outer", suffixes=('', feed_suffix))
                
                # Find columns from the feed (those with the suffix)
                feed_suffix_columns = [col for col in temp_df.columns if col.endswith(feed_suffix)]
                
                # For each feed column, fill NaN values in the corresponding original column
                for feed_col in feed_suffix_columns:
                    original_col = feed_col.replace(feed_suffix, '')
                    if original_col in temp_df.columns:
                        # Fill NaN values in original column with values from feed column
                        temp_df[original_col] = temp_df[original_col].fillna(temp_df[feed_col])
                    
                    # Remove the feed suffixed column after using its values
                    temp_df = temp_df.drop(columns=[feed_col])
                    
                # Update the merged dataframe
                merged_df = temp_df
            else:
                # Alternative approach for feeds missing the join column
                print(f"Feed {i+1} or main dataframe doesn't have '{join_column}' column for joining. Handling columns individually.")
                
                # Add all columns from feed to the main dataframe
                for col in df_from_feed.columns:
                    if col in final_cols and col not in merged_df.columns:
                        # This is a new column we want in the output
                        merged_df[col] = ""
                    elif col in final_cols:
                        # This is a column we already have, but maybe with empty values
                        # Copy non-empty values from feed to fill empty spots in main df
                        for idx in merged_df.index:
                            if pd.isna(merged_df.at[idx, col]) or merged_df.at[idx, col] == "":
                                # Try to find a non-empty value in the feed
                                if len(df_from_feed) > 0:  # Only attempt if feed has data
                                    # Take the first non-empty value we find (or empty if none found)
                                    feed_val = df_from_feed[col].dropna().iloc[0] if not df_from_feed[col].dropna().empty else ""
                                    merged_df.at[idx, col] = feed_val
        
        except Exception as e:
            print(f"Error processing feed {i+1}: {str(e)}")
            # Continue with next feed despite the error
            continue

    # Make sure all required columns exist in the final output
    for col in final_cols:
        if col not in merged_df.columns:
            merged_df[col] = ""  # Add any missing columns with empty string
    
    # Handle any remaining NaN values by converting to empty string
    result_df = merged_df[final_cols].fillna("")
    
    return result_df