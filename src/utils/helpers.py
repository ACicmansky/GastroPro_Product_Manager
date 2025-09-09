# src/utils/helpers.py
import pandas as pd
import re

def merge_dataframes(main_df: pd.DataFrame, feed_dfs: list, final_cols: list) -> pd.DataFrame:
    """
    Merges data from the main DataFrame and a list of DataFrames from feeds.
    Priority: Main CSV > Feed1 > Feed2 > etc.
    Joins on 'Kat. číslo' as the primary key.
    """
    merged_df = main_df.copy()
    for col in final_cols:
        if col not in merged_df.columns:
            merged_df[col] = ""
    
    join_column = "Kat. číslo"
    
    for i, df_from_feed in enumerate(feed_dfs):
        if df_from_feed.empty:
            continue
            
        if join_column in df_from_feed.columns and join_column in merged_df.columns:
            feed_suffix = f'_feed{i+1}'
            temp_df = pd.merge(merged_df, df_from_feed, on=join_column, how="outer", suffixes=('', feed_suffix))
            
            for feed_col in [c for c in temp_df.columns if c.endswith(feed_suffix)]:
                original_col = feed_col.replace(feed_suffix, '')
                if original_col in temp_df.columns:
                    # Special handling for description columns to avoid overwriting AI-enhanced content
                    if original_col in ['Krátky popis', 'Dlhý popis'] and 'Spracovane AI' in temp_df.columns:
                        mask = (
                            (temp_df[original_col].isna() | (temp_df[original_col] == "")) & 
                            temp_df[feed_col].notna() &
                            (temp_df['Spracovane AI'].isin([False, 'FALSE', ""]))
                        )
                    else:
                        mask = (temp_df[original_col].isna() | (temp_df[original_col] == "")) & temp_df[feed_col].notna()
                    
                    temp_df.loc[mask, original_col] = temp_df.loc[mask, feed_col]
                
                temp_df = temp_df.drop(columns=[feed_col])
            
            merged_df = temp_df
    
    for col in final_cols:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].fillna("").astype(str).replace("nan", "")
        else:
            merged_df[col] = ""
    
    return merged_df

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
