# src/utils/category_mapper.py
import pandas as pd
import html
from typing import List, Tuple, Dict, Union, Optional
from rapidfuzz import fuzz


def normalize_category_string(category: str) -> str:
    """Normalize a category string by replacing non-breaking spaces and unescaping HTML.

    Args:
        category: The category string to normalize

    Returns:
        The normalized category string
    """
    if not category:
        return ""

    normalized = category.replace("\xa0", " ")
    try:
        normalized = html.unescape(normalized)
    except (ImportError, AttributeError):
        normalized = normalized.replace("&nbsp;", " ")
    return normalized


def build_category_lookup(category_mappings: List[Dict]) -> Dict[str, Tuple[str, int]]:
    """Build a lookup dictionary from a list of category mappings.

    Args:
        category_mappings: List of category mapping dictionaries

    Returns:
        A dictionary mapping category strings (raw and normalized) to (newCategory, index)
        The index is used to resolve conflicts (lower index = higher priority)
    """
    lookup = {}
    for idx, mapping in enumerate(category_mappings):
        old_cat = mapping.get("oldCategory")
        new_cat = mapping.get("newCategory")

        if old_cat:
            # Map exact match
            if old_cat not in lookup:
                lookup[old_cat] = (new_cat, idx)

            # Map normalized match
            normalized_old = normalize_category_string(old_cat)
            if normalized_old not in lookup:
                lookup[normalized_old] = (new_cat, idx)
    return lookup


def map_category(
    category: str,
    category_mappings: Union[List[Dict], Dict[str, Tuple[str, int]]],
    interactive_callback=None,
    product_name: Optional[str] = None
) -> Optional[str]:
    """Map a category using the provided mappings.

    Args:
        category: The category to map
        category_mappings: List of category mapping dictionaries or a pre-built lookup dictionary
        interactive_callback: Optional callback function(category, product_name) -> new_category
                            Called when no mapping is found
        product_name: Optional product name for context in interactive callback

    Returns:
        Mapped category name or result from interactive callback
    """
    if not category or not isinstance(category, str) or not category_mappings:
        return category

    # Optimized path using lookup dictionary
    if isinstance(category_mappings, dict):
        normalized_category = normalize_category_string(category)

        # Check for matches
        res1 = category_mappings.get(category)
        res2 = category_mappings.get(normalized_category) if category != normalized_category else None

        result = None
        if res1 and res2:
            # If both match, prefer the one with lower index (earlier in original list)
            result = res1[0] if res1[1] <= res2[1] else res2[0]
        elif res1:
            result = res1[0]
        elif res2:
            result = res2[0]

        if result is not None:
            return result

    # Legacy path using list iteration
    elif isinstance(category_mappings, list):
        normalized_category = normalize_category_string(category)

        for mapping in category_mappings:
            if (
                mapping.get("oldCategory") == category
                or mapping.get("oldCategory") == normalized_category
            ):
                return mapping["newCategory"]

            old_cat_norm = normalize_category_string(mapping.get("oldCategory", ""))

            if old_cat_norm == category or old_cat_norm == normalized_category:
                return mapping["newCategory"]

    # No mapping found - use interactive callback if provided
    if interactive_callback:
        new_category = interactive_callback(category, product_name)
        if new_category:
            return new_category

    return category


def map_dataframe_categories(df, category_mappings):
    """Map categories in a DataFrame based on the provided mappings."""
    if (
        df is None
        or not isinstance(df, pd.DataFrame)
        or "Hlavna kategória" not in df.columns
        or not category_mappings
    ):
        return df

    mapped_df = df.copy()
    mapped_count = 0

    # Build optimized lookup dictionary once
    lookup = build_category_lookup(category_mappings) if isinstance(category_mappings, list) else category_mappings

    def apply_map(cat):
        nonlocal mapped_count
        original = cat
        mapped = map_category(original, lookup)
        if mapped != original:
            mapped_count += 1
        return mapped

    mapped_df["Hlavna kategória"] = mapped_df["Hlavna kategória"].apply(apply_map)

    print(f"Mapped {mapped_count} out of {len(mapped_df)} categories in input CSV file")
    return mapped_df


def get_category_suggestions(
    unmapped_category: str, existing_categories: List[str], top_n: int = 5
) -> List[Tuple[str, float]]:
    """Get category suggestions based on similarity to existing categories.

    Uses a hybrid approach combining:
    - Full string similarity
    - Hierarchical level matching (categories split by "/")
    - Bonus for shared parent paths

    Args:
        unmapped_category: The category to find matches for
        existing_categories: List of existing category names to match against
        top_n: Number of top suggestions to return

    Returns:
        List of tuples (category_name, similarity_score) sorted by score descending
    """
    if not unmapped_category or not existing_categories:
        return []

    # Normalize the unmapped category
    unmapped_normalized = unmapped_category.strip().lower()
    unmapped_normalized = unmapped_normalized.replace("\\", "/").replace("//", "/")
    unmapped_parts = [p.strip() for p in unmapped_normalized.split("/") if p.strip()]

    suggestions = []

    for existing_cat in existing_categories:
        if not existing_cat:
            continue

        # Normalize existing category
        existing_normalized = existing_cat.strip().lower()
        existing_normalized = existing_normalized.replace("\\", "/").replace("//", "/")
        existing_parts = [
            p.strip() for p in existing_normalized.split("/") if p.strip()
        ]

        # Calculate multiple similarity scores

        # 1. Full string similarity (40% weight)
        full_similarity = fuzz.ratio(unmapped_normalized, existing_normalized)

        # 2. Token sort similarity - handles word order differences (30% weight)
        token_similarity = fuzz.token_sort_ratio(
            unmapped_normalized, existing_normalized
        )

        # 3. Partial similarity - handles substring matches (20% weight)
        partial_similarity = fuzz.partial_ratio(
            unmapped_normalized, existing_normalized
        )

        # 4. Hierarchical bonus (10% weight)
        hierarchical_bonus = 0
        if len(unmapped_parts) > 0 and len(existing_parts) > 0:
            # Compare last level (most specific)
            last_level_sim = fuzz.ratio(unmapped_parts[-1], existing_parts[-1])

            # Check for shared parent paths
            shared_parents = 0
            for i in range(min(len(unmapped_parts) - 1, len(existing_parts) - 1)):
                if fuzz.ratio(unmapped_parts[i], existing_parts[i]) > 80:
                    shared_parents += 1
                else:
                    break

            # Bonus for shared structure
            hierarchical_bonus = last_level_sim * 0.7 + (shared_parents * 10)

        # Weighted average
        combined_score = (
            full_similarity * 0.40
            + token_similarity * 0.30
            + partial_similarity * 0.20
            + hierarchical_bonus * 0.10
        )

        suggestions.append((existing_cat, combined_score))

    # Sort by score descending and return top N
    suggestions.sort(key=lambda x: x[1], reverse=True)
    return suggestions[:top_n]
