# src/utils/helpers.py
import pandas as pd
import re

def merge_dataframes(main_df: pd.DataFrame, feed_dfs: list, final_cols: list) -> pd.DataFrame:
    """
    Merges data from a main DataFrame and a list of feed DataFrames.

    1.  Adds new products from feeds that are not in the main DataFrame.
    2.  For existing products, it only updates the 'Bežná cena' (Regular Price).
    3.  Ensures the final DataFrame has all specified columns and is cleaned.

    Args:
        main_df: The primary DataFrame. Can be empty.
        feed_dfs: A list of DataFrames from various feeds to merge.
        final_cols: A list of column names that should be in the final DataFrame.

    Returns:
        A merged and cleaned pandas DataFrame.
    """
    join_column = "Kat. číslo"

    if main_df.empty:
        final_df = pd.DataFrame(columns=final_cols)
    else:
        final_df = main_df.copy()

    if join_column not in final_df.columns and not final_df.empty:
        final_df[join_column] = ""

    final_df.set_index(join_column, inplace=True, drop=False)

    for feed_df in feed_dfs:
        if feed_df.empty or join_column not in feed_df.columns:
            continue

        feed_df_copy = feed_df.copy().set_index(join_column, drop=False)

        new_products_mask = ~feed_df_copy.index.isin(final_df.index)
        existing_products_mask = feed_df_copy.index.isin(final_df.index)

        if new_products_mask.any():
            final_df = pd.concat([final_df, feed_df_copy[new_products_mask]])

        if 'Bežná cena' in feed_df_copy.columns and existing_products_mask.any():
            updates = feed_df_copy.loc[existing_products_mask, 'Bežná cena']
            final_df.loc[updates.index, 'Bežná cena'] = updates

    final_df.reset_index(drop=True, inplace=True)

    for col in final_cols:
        if col not in final_df.columns:
            final_df[col] = ""

    final_df = final_df[final_cols]

    for col in final_cols:
        final_df[col] = final_df[col].fillna("").astype(str).replace("nan", "")

    return final_df

def clean_html_text(s):
    """Cleans a string by removing unwanted characters from text nodes while preserving HTML structure."""
    if not isinstance(s, str):
        return s
    # This regex is complex; it finds text outside of tags and applies a cleaning function to it.
    def repl(match):
        return re.sub(r'[^\w\u00C0-\u017F/\-\+\~\:\°\,\;\.\?\!\%\(\)\s]+', '', match.group(0))
    
    # Apply replacement only to content between > and <
    cleaned_s = re.sub(r'>([^<]+)<', lambda m: '>' + repl(m) + '<', s)
    # Also remove quotes and backslashes from the whole string
    return cleaned_s.replace('"', "").replace('\\', "")
