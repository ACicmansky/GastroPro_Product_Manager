"""
Product Variant Matcher

This module provides functionality to identify product variants based on product name similarity,
assign parent catalog numbers to create proper product hierarchies, and extract product differences
such as dimensions, power, volume, and other variant characteristics.
"""
import re
import os
import json
import pandas as pd
from difflib import SequenceMatcher
from collections import defaultdict
from datetime import datetime


def natural_sort_key(s):
    """
    Generate a key for natural sorting of alphanumeric strings.
    For example: "A10" will come before "A2" in standard sorting,
    but after "A2" in natural sorting.
    """
    # Split the string into text and numeric parts
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', str(s))]


def normalize_unit(value, unit):
    """
    Normalize units to standard format (mm, W, L).
    
    Args:
        value: The numeric value
        unit: The unit string (cm, mm, kW, W, l, L, etc.)
        
    Returns:
        Tuple of (normalized value, normalized unit)
    """
    unit = unit.lower() if unit else ""
    try:
        value = float(value.replace(',', '.')) if isinstance(value, str) else float(value)
    except (ValueError, TypeError):
        return None, None
        
    # Convert to standard units
    if unit in ['cm', 'centimeter', 'centimeters']:
        return value * 10, 'mm'  # Convert cm to mm
    elif unit in ['m', 'meter', 'meters']:
        return value * 1000, 'mm'  # Convert m to mm
    elif unit in ['kw', 'kW']:
        return value * 1000, 'W'  # Convert kW to W
    elif unit in ['l', 'L', 'liter', 'liters', 'litre', 'litres']:
        return value, 'L'  # Standardize to L
    else:
        return value, unit


