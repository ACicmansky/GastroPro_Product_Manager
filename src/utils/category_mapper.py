# src/utils/category_mapper.py
import pandas as pd
import html

def map_category(category, category_mappings):
    """Map a category using the provided mappings."""
    if not category or not isinstance(category, str) or not category_mappings:
        return category
    
    normalized_category = category.replace('\xa0', ' ')
    try:
        normalized_category = html.unescape(normalized_category)
    except (ImportError, AttributeError):
        normalized_category = normalized_category.replace('&nbsp;', ' ')
    
    for mapping in category_mappings:
        if mapping.get("oldCategory") == category or mapping.get("oldCategory") == normalized_category:
            return mapping["newCategory"]
        
        old_cat_norm = mapping.get("oldCategory", "").replace('\xa0', ' ')
        try:
            old_cat_norm = html.unescape(old_cat_norm)
        except (ImportError, AttributeError):
            old_cat_norm = old_cat_norm.replace('&nbsp;', ' ')
            
        if old_cat_norm == category or old_cat_norm == normalized_category:
            return mapping["newCategory"]
    
    return category

def map_dataframe_categories(df, category_mappings):
    """Map categories in a DataFrame based on the provided mappings."""
    if df is None or not isinstance(df, pd.DataFrame) or 'Hlavna kategória' not in df.columns or not category_mappings:
        return df
    
    mapped_df = df.copy()
    mapped_count = 0
    
    def apply_map(cat):
        nonlocal mapped_count
        original = cat
        mapped = map_category(original, category_mappings)
        if mapped != original:
            mapped_count += 1
        return mapped

    mapped_df['Hlavna kategória'] = mapped_df['Hlavna kategória'].apply(apply_map)
    
    print(f"Mapped {mapped_count} out of {len(mapped_df)} categories in input CSV file")
    return mapped_df
