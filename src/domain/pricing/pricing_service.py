"""Price mapping service for table base products."""

import json
import os
import logging
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class PricingService:
    """Handles price mapping for products that need manual price assignment."""

    def __init__(self, prices_path: str = "table_bases_prices.json"):
        self.prices_path = prices_path
        self._prices: Dict[str, str] = {}
        self._load()

    def _load(self):
        """Load price mappings from JSON file."""
        if os.path.exists(self.prices_path):
            with open(self.prices_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._prices = data
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "code" in item and "price" in item:
                            self._prices[item["code"]] = str(item["price"])

    def _save(self):
        """Persist price mappings."""
        with open(self.prices_path, "w", encoding="utf-8") as f:
            json.dump(self._prices, f, ensure_ascii=False, indent=2)

    def identify_unmapped(self, df: pd.DataFrame) -> List[str]:
        """Return list of product codes that need price mapping."""
        unmapped = []
        for _, row in df.iterrows():
            code = str(row.get("code", "")).strip()
            price = str(row.get("price", "")).strip()
            if code and (not price or price in ("", "0", "nan", "None")):
                if code not in self._prices:
                    unmapped.append(code)
        return unmapped

    def apply_mappings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply known price mappings to DataFrame."""
        df = df.copy()
        for idx, row in df.iterrows():
            code = str(row.get("code", "")).strip()
            if code in self._prices:
                df.at[idx, "price"] = self._prices[code]
        return df

    def add_mapping(self, code: str, price: str):
        """Add a price mapping and persist."""
        self._prices[code] = price
        self._save()

    def get_price(self, code: str) -> Optional[str]:
        """Get mapped price for a code."""
        return self._prices.get(code)
