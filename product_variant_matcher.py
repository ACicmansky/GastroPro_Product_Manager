"""
Product Variant Matcher

This module provides functionality to identify product variants based on product name similarity
and assign parent catalog numbers to create proper product hierarchies.
"""
import re
import os
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


class ProductVariantMatcher:
    """
    Class for identifying product variants based on name similarity and assigning
    appropriate parent catalog numbers.
    """
    
    def __init__(self, progress_callback=None, report_dir="reports"):
        """
        Initialize the ProductVariantMatcher.
        
        Args:
            progress_callback: Optional function to call with progress messages
            report_dir: Directory to save report files (will be created if doesn't exist)
        """
        self.progress_callback = progress_callback
        self.report_dir = report_dir
    
    def log_progress(self, message):
        """Send progress message if a callback is provided"""
        if self.progress_callback:
            self.progress_callback(message)
    
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
            
        Returns:
            DataFrame with updated 'Kat. číslo rodiča' values for identified variants
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
            group_products = products_to_process.loc[group_indices]
            
            # Use natural sorting to find the "lowest" catalog number
            catalog_numbers = group_products["Kat. číslo"].tolist()
            parent_catalog = sorted(catalog_numbers, key=natural_sort_key)[0]
            
            # Assign this as parent for all products in group
            result_df.loc[group_indices, "Kat. číslo rodiča"] = parent_catalog
            
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
        
        return result_df
        
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
