"""AI result parsing and fuzzy matching."""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# Scalar units whose values are stored as bare numbers (unit lives in the header)
_SCALAR_UNITS = {
    "mm", "cm", "m", "m2", "g", "kg", "l", "ml", "w", "kw", "v", "°c", "rpm",
    "mikróny", "kg/h", "l/h", "ks/h", "kg/24h", "m3/h", "košov/h", "kg/cyklus",
    "°c/h",
}
_UNIT_SUFFIX = re.compile(r"\s*\(([^)]*)\)\s*$")
_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")
_YES = {"áno", "ano", "yes", "true", "1"}
_NO = {"nie", "no", "false", "0"}


class ResultParser:
    """Parses AI batch results and matches them back to source products."""

    def __init__(self, similarity_threshold: int = 85, allowed_params: Optional[Set[str]] = None):
        self.similarity_threshold = similarity_threshold
        # Canonical map: exact name -> itself, plus unit-less base -> full name,
        # so a model echoing "Šírka" still lands in "Šírka (mm)".
        self.param_map: Dict[str, str] = {}
        for name in allowed_params or ():
            self.param_map[name] = name
            base = _UNIT_SUFFIX.sub("", name)
            self.param_map.setdefault(base, name)

    @staticmethod
    def normalize_param_value(param_name: str, value: str) -> str:
        """Deterministic filter values: bare numbers for scalar units, canonical Áno/Nie."""
        value = str(value).strip()
        if "Áno/Nie" in param_name:
            low = value.lower()
            return "Áno" if low in _YES else "Nie" if low in _NO else value
        m = _UNIT_SUFFIX.search(param_name)
        # ponytail: ranges ("rozsah") keep their text, e.g. "-2 až +8"
        if m and m.group(1).lower() in _SCALAR_UNITS and "rozsah" not in param_name.lower():
            num = _NUMBER.search(value)
            if num:
                return num.group(0).replace(",", ".")
        return value

    def find_best_match(
        self, enhanced_name: str, column_name: str, df: pd.DataFrame
    ) -> Optional[int]:
        """Find best matching product using fuzzy matching.

        Args:
            enhanced_name: Product name/code from AI response
            column_name: Column to match against ('code' or 'name')
            df: DataFrame to search in

        Returns:
            Index of best match or None
        """
        best_match_idx = None
        best_score = 0
        enhanced_lower = enhanced_name.lower()

        for idx, row in df.iterrows():
            value = str(row[column_name]).lower()

            substring_match = enhanced_lower in value or value in enhanced_lower
            partial_score = fuzz.partial_ratio(enhanced_lower, value)
            token_score = fuzz.token_sort_ratio(enhanced_lower, value)

            max_score = max(partial_score, token_score)
            if substring_match:
                max_score = max(max_score, 90)

            if max_score > best_score and max_score >= self.similarity_threshold:
                best_score = max_score
                best_match_idx = idx

        return best_match_idx

    def update_dataframe(
        self,
        df: pd.DataFrame,
        enhanced_products: List[Dict],
        valid_indices=None,
    ) -> Tuple[pd.DataFrame, int]:
        """Update DataFrame with enhanced product data.

        Uses 3-strategy matching: exact code -> fuzzy code -> fuzzy name.

        Returns:
            Tuple of (updated DataFrame, count of updated products)
        """
        updated_count = 0
        search_df = df.loc[valid_indices] if valid_indices is not None else df

        for enhanced in enhanced_products:
            best_match_idx = None

            code = str(enhanced.get("code", "")).strip()
            if code:
                # Strategy 1: Exact match on code
                exact = search_df[search_df["code"].astype(str).str.strip() == code]
                if len(exact) == 1:
                    best_match_idx = exact.index[0]
                elif len(exact) > 1:
                    best_match_idx = exact.index[0]
                    logger.warning(f"Multiple exact matches for {code}, using first")
                else:
                    # Strategy 2: Fuzzy match on code
                    best_match_idx = self.find_best_match(code, "code", search_df)
                    if best_match_idx is None:
                        # Strategy 3: Fuzzy match on name
                        name = enhanced.get("name", "")
                        if name:
                            best_match_idx = self.find_best_match(name, "name", search_df)

            if best_match_idx is not None:
                for field in ("shortDescription", "description", "seoTitle", "metaDescription"):
                    if field in enhanced:
                        df.at[best_match_idx, field] = enhanced[field]

                if "parameters" in enhanced and isinstance(enhanced["parameters"], dict):
                    for param_key, param_val in enhanced["parameters"].items():
                        if not param_val:
                            continue
                        if self.param_map:
                            canonical = self.param_map.get(param_key)
                            if canonical is None:
                                logger.debug(f"Dropping unrequested parameter '{param_key}'")
                                continue
                            param_key = canonical
                        df.at[best_match_idx, f"filteringProperty:{param_key}"] = (
                            self.normalize_param_value(param_key, param_val)
                        )

                df.at[best_match_idx, "aiProcessed"] = "1"
                df.at[best_match_idx, "aiProcessedDate"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                updated_count += 1
            else:
                logger.error(f"No match for product {enhanced.get('code', 'UNKNOWN')}")

        return df, updated_count

    def parse_batch_results(
        self, df: pd.DataFrame, file_content: str, progress_callback=None
    ) -> Tuple[pd.DataFrame, Dict]:
        """Parse JSONL batch results and apply to DataFrame.

        Returns:
            Tuple of (updated DataFrame, stats dict)
        """
        if progress_callback:
            progress_callback(95, 100, "Aplikovanie vysledkov do tabulky...")

        enhanced_all = []

        for line in file_content.splitlines():
            if not line:
                continue
            try:
                parsed = json.loads(line)
                if "response" in parsed and parsed["response"]:
                    for part in parsed["response"]["candidates"][0]["content"]["parts"]:
                        if "text" in part:
                            text = part["text"].strip().replace("```json", "").replace("```", "")
                            try:
                                items = json.loads(text)
                                if isinstance(items, list):
                                    enhanced_all.extend(items)
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to decode batch text: {e}")
                elif "error" in parsed:
                    logger.error(f"Batch item error: {parsed['error']}")
            except Exception as e:
                logger.error(f"Error parsing batch line: {e}")

        if enhanced_all:
            updated_df, count = self.update_dataframe(df, enhanced_all)
            return updated_df, {"ai_should_process": len(enhanced_all), "ai_processed": count}

        return df, {"ai_should_process": 0, "ai_processed": 0}
