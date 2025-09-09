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
from ..utils.config_loader import load_config


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
        Backward-compatible wrapper that now splits detection into analysis and assignment.
        It returns a DataFrame with assigned parents and the computed group_data.
        """
        # Analyze to produce group_data (no assignments here)
        group_data = self.analyze_variants(df, generate_report=generate_report)
        if not group_data:
            return df, []
        # Assign parents based on the analyzed groups
        result_df = self.assign_variants_from_group_data(df, group_data, override=True)
        return result_df, group_data
        
    def analyze_variants(self, df, generate_report=True):
        """
        Analyze product variants based on product name similarity and produce group_data only.
        Does not modify the DataFrame. Optionally generates the group report.
        """
        # Ensure required columns exist
        if "Názov tovaru" not in df.columns or "Kat. číslo" not in df.columns:
            self.log_progress("Warning: Required columns missing for variant analysis")
            return []

        # Determine which products already have a parent
        if "Kat. číslo rodiča" in df.columns:
            has_parent = df["Kat. číslo rodiča"].notna() & (df["Kat. číslo rodiča"] != "")
        else:
            has_parent = pd.Series(False, index=df.index)

        # Products used as parents (avoid circular references)
        used_as_parent = []
        if "Kat. číslo rodiča" in df.columns:
            used_as_parent = df.loc[df["Kat. číslo rodiča"].notna() & (df["Kat. číslo rodiča"] != ""), "Kat. číslo rodiča"].unique()
        not_parent = ~df["Kat. číslo"].isin(used_as_parent) if len(used_as_parent) > 0 else pd.Series(True, index=df.index)

        # Skip Liebherr if manufacturer column exists
        is_not_liebherr = pd.Series(True, index=df.index)
        if "Výrobca" in df.columns:
            is_liebherr = df["Výrobca"].str.contains("Liebherr", case=False, na=False)
            is_not_liebherr = ~is_liebherr

        # Candidates to analyze
        products_to_process = df[~has_parent & not_parent & is_not_liebherr].copy()
        if products_to_process.empty or len(products_to_process) < 2:
            self.log_progress("No suitable products for variant analysis")
            return []

        # Extract base names
        products_to_process["base_name"] = products_to_process["Názov tovaru"].apply(self.extract_base_name)
        products_to_process = products_to_process[products_to_process["base_name"] != ""]

        # Group by similarity
        groups = defaultdict(list)
        processed_indices = set()
        product_data = list(products_to_process.iterrows())
        group_counter = 0

        for i, (idx1, row1) in enumerate(product_data):
            if idx1 in processed_indices:
                continue
            base_name1 = row1["base_name"]
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
                if len(base_name2) < 8:
                    continue
                len_ratio = min(len(base_name1), len(base_name2)) / max(len(base_name1), len(base_name2))
                if len_ratio < 0.5:
                    continue
                similarity = SequenceMatcher(None, base_name1, base_name2).ratio()
                if similarity > 0.98:
                    groups[group_key].append(idx2)
                    processed_indices.add(idx2)

        # Build group_data only
        group_data = []
        groups_count = 0
        variants_count = 0

        for group_indices in groups.values():
            if len(group_indices) <= 1:
                continue
            groups_count += 1
            variants_count += len(group_indices)
            group_products = products_to_process.loc[group_indices].copy()
            catalog_numbers = group_products["Kat. číslo"].tolist()
            parent_catalog = sorted(catalog_numbers, key=natural_sort_key)[0]

            group_info = {
                "group_id": groups_count,
                "parent_catalog": parent_catalog,
                "products": []
            }
            for _, row in group_products.iterrows():
                group_info["products"].append({
                    "catalog_number": row["Kat. číslo"],
                    "name": row["Názov tovaru"],
                    "base_name": row["base_name"],
                    "is_parent": row["Kat. číslo"] == parent_catalog
                })
            group_data.append(group_info)

        if groups_count > 0:
            self.log_progress(f"Detected {variants_count} variants in {groups_count} groups (analysis only)")
            if generate_report and group_data:
                report_file = self.generate_report(group_data)
                self.log_progress(f"Generated variant groups report: {report_file}")
        else:
            self.log_progress("No product variants detected during analysis")

        return group_data

    def assign_variants_from_group_data(self, df, group_data, override=True):
        """
        Assign 'Kat. číslo rodiča' according to provided group_data.
        If override is False, keep existing non-empty parents.
        """
        result_df = df.copy()
        if "Kat. číslo rodiča" not in result_df.columns:
            result_df["Kat. číslo rodiča"] = ""

        # Map catalog -> indices (handle potential duplicates)
        catalog_to_indices = {}
        for idx, cat in result_df["Kat. číslo"].items():
            if pd.notna(cat) and cat != "":
                catalog_to_indices.setdefault(cat, []).append(idx)

        assigned = 0
        for group in group_data:
            parent = group.get("parent_catalog", "")
            if not parent:
                continue
            for product in group.get("products", []):
                cat = product.get("catalog_number", "")
                if not cat or cat == parent:
                    continue
                for idx in catalog_to_indices.get(cat, []):
                    if override or result_df.at[idx, "Kat. číslo rodiča"] in ("", None) or pd.isna(result_df.at[idx, "Kat. číslo rodiča"]):
                        result_df.at[idx, "Kat. číslo rodiča"] = parent
                        assigned += 1
        self.log_progress(f"Assigned parent catalog numbers to {assigned} products from group_data")
        return result_df

    # ---------------------- Client report parsing & assignment ----------------------

    def _normalize_catalog_token(self, token: str) -> str:
        """Normalize a catalog token from report (strip leading slashes, file extensions, spaces)."""
        if token is None:
            return ""
        t = str(token).strip()
        # Remove leading slashes
        while t.startswith('/'):
            t = t[1:]
        # Remove common file-like extension at end (e.g., .jpg)
        t = re.sub(r"\.[A-Za-z]{2,4}$", "", t)
        # Remove separators that we also remove from targets during matching
        t = re.sub(r"[\s\-_/\\.]", "", t)
        return t

    def _normalize_for_match(self, s: str) -> str:
        """Normalize target catalog strings for matching: uppercase and drop separators."""
        if s is None:
            return ""
        x = str(s).upper()
        x = re.sub(r"[\s\-_/\\.]", "", x)
        return x

    def _pattern_to_regex(self, token: str) -> re.Pattern:
        """
        Convert a normalized token into a regex.
        Supports:
        - 'x'/'X' as digit placeholders (xxxx -> \d{4})
        - '*' as any sequence
        - '?' as any single character
        Other characters are treated literally (after normalization).
        """
        t = self._normalize_catalog_token(token)
        if not t:
            return re.compile(r".*", re.IGNORECASE)

        regex_parts = []
        i = 0
        while i < len(t):
            c = t[i]
            if c in ('x', 'X'):
                j = i
                while j < len(t) and t[j] in ('x', 'X'):
                    j += 1
                count = j - i
                regex_parts.append(fr"\d{{{count}}}")
                i = j
                continue
            if c == '*':
                regex_parts.append(".*")
                i += 1
                continue
            if c == '?':
                regex_parts.append('.')
                i += 1
                continue
            # Literal char (already normalized, so just escape to be safe)
            regex_parts.append(re.escape(c))
            i += 1
        pattern = '^' + ''.join(regex_parts) + '$'
        return re.compile(pattern, re.IGNORECASE)

    def parse_variant_groups_report(self, report_path):
        """
        Parse a client-provided product variants report into structured group_data.
        Supports optional wildcard tokens in catalog fields.
        """
        if not os.path.exists(report_path):
            self.log_progress(f"Report not found: {report_path}")
            return []

        def _read_text(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(p, 'r', encoding='cp1250', errors='replace') as f:
                    return f.read()

        text = _read_text(report_path)
        lines = text.splitlines()

        header_re = re.compile(r'^Group\s*#\s*(\d+)\s*-\s*Parent catalog:\s*(.+)\s*$')
        product_re = re.compile(r'^\s*\d+\.\s*(\[\s*PARENT\s*\])?\s*([^\s]+)\s*-\s*(.+?)\s*$')
        base_re = re.compile(r'^\s*Base name:\s*(.+?)\s*$')

        group_data = []
        current_group = None

        for line in lines:
            line = line.rstrip('\r\n')
            if not line:
                continue
            m_hdr = header_re.match(line)
            if m_hdr:
                if current_group:
                    group_data.append(current_group)
                gid = int(m_hdr.group(1))
                parent_token = m_hdr.group(2).strip()
                current_group = {"group_id": gid, "parent_catalog": parent_token, "products": []}
                continue

            if current_group is None:
                continue

            m_prod = product_re.match(line)
            if m_prod:
                is_parent = m_prod.group(1) is not None
                catalog_token = m_prod.group(2).strip()
                name = m_prod.group(3).strip()
                base_name_guess = self.extract_base_name(name)
                current_group["products"].append({
                    "catalog_number": catalog_token,
                    "name": name,
                    "base_name": base_name_guess,
                    "is_parent": is_parent,
                })
                continue

            m_base = base_re.match(line)
            if m_base and current_group["products"]:
                current_group["products"][-1]["base_name"] = m_base.group(1).strip()
                continue

        if current_group:
            group_data.append(current_group)

        self.log_progress(f"Parsed {len(group_data)} groups from report")
        return group_data

    def _write_assignment_summary(self, summary: dict, filepath: str):
        os.makedirs(self.report_dir, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("VARIANT ASSIGNMENT SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Groups processed: {summary.get('groups', 0)}\n")
            f.write(f"Products considered: {summary.get('total_products', 0)}\n")
            f.write(f"Assignments made: {summary.get('assigned_count', 0)}\n")
            f.write(f"Conflicts overridden: {len(summary.get('overridden_conflicts', []))}\n")
            f.write(f"Conflicts skipped: {len(summary.get('skipped_conflicts', []))}\n")
            f.write(f"Unmatched parent tokens: {len(summary.get('unmatched_parents', []))}\n")
            f.write(f"Unmatched product tokens: {len(summary.get('unmatched_products', []))}\n")
            f.write(f"Ambiguous parent tokens: {len(summary.get('ambiguous_parents', []))}\n")
            f.write(f"Ambiguous product tokens: {len(summary.get('ambiguous_products', []))}\n\n")

            def _dump(title, items):
                if not items:
                    return
                f.write(title + "\n")
                f.write("-" * 80 + "\n")
                for it in items:
                    f.write(json.dumps(it, ensure_ascii=False) + "\n")
                f.write("\n")

            _dump("UNMATCHED PARENTS", summary.get('unmatched_parents', []))
            _dump("UNMATCHED PRODUCTS", summary.get('unmatched_products', []))
            _dump("AMBIGUOUS PARENTS", summary.get('ambiguous_parents', []))
            _dump("AMBIGUOUS PRODUCTS", summary.get('ambiguous_products', []))
            _dump("CONFLICTS OVERRIDDEN", summary.get('overridden_conflicts', []))
            _dump("CONFLICTS SKIPPED", summary.get('skipped_conflicts', []))

    def assign_variants_from_report(self, df, report_path, override=True, generate_differences=True):
        """
        Apply client-approved variant groups from a report file to assign 'Kat. číslo rodiča'.
        - Supports wildcard catalog patterns (xxxx, xxx, *, ?)
        - Resolves parent pattern to a concrete parent using natural sort if multiple match
        - Optionally calls extract_product_differences() after assignment

        Returns: (result_df, resolved_group_data, summary_report_path)
        """
        group_data_raw = self.parse_variant_groups_report(report_path)
        if not group_data_raw:
            return df, [], None

        result_df = df.copy()
        if "Kat. číslo rodiča" not in result_df.columns:
            result_df["Kat. číslo rodiča"] = ""

        # Build normalized catalog lookup
        norm_to_originals = {}
        catalog_to_indices = {}
        for idx, cat in result_df["Kat. číslo"].items():
            if pd.isna(cat) or cat == "":
                continue
            catalog_to_indices.setdefault(cat, []).append(idx)
            norm = self._normalize_for_match(cat)
            norm_to_originals.setdefault(norm, set()).add(cat)

        def resolve_token(token):
            token_norm = self._normalize_catalog_token(token)
            # Direct match path (no wildcards/x)
            if not any(ch in token_norm for ch in ['*', '?', 'x', 'X']):
                # exact normalized match
                candidates = norm_to_originals.get(self._normalize_for_match(token_norm), set())
                return sorted(list(candidates), key=natural_sort_key)
            # Regex path
            rx = self._pattern_to_regex(token_norm)
            matches = []
            for norm, originals in norm_to_originals.items():
                if rx.match(norm):
                    matches.extend(list(originals))
            return sorted(list(set(matches)), key=natural_sort_key)

        resolved_group_data = []
        summary = {
            'groups': len(group_data_raw),
            'total_products': sum(len(g.get('products', [])) for g in group_data_raw),
            'assigned_count': 0,
            'unmatched_parents': [],
            'unmatched_products': [],
            'ambiguous_parents': [],
            'ambiguous_products': [],
            'overridden_conflicts': [],
            'skipped_conflicts': [],
        }

        for grp in group_data_raw:
            gid = grp.get('group_id')
            # Resolve all product tokens (expand patterns)
            expanded_products = []
            for p in grp.get('products', []):
                token = p.get('catalog_number', '')
                matches = resolve_token(token)
                if not matches:
                    summary['unmatched_products'].append({'group_id': gid, 'token': token})
                    continue
                if len(matches) > 1:
                    summary['ambiguous_products'].append({'group_id': gid, 'token': token, 'match_count': len(matches)})
                for cat in matches:
                    # Pull real name from df
                    # Choose first index for name lookup
                    idx0 = catalog_to_indices.get(cat, [None])[0]
                    name = result_df.at[idx0, 'Názov tovaru'] if idx0 is not None and 'Názov tovaru' in result_df.columns else p.get('name', '')
                    expanded_products.append({
                        'catalog_number': cat,
                        'name': name,
                        'base_name': self.extract_base_name(name),
                        'is_parent': False,  # set later
                    })

            # Resolve parent
            parent_token = grp.get('parent_catalog', '')
            parent_matches = resolve_token(parent_token) if parent_token else []
            chosen_parent = None
            if not parent_matches:
                if parent_token:
                    summary['unmatched_parents'].append({'group_id': gid, 'token': parent_token})
                # Fallback: choose smallest catalog among expanded products
                if expanded_products:
                    chosen_parent = sorted([p['catalog_number'] for p in expanded_products], key=natural_sort_key)[0]
            else:
                if len(parent_matches) > 1:
                    chosen_parent = parent_matches[0]
                    summary['ambiguous_parents'].append({'group_id': gid, 'token': parent_token, 'match_count': len(parent_matches), 'selected': chosen_parent})
                else:
                    chosen_parent = parent_matches[0]

            if not expanded_products or not chosen_parent:
                # Nothing to assign for this group
                continue

            # Mark parent flag
            for p in expanded_products:
                p['is_parent'] = (p['catalog_number'] == chosen_parent)

            # Assign to DataFrame
            for p in expanded_products:
                cat = p['catalog_number']
                if cat == chosen_parent:
                    continue
                for idx in catalog_to_indices.get(cat, []):
                    cur = result_df.at[idx, 'Kat. číslo rodiča']
                    if cur not in ("", None) and not pd.isna(cur):
                        if cur != chosen_parent:
                            if override:
                                summary['overridden_conflicts'].append({'group_id': gid, 'catalog': cat, 'old_parent': cur, 'new_parent': chosen_parent})
                                result_df.at[idx, 'Kat. číslo rodiča'] = chosen_parent
                                summary['assigned_count'] += 1
                            else:
                                summary['skipped_conflicts'].append({'group_id': gid, 'catalog': cat, 'existing_parent': cur, 'desired_parent': chosen_parent})
                        # else already set to desired parent; do nothing
                    else:
                        result_df.at[idx, 'Kat. číslo rodiča'] = chosen_parent
                        summary['assigned_count'] += 1

            resolved_group_data.append({
                'group_id': gid,
                'parent_catalog': chosen_parent,
                'products': expanded_products,
            })

        # Write summary report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_path = os.path.join(self.report_dir, f"variant_assignment_summary_{timestamp}.txt")
        self._write_assignment_summary(summary, summary_path)
        self.log_progress(f"Variant assignment summary written: {summary_path}")
        self.log_progress(f"Assignments made: {summary['assigned_count']}")

        # Optionally extract differences using resolved groups
        if generate_differences and resolved_group_data:
            result_df = self.extract_product_differences(result_df, resolved_group_data)

        return result_df, resolved_group_data, summary_path

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
