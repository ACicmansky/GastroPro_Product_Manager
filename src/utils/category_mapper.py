# src/utils/category_mapper.py
import pandas as pd
import html
from typing import List, Tuple
from rapidfuzz import fuzz


def map_category(
    category, category_mappings, interactive_callback=None, product_name=None
):
    """Map a category using the provided mappings.

    Args:
        category: The category to map
        category_mappings: List of category mapping dictionaries
        interactive_callback: Optional callback function(category, product_name) -> new_category
                            Called when no mapping is found
        product_name: Optional product name for context in interactive callback

    Returns:
        Mapped category name or result from interactive callback
    """
    if not category or not isinstance(category, str) or not category_mappings:
        return category

    normalized_category = category.replace("\xa0", " ")
    try:
        normalized_category = html.unescape(normalized_category)
    except (ImportError, AttributeError):
        normalized_category = normalized_category.replace("&nbsp;", " ")

    for mapping in category_mappings:
        if (
            mapping.get("oldCategory") == category
            or mapping.get("oldCategory") == normalized_category
        ):
            return mapping["newCategory"]

        old_cat_norm = mapping.get("oldCategory", "").replace("\xa0", " ")
        try:
            old_cat_norm = html.unescape(old_cat_norm)
        except (ImportError, AttributeError):
            old_cat_norm = old_cat_norm.replace("&nbsp;", " ")

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

    def apply_map(cat):
        nonlocal mapped_count
        original = cat
        mapped = map_category(original, category_mappings)
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
