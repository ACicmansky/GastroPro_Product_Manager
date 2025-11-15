# src/utils/helpers.py
import pandas as pd
import re

from typing import Dict, Tuple


def merge_dataframes(
    main_df: pd.DataFrame, feed_dfs: Dict[str, pd.DataFrame], final_cols: list
) -> Tuple[pd.DataFrame, Dict]:
    """
    Merges data from a main DataFrame and a dictionary of named feed DataFrames.

    1.  Adds new products from feeds that are not in the main DataFrame.
    2.  For existing products, it only updates the 'Bežná cena' (Regular Price).
    3.  Ensures the final DataFrame has all specified columns and is cleaned.

    Args:
        main_df: The primary DataFrame. Can be empty.
        feed_dfs: A dictionary of named DataFrames from various feeds to merge.
        final_cols: A list of column names that should be in the final DataFrame.

    Returns:
        A tuple containing the merged DataFrame and a dictionary with merge statistics.
    """
    join_column = "Kat. číslo"

    if main_df.empty:
        final_df = pd.DataFrame(columns=final_cols)
    else:
        final_df = main_df.copy()

    if join_column not in final_df.columns and not final_df.empty:
        final_df[join_column] = ""

    # CRITICAL: Remove duplicates from main_df before setting as index
    if not final_df.empty and join_column in final_df.columns:
        duplicates = final_df[final_df.duplicated(subset=[join_column], keep=False)]
        if not duplicates.empty:
            print(
                f"WARNING: Found {len(duplicates)} duplicate products in main DataFrame"
            )
            print(
                f"Duplicate catalog numbers: {duplicates[join_column].unique().tolist()[:10]}..."
            )  # Show first 10
            # Update prices for duplicates, keep first occurrence
            for kat_cislo in duplicates[join_column].unique():
                mask = final_df[join_column] == kat_cislo
                duplicate_rows = final_df[mask]
                if len(duplicate_rows) > 1 and "Bežná cena" in final_df.columns:
                    first_idx = duplicate_rows.index[0]
                    last_price = duplicate_rows.iloc[-1]["Bežná cena"]
                    final_df.at[first_idx, "Bežná cena"] = last_price
            final_df = final_df.drop_duplicates(subset=[join_column], keep="first")
            print(
                f"Removed duplicates from main DataFrame, kept {len(final_df)} unique products"
            )

    final_df.set_index(join_column, inplace=True, drop=False)

    stats = {}

    for feed_name, feed_df in feed_dfs.items():
        if feed_df.empty or join_column not in feed_df.columns:
            continue

        feed_df_copy = feed_df.copy()

        # CRITICAL: Remove duplicates from feed DataFrame before setting as index
        if join_column in feed_df_copy.columns:
            duplicates = feed_df_copy[
                feed_df_copy.duplicated(subset=[join_column], keep=False)
            ]
            if not duplicates.empty:
                print(
                    f"WARNING: Found {len(duplicates)} duplicate products in {feed_name} feed"
                )
                print(
                    f"Duplicate catalog numbers: {duplicates[join_column].unique().tolist()[:10]}..."
                )  # Show first 10
                # Update prices for duplicates, keep first occurrence
                for kat_cislo in duplicates[join_column].unique():
                    mask = feed_df_copy[join_column] == kat_cislo
                    duplicate_rows = feed_df_copy[mask]
                    if len(duplicate_rows) > 1 and "Bežná cena" in feed_df_copy.columns:
                        first_idx = duplicate_rows.index[0]
                        last_price = duplicate_rows.iloc[-1]["Bežná cena"]
                        feed_df_copy.at[first_idx, "Bežná cena"] = last_price
                feed_df_copy = feed_df_copy.drop_duplicates(
                    subset=[join_column], keep="first"
                )
                print(
                    f"Removed duplicates from {feed_name} feed, kept {len(feed_df_copy)} unique products"
                )

        feed_df_copy.set_index(join_column, drop=False, inplace=True)

        new_products_mask = ~feed_df_copy.index.isin(final_df.index)
        existing_products_mask = feed_df_copy.index.isin(final_df.index)

        added_count = int(new_products_mask.sum())
        updated_count = 0

        if "Bežná cena" in feed_df_copy.columns and existing_products_mask.any():
            # Select the subset of products that already exist in both dataframes
            existing_from_final = final_df[final_df.index.isin(feed_df_copy.index)]
            existing_from_feed = feed_df_copy[feed_df_copy.index.isin(final_df.index)]

            # Align both subsets to the same index to ensure direct comparison
            aligned_final, aligned_feed = existing_from_final.align(
                existing_from_feed, join="inner", axis=0
            )

            # Clean and convert prices to numeric for accurate comparison
            original_prices_numeric = aligned_final["Bežná cena"].apply(clean_price)
            new_prices_numeric = aligned_feed["Bežná cena"].apply(clean_price)

            # Identify which prices have actually changed
            prices_to_update_mask = (new_prices_numeric != original_prices_numeric) & (
                new_prices_numeric.notna()
            )

            # Get the indices of the products to update
            update_indices = prices_to_update_mask[prices_to_update_mask].index
            prices_to_update = feed_df_copy.loc[update_indices]

            if not prices_to_update.empty:
                # Apply updates only for prices that have changed
                final_df.loc[update_indices, "Bežná cena"] = prices_to_update[
                    "Bežná cena"
                ]
                updated_count = len(update_indices)
            else:
                updated_count = 0
        else:
            updated_count = 0

        if new_products_mask.any():
            final_df = pd.concat([final_df, feed_df_copy[new_products_mask]])

        stats[feed_name] = {"added": added_count, "updated": updated_count}

    final_df.reset_index(drop=True, inplace=True)

    for col in final_cols:
        if col not in final_df.columns:
            final_df[col] = ""

    final_df = final_df[final_cols]

    for col in final_cols:
        final_df[col] = final_df[col].fillna("").astype(str).replace("nan", "")

    return final_df, stats


def clean_price(price):
    """Cleans a price string and converts it to a float."""
    if not isinstance(price, str):
        return float("nan")

    cleaned_price = price.replace("€", "").replace(",", ".").strip()
    try:
        return float(cleaned_price)
    except (ValueError, TypeError):
        return float("nan")


def clean_html_text(s):
    """Cleans a string by removing unwanted characters from text nodes while preserving HTML structure."""
    if not isinstance(s, str):
        return s

    # This regex is complex; it finds text outside of tags and applies a cleaning function to it.
    def repl(match):
        return re.sub(
            r"[^\w\u00C0-\u017F/\-\+\~\:\°\,\;\.\?\!\%\(\)\s]+", "", match.group(0)
        )

    # Apply replacement only to content between > and <
    cleaned_s = re.sub(r">([^<]+)<", lambda m: ">" + repl(m) + "<", s)
    # Also remove quotes and backslashes from the whole string
    return cleaned_s.replace('"', "").replace("\\", "")