class ProductVariantMatcher:
    """
    Class for identifying product variants based on name similarity and assigning
    appropriate parent catalog numbers.
    """
    
    def __init__(self, report_dir="reports", progress_callback=None, extraction_config_path="variant_extractions.json"):
        """
        Initialize the ProductVariantMatcher with the given parameters.
        
        Args:
            report_dir: Directory to save variant reports
            progress_callback: Optional callback function for progress updates
            extraction_config_path: Path to the variant extraction configuration file
        """
        self.report_dir = report_dir
        self.progress_callback = progress_callback
        self.extraction_config_path = extraction_config_path
        self.extraction_config = self._load_extraction_config()
    
    def log_progress(self, message):
        """Send progress message if a callback is provided"""
        if self.progress_callback:
            self.progress_callback(message)
            
    def _load_extraction_config(self):
        """
        Load the variant extraction configuration file.
        
        Returns:
            List of dictionaries containing category and result_columns
        """
        try:
            with open(self.extraction_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.log_progress(f"Loaded extraction configuration from {self.extraction_config_path}")
                return config
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.log_progress(f"Warning: Failed to load extraction configuration: {e}")
            return []
            
    def _get_columns_to_show(self, category):
        """
        Get the columns to show for a specific product category.
        
        Args:
            category: Product category
            
        Returns:
            List of column names to show or empty list if category not in config
        """
        # Look for a matching category in the config
        for entry in self.extraction_config:
            if entry.get('category', '') == category:
                return entry.get('result_columns', [])
                
        # If no match, return empty list (no extraction for categories not in config)
        return []
    
    def extract_base_name(self, name):
        """
        Extract base product name by removing dimensions and sizes.
        
        Args:
            name: Product name to process
            
        Returns:
            Base name without dimensions or size information
        """
        if pd.isna(name) or name == "":
            return ""
            
        # Convert to string if not already
        name = str(name)
        
        # Remove dimensions anywhere in the string with formats like: 400x400x850mm, 5x33, 300x700 mm, 2500x800x450mm
        base = re.sub(r'\s+\d+(?:[xX×]\d+)+(?:\s*mm)?(?:\s*cm)?(?:\s*l)?(?:\s|$)', ' ', name)
        
        # Remove dimensions in format 800x300x600 mm at the end
        base = re.sub(r'\s+\d+(?:[xX×]\d+)+(?:\s*mm)?(?:\s*cm)?(?:\s*l)?$', '', base)
        
        # Remove formats like: - 400x400x850 mm, - 5x33, - 300x700 mm
        base = re.sub(r'\s*[-–]\s*\d+(?:[xX×]\d+)*(?:\s*mm)?(?:\s*cm)?(?:\s*l)?', '', base)
        
        # Remove sizes like: - 25 cm, - 50 l, - 115 l, - 1800-2000, KW 250, 200/60
        base = re.sub(r'\s*[-–]?\s*\d+(?:[/-]\d+)?(?:\s*[a-zA-Z]+)?(?:\s|$)', ' ', base)
        
        # Remove dimensions and sizes within parentheses: (400x400x850 mm), (5x33)
        base = re.sub(r'\s*\(\d+(?:[xX×]\d+)*(?:\s*mm)?(?:\s*cm)?(?:\s*l)?\)', '', base)
        
        # Clean up multiple spaces
        base = re.sub(r'\s+', ' ', base)
        
        return base.strip()
    
    def identify_variants(self, df, generate_report=True):
        """
        Identifies product variants and assigns parent catalog numbers based on product name similarity.
        
        Args:
            df: DataFrame containing product data with columns 'Názov tovaru', 'Kat. číslo', and optionally 'Kat. číslo rodiča'
            generate_report: Whether to generate a report file of grouped products
            extract_differences: Whether to extract product differences (dimensions, power, etc.)
            
        Returns:
            DataFrame with updated 'Kat. číslo rodiča' values for identified variants and optional difference columns
        """
        # Ensure required columns exist
        if "Názov tovaru" not in df.columns or "Kat. číslo" not in df.columns:
            self.log_progress("Warning: Required columns missing for variant detection")
            return df
        
        # Create a copy to avoid modifying the original
        result_df = df.copy()
        
        # Ensure 'Kat. číslo rodiča' column exists
        if "Kat. číslo rodiča" not in result_df.columns:
            result_df["Kat. číslo rodiča"] = ""
        
        # Step 1: Handle products that already have parent catalog numbers
        has_parent = result_df["Kat. číslo rodiča"].notna() & (result_df["Kat. číslo rodiča"] != "")
        
        # Skip processing if all products already have parents or there are very few products
        if has_parent.all() or len(result_df) < 2:
            return result_df
            
        # Count products before processing
        before_count = (~has_parent).sum()
        self.log_progress(f"Analyzing {before_count} products for variant detection...")
        
        # Step 2: Find products that are already used as parent catalog numbers
        # and exclude them from processing to avoid circular references
        used_as_parent = result_df.loc[result_df["Kat. číslo rodiča"].notna() & 
                                      (result_df["Kat. číslo rodiča"] != ""), 
                                      "Kat. číslo rodiča"].unique()
        
        # Filter out products that are already used as parent catalog numbers
        not_parent = ~result_df["Kat. číslo"].isin(used_as_parent)
        self.log_progress(f"Excluding {(~not_parent).sum()} products already used as parent variants")
        
        # Skip Liebherr products if manufacturer column exists
        is_not_liebherr = pd.Series(True, index=result_df.index)
        if "Výrobca" in result_df.columns:
            is_liebherr = result_df["Výrobca"].str.contains("Liebherr", case=False, na=False)
            is_not_liebherr = ~is_liebherr
            self.log_progress(f"Excluding {is_liebherr.sum()} Liebherr products from variant detection")
        
        # Step 3: Process products without parent catalog number and not used as parent
        products_to_process = result_df[~has_parent & not_parent & is_not_liebherr].copy()
        
        # Step 4: Extract base names by removing dimensions and sizes
        products_to_process["base_name"] = products_to_process["Názov tovaru"].apply(self.extract_base_name)
        
        # Filter out products with empty base names
        products_to_process = products_to_process[products_to_process["base_name"] != ""]
        
        # Step 4: Group by similar base names
        groups = defaultdict(list)
        processed_indices = set()
        
        # Compare each product with others
        product_data = list(products_to_process.iterrows())
        group_counter = 0
        
        for i, (idx1, row1) in enumerate(product_data):
            if idx1 in processed_indices:
                continue
                
            base_name1 = row1["base_name"]
            # Skip very short base names (likely to cause false positives)
            if len(base_name1) < 8:
                continue
                
            group_key = f"group_{group_counter}"
            group_counter += 1
            
            groups[group_key].append(idx1)
            processed_indices.add(idx1)
            
            for idx2, row2 in product_data[i+1:]:
                if idx2 in processed_indices:
                    continue
                    
                base_name2 = row2["base_name"]
                
                # Skip very short base names
                if len(base_name2) < 8:
                    continue
                
                # Skip if base names are different lengths by more than 50%
                len_ratio = min(len(base_name1), len(base_name2)) / max(len(base_name1), len(base_name2))
                if len_ratio < 0.5:  # Skip if too different in length
                    continue
                    
                # Check if base names are similar (using sequence matcher)
                similarity = SequenceMatcher(None, base_name1, base_name2).ratio()
                if similarity > 0.98:  # Threshold can be adjusted
                    groups[group_key].append(idx2)
                    processed_indices.add(idx2)
        
        # Step 5: Assign parent catalog numbers and collect group data for reporting
        variants_count = 0
        groups_count = 0
        group_data = [] # Collect data for reporting
        
        for group_indices in groups.values():
            # Skip groups with just one product
            if len(group_indices) <= 1:
                continue
                
            groups_count += 1
            variants_count += len(group_indices)
            
            # Get the products in this group
            group_products = products_to_process.loc[group_indices].copy()
            
            # Use natural sorting to find the "lowest" catalog number
            catalog_numbers = group_products["Kat. číslo"].tolist()
            parent_catalog = sorted(catalog_numbers, key=natural_sort_key)[0]
            
            # Assign this as parent for all products in group except the parent catalog
            result_df.loc[group_indices[group_indices != parent_catalog], "Kat. číslo rodiča"] = parent_catalog
            
            # Add to group data for reporting
            group_info = {
                "group_id": groups_count,
                "parent_catalog": parent_catalog,
                "products": []
            }
            
            # Add each product's details
            for idx, row in group_products.iterrows():
                group_info["products"].append({
                    "catalog_number": row["Kat. číslo"],
                    "name": row["Názov tovaru"],
                    "base_name": row["base_name"],
                    "is_parent": row["Kat. číslo"] == parent_catalog
                })
                
            group_data.append(group_info)
        
        if groups_count > 0:
            self.log_progress(f"Detected {variants_count} variants in {groups_count} product groups")
            self.log_progress(f"Assigned parent catalog numbers to {variants_count} products")
            
            # Generate report if requested
            if generate_report and group_data:
                report_file = self.generate_report(group_data)
                self.log_progress(f"Generated variant groups report: {report_file}")

        else:
            self.log_progress("No product variants detected")
        
        return result_df, group_data
        
    def generate_report(self, group_data):
        """
        Generate a human-readable report of the product variant groups.
        
        Args:
            group_data: List of dictionaries containing group information
            
        Returns:
            Path to the generated report file
        """
        # Create reports directory if it doesn't exist
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir)
            
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join(self.report_dir, f"product_variants_{timestamp}.txt")
        
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write("PRODUCT VARIANT GROUPS REPORT\n")
            f.write("===========================\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total groups: {len(group_data)}\n")
            f.write(f"Total variants: {sum(len(g['products']) for g in group_data)}\n\n")
            
            # Write each group
            for group in group_data:
                f.write(f"Group #{group['group_id']} - Parent catalog: {group['parent_catalog']}\n")
                f.write("-" * 80 + "\n")
                
                # Write products in this group
                for i, product in enumerate(group['products'], 1):
                    parent_indicator = "[PARENT]" if product["is_parent"] else "        "
                    f.write(f"{i}. {parent_indicator} {product['catalog_number']} - {product['name']}\n")
                    f.write(f"   Base name: {product['base_name']}\n")
                
                f.write("\n" + "=" * 80 + "\n\n")
        
        return report_filename
    
    def generate_differences_report(self, df, group_data):
        """
        Generate a human-readable report of the extracted product differences.
        
        Args:
            df: DataFrame containing product data with extracted differences
            group_data: List of dictionaries containing grouped product information
            
        Returns:
            Path to the generated differences report file
        """
        # Create reports directory if it doesn't exist
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir)
            
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join(self.report_dir, f"product_differences_{timestamp}.txt")
        
        # Create a dictionary to map product catalog numbers to their index in the DataFrame
        catalog_to_index = {}
        for idx, row in df.iterrows():
            catalog_number = row['Kat. číslo']
            if pd.notna(catalog_number) and catalog_number != "":
                catalog_to_index[catalog_number] = idx
        
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write("PRODUCT DIFFERENCES REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Process each product group
            for group_idx, group in enumerate(group_data, 1):
                parent_catalog = group['parent_catalog']
                f.write(f"Group #{group_idx} - Parent catalog: {parent_catalog}\n")
                f.write("-" * 80 + "\n")
                
                # Get product details for all products in the group
                products_with_differences = []
                for product in group['products']:
                    catalog = product['catalog_number']
                    if catalog in catalog_to_index:
                        idx = catalog_to_index[catalog]
                        is_parent = catalog == parent_catalog
                        
                        # Get product category
                        category = df.at[idx, 'Hlavna kategória'] if 'Hlavna kategória' in df.columns else ''
                        
                        # Skip products whose categories aren't in the config
                        columns_to_show = self._get_columns_to_show(category)
                        if not columns_to_show:
                            continue
                        
                        width = df.at[idx, 'Šírka'] if 'Šírka' in df.columns and pd.notna(df.at[idx, 'Šírka']) and 'Šírka' in columns_to_show else ""
                        length = df.at[idx, 'Dĺžka'] if 'Dĺžka' in df.columns and pd.notna(df.at[idx, 'Dĺžka']) and 'Dĺžka' in columns_to_show else ""
                        height = df.at[idx, 'Výška'] if 'Výška' in df.columns and pd.notna(df.at[idx, 'Výška']) and 'Výška' in columns_to_show else ""
                        power = df.at[idx, 'Výkon'] if 'Výkon' in df.columns and pd.notna(df.at[idx, 'Výkon']) and 'Výkon' in columns_to_show else ""
                        volume = df.at[idx, 'Objem'] if 'Objem' in df.columns and pd.notna(df.at[idx, 'Objem']) and 'Objem' in columns_to_show else ""
                        variant = df.at[idx, 'Variant'] if 'Variant' in df.columns and pd.notna(df.at[idx, 'Variant']) and 'Variant' in columns_to_show else ""
                        
                        # Check if product has any extracted differences
                        has_differences = any([width, length, height, power, volume, variant])
                        
                        products_with_differences.append({
                            'catalog': catalog,
                            'name': product['name'],
                            'is_parent': is_parent,
                            'width': width,
                            'length': length,
                            'height': height,
                            'power': power,
                            'volume': volume,
                            'variant': variant,
                            'has_differences': has_differences
                        })
                
                # Output each product with its differences
                for idx, product in enumerate(products_with_differences, 1):
                    parent_marker = "[PARENT] " if product['is_parent'] else "         "
                    f.write(f"{idx}. {parent_marker}{product['catalog']} - {product['name']}\n")
                    
                    # Write detected differences
                    dimensions = []
                    if product['width']:
                        dimensions.append(f"Šírka: {product['width']}")
                    if product['length']:
                        dimensions.append(f"Dĺžka: {product['length']}")
                    if product['height']:
                        dimensions.append(f"Výška: {product['height']}")
                    
                    # Write dimensions on one line if any exist
                    if dimensions:
                        f.write(f"   Rozmery: {', '.join(dimensions)}\n")
                    
                    # Write power and volume if they exist
                    if product['power']:
                        f.write(f"   Výkon: {product['power']}\n")
                    if product['volume']:
                        f.write(f"   Objem: {product['volume']}\n")
                    if product['variant']:
                        f.write(f"   Variant: {product['variant']}\n")
                    
                    # If no differences detected, note that
                    if not product['has_differences']:
                        f.write("   Žiadne rozdiely neboli detekované\n")
                    
                    f.write("\n")
                
                f.write("\n" + "=" * 80 + "\n\n")
        
        return report_filename
        
    def extract_product_differences(self, df, group_data):
        """
        Extract product differences such as dimensions, power, volume, etc.
        and add them as new columns to the DataFrame based on product category.
        
        Args:
            df: DataFrame containing product data
            group_data: List of dictionaries containing grouped product information
            
        Returns:
            DataFrame with additional columns for product differences
        """
        # Define all possible extraction columns
        all_columns = ['Šírka', 'Dĺžka', 'Výška', 'Výkon', 'Objem', 'Variant']
        
        # Ensure all possible columns exist in the DataFrame
        for col in all_columns:
            if col not in df.columns:
                df[col] = ""
        
        # Create a dictionary to map product indices to their catalog numbers
        catalog_to_index = {}
        for idx, row in df.iterrows():
            catalog_number = row['Kat. číslo']
            if pd.notna(catalog_number) and catalog_number != "":
                catalog_to_index[catalog_number] = idx
        
        # Create a dictionary to map categories to their extraction columns
        category_to_columns = {}
        for entry in self.extraction_config:
            category = entry.get('category', '')
            if category:
                category_to_columns[category] = entry.get('result_columns', [])
        
        self.log_progress(f"Loaded extraction rules for {len(category_to_columns)} categories")
        
        # Process each product group
        for group in group_data:
            # Process each product in the group
            for product in group['products']:
                catalog = product['catalog_number']
                if catalog in catalog_to_index:
                    idx = catalog_to_index[catalog]
                    name = product['name']
                    
                    # Get product category and determine which columns to extract
                    category = df.at[idx, 'Hlavna kategória'] if 'Hlavna kategória' in df.columns else ''
                    
                    # Only extract differences for categories explicitly defined in config
                    if category not in category_to_columns:
                        continue
                        
                    columns_to_extract = category_to_columns[category]
                    
                    short_desc = df.at[idx, 'Krátky popis'] if 'Krátky popis' in df.columns and pd.notna(df.at[idx, 'Krátky popis']) else ""
                    
                    # Extract information based on the columns specified for this category
                    if any(col in columns_to_extract for col in ['Šírka', 'Dĺžka', 'Výška']):
                        dimensions = self._extract_dimensions(name, short_desc)
                        if dimensions:
                            if 'Šírka' in columns_to_extract:
                                df.at[idx, 'Šírka'] = dimensions.get('width', '')
                            if 'Dĺžka' in columns_to_extract:
                                df.at[idx, 'Dĺžka'] = dimensions.get('length', '')
                            if 'Výška' in columns_to_extract:
                                df.at[idx, 'Výška'] = dimensions.get('height', '')
                    
                    if 'Výkon' in columns_to_extract:
                        power = self._extract_power(name, short_desc)
                        if power:
                            df.at[idx, 'Výkon'] = power
                    
                    if 'Objem' in columns_to_extract:
                        volume = self._extract_volume(name, short_desc)
                        if volume:
                            df.at[idx, 'Objem'] = volume
                    
                    if 'Variant' in columns_to_extract:
                        variant = self._extract_variant_differences(product['name'], product['base_name'])
                        if variant:
                            df.at[idx, 'Variant'] = variant
        
        # Generate report for product differences
        diff_report_file = self.generate_differences_report(df, group_data)
        self.log_progress(f"Generated product differences report: {diff_report_file}")            
        
        return df
    
    def _extract_dimensions(self, name, short_desc=""):
        """
        Extract width, length, and height dimensions from product name or description.
        
        Args:
            name: Product name
            short_desc: Optional short description
            
        Returns:
            Dictionary with width, length, and height values if found
        """
        dimensions = {}
        
        # Try to extract dimensions from the product name first
        
        # Pattern for dimensions like: 500x735x880mm, 610x455x1800, 40 x 40 cm
        pattern_3d = r'(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)(?:\s*([a-zA-Z]+))?'
        match_3d = re.search(pattern_3d, name)
        
        if match_3d:
            width, length, height, unit = match_3d.groups()
            unit = unit if unit else "mm"  # Default unit if not specified
            
            width_val, width_unit = normalize_unit(width, unit)
            length_val, length_unit = normalize_unit(length, unit)
            height_val, height_unit = normalize_unit(height, unit)
            
            if width_val is not None:
                dimensions['width'] = f"{width_val} {width_unit}"
            if length_val is not None:
                dimensions['length'] = f"{length_val} {length_unit}"
            if height_val is not None:
                dimensions['height'] = f"{height_val} {height_unit}"
                
            return dimensions
        
        # Pattern for 2D dimensions like: 400x400, 10x20 cm
        pattern_2d = r'(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)(?:\s*([a-zA-Z]+))?'
        match_2d = re.search(pattern_2d, name)
        
        if match_2d:
            width, length, unit = match_2d.groups()
            unit = unit if unit else "mm"  # Default unit if not specified
            
            width_val, width_unit = normalize_unit(width, unit)
            length_val, length_unit = normalize_unit(length, unit)
            
            if width_val is not None:
                dimensions['width'] = f"{width_val} {width_unit}"
            if length_val is not None:
                dimensions['length'] = f"{length_val} {length_unit}"
                
            return dimensions
        
        # If no dimensions found in name, try short description
        if short_desc and not dimensions:
            # Try 3D pattern in short description
            match_3d = re.search(pattern_3d, short_desc)
            if match_3d:
                width, length, height, unit = match_3d.groups()
                unit = unit if unit else "mm"  # Default unit if not specified
                
                width_val, width_unit = normalize_unit(width, unit)
                length_val, length_unit = normalize_unit(length, unit)
                height_val, height_unit = normalize_unit(height, unit)
                
                if width_val is not None:
                    dimensions['width'] = f"{width_val} {width_unit}"
                if length_val is not None:
                    dimensions['length'] = f"{length_val} {length_unit}"
                if height_val is not None:
                    dimensions['height'] = f"{height_val} {height_unit}"
            else:
                # Try 2D pattern in short description
                match_2d = re.search(pattern_2d, short_desc)
                if match_2d:
                    width, length, unit = match_2d.groups()
                    unit = unit if unit else "mm"  # Default unit if not specified
                    
                    width_val, width_unit = normalize_unit(width, unit)
                    length_val, length_unit = normalize_unit(length, unit)
                    
                    if width_val is not None:
                        dimensions['width'] = f"{width_val} {width_unit}"
                    if length_val is not None:
                        dimensions['length'] = f"{length_val} {length_unit}"
        
        # Try to extract individual dimensions
        width_patterns = [
            r'šírka[:\s]+(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)?',
            r'šírka[:\s]+(\d+(?:[.,]\d+)?)',
            r'š\s*[:\-]\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)?',
            r'š\s*[:\-]\s*(\d+(?:[.,]\d+)?)',
        ]
        
        length_patterns = [
            r'dĺžka[:\s]+(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)?',
            r'dĺžka[:\s]+(\d+(?:[.,]\d+)?)',
            r'dlžka[:\s]+(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)?',
            r'dlžka[:\s]+(\d+(?:[.,]\d+)?)',
            r'd\s*[:\-]\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)?',
            r'd\s*[:\-]\s*(\d+(?:[.,]\d+)?)',
        ]
        
        height_patterns = [
            r'výška[:\s]+(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)?',
            r'výška[:\s]+(\d+(?:[.,]\d+)?)',
            r'vyska[:\s]+(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)?',
            r'vyska[:\s]+(\d+(?:[.,]\d+)?)',
            r'v\s*[:\-]\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)?',
            r'v\s*[:\-]\s*(\d+(?:[.,]\d+)?)',
        ]
        
        # Check all text sources
        text_sources = [name]
        if short_desc:
            text_sources.append(short_desc)
            
        for text in text_sources:
            # Try to extract width
            if 'width' not in dimensions:
                for pattern in width_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        groups = match.groups()
                        width = groups[0]
                        unit = groups[1] if len(groups) > 1 and groups[1] else "mm"
                        width_val, width_unit = normalize_unit(width, unit)
                        if width_val is not None:
                            dimensions['width'] = f"{width_val} {width_unit}"
                        break
            
            # Try to extract length
            if 'length' not in dimensions:
                for pattern in length_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        groups = match.groups()
                        length = groups[0]
                        unit = groups[1] if len(groups) > 1 and groups[1] else "mm"
                        length_val, length_unit = normalize_unit(length, unit)
                        if length_val is not None:
                            dimensions['length'] = f"{length_val} {length_unit}"
                        break
            
            # Try to extract height
            if 'height' not in dimensions:
                for pattern in height_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        groups = match.groups()
                        height = groups[0]
                        unit = groups[1] if len(groups) > 1 and groups[1] else "mm"
                        height_val, height_unit = normalize_unit(height, unit)
                        if height_val is not None:
                            dimensions['height'] = f"{height_val} {height_unit}"
                        break
        
        return dimensions
    
    def _extract_power(self, name, short_desc=""):
        """
        Extract power information from product name or description.
        
        Args:
            name: Product name
            short_desc: Optional short description
            
        Returns:
            Standardized power string if found, empty string otherwise
        """
        # Patterns for power like: 4 x 2,6 kW, 2x 5kW, 6W, 2x 8W
        power_patterns = [
            # Multiple power units: 4 x 2,6 kW, 2x 5kW
            r'(\d+)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*([kK]?[wW])',
            # Single power unit: 6W, 2.5 kW
            r'(\d+(?:[.,]\d+)?)\s*([kK]?[wW])',
            # Power labeled: výkon: 2500W, výkon: 2,5 kW
            r'výkon[:\s]+(\d+(?:[.,]\d+)?)\s*([kK]?[wW])',
        ]
        
        # Check all text sources
        text_sources = [name]
        if short_desc:
            text_sources.append(short_desc)
            
        for text in text_sources:
            # Check for multiple power units pattern first
            for pattern in power_patterns:
                match = re.search(pattern, text)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:  # Multiple power units pattern
                        count, power_val, power_unit = groups
                        normalized_val, normalized_unit = normalize_unit(power_val, power_unit)
                        if normalized_val is not None:
                            return f"{count}x {normalized_val} {normalized_unit}"
                    else:  # Single power unit pattern
                        power_val, power_unit = groups
                        normalized_val, normalized_unit = normalize_unit(power_val, power_unit)
                        if normalized_val is not None:
                            return f"{normalized_val} {normalized_unit}"
        
        return ""
    
    def _extract_volume(self, name, short_desc=""):
        """
        Extract volume information from product name or description.
        
        Args:
            name: Product name
            short_desc: Optional short description
            
        Returns:
            Standardized volume string if found, empty string otherwise
        """
        # Patterns for volume like: 1x20l, 2 x 10 L, 25 L
        volume_patterns = [
            # Multiple volumes: 1x20l, 2 x 10 L
            r'(\d+)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*([lL])',
            # Single volume: 25 L, 25l, 25 litrov
            r'(\d+(?:[.,]\d+)?)\s*([lL](?:iter|itre|itrov)?s?)',
            # Volume labeled: objem: 25L, objem: 25 l
            r'objem[:\s]+(\d+(?:[.,]\d+)?)\s*([lL](?:iter|itre|itrov)?s?)',
        ]
        
        # Check all text sources
        text_sources = [name]
        if short_desc:
            text_sources.append(short_desc)
            
        for text in text_sources:
            # Check patterns
            for pattern in volume_patterns:
                match = re.search(pattern, text)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:  # Multiple volume pattern
                        count, volume_val, volume_unit = groups
                        normalized_val, normalized_unit = normalize_unit(volume_val, volume_unit)
                        if normalized_val is not None:
                            return f"{count}x {normalized_val} {normalized_unit}"
                    else:  # Single volume pattern
                        volume_val, volume_unit = groups
                        normalized_val, normalized_unit = normalize_unit(volume_val, volume_unit)
                        if normalized_val is not None:
                            return f"{normalized_val} {normalized_unit}"
        
        return ""
    
    def _extract_variant_differences(self, full_name, base_name):
        """
        Extract variant differences by comparing full name to base name.
        
        Args:
            full_name: Complete product name
            base_name: Extracted base name (without dimensions/specs)
            
        Returns:
            String describing variant differences if found, empty string otherwise
        """
        # If base name is the same as full name, there's no variant difference
        if full_name == base_name:
            return ""
            
        # Try to find zone counts (e.g., "2 zony" vs "4 zony")
        zone_pattern = r'(\d+)\s*zon[ay]'
        zone_match = re.search(zone_pattern, full_name)
        if zone_match:
            return f"{zone_match.group(1)} zón"
        
        # Look for GN containers (e.g., "2x GN1/1" vs "3x GN1/1")
        gn_pattern = r'(\d+)[xX]\s*GN\s*\d+/\d+'
        gn_match = re.search(gn_pattern, full_name)
        if gn_match:
            return f"{gn_match.group(1)}x GN"
        
        # Extract any numbered prefix (e.g., "4 - E-sporák" vs "6 - E-sporák")
        prefix_pattern = r'^(\d+)\s*-'
        prefix_match = re.search(prefix_pattern, full_name)
        if prefix_match:
            return f"Typ {prefix_match.group(1)}"
        
        # If we couldn't identify a specific pattern, try to extract the difference
        # by removing the base name from the full name
        difference = full_name.replace(base_name, "").strip()
        if difference and len(difference) <= 30:  # Only return if difference is reasonable size
            return difference.strip(' -–:')
            
        return ""
