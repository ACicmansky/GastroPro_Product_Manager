"""Unified category mapping service.

Replaces three previous systems:
- src/utils/category_mapper.py
- src/mappers/category_mapper_new_format.py
- CategoryMappingManager from src/utils/config_loader.py
"""

import json
import os
from typing import List, Optional, Callable, Tuple

from rapidfuzz import fuzz


class CategoryService:
    """Single unified category mapping system."""

    def __init__(self, mappings_path: str = "categories.json"):
        self.mappings_path = mappings_path
        self._mappings: dict[str, str] = {}
        self._interactive_callback: Optional[Callable[[str, Optional[str]], str]] = None
        self._load()

    def _load(self):
        """Load mappings from JSON file."""
        if not os.path.exists(self.mappings_path):
            self._mappings = {}
            return

        with open(self.mappings_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._mappings = {}
        for item in data:
            if isinstance(item, dict) and "oldCategory" in item and "newCategory" in item:
                self._mappings[item["oldCategory"]] = item["newCategory"]

    def _save(self):
        """Persist mappings back to JSON file."""
        data = [
            {"oldCategory": old, "newCategory": new}
            for old, new in self._mappings.items()
        ]
        with open(self.mappings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def map(self, old_category: str) -> Optional[str]:
        """Look up a known mapping. Returns None if not found."""
        return self._mappings.get(old_category)

    def map_or_ask(self, old_category: str, product_name: Optional[str] = None) -> str:
        """Map a category, using interactive callback if mapping is unknown.

        If no callback is set, returns the original category unchanged.
        """
        mapped = self.map(old_category)
        if mapped is not None:
            return mapped

        if self._interactive_callback:
            new_category = self._interactive_callback(old_category, product_name)
            if new_category and new_category != old_category:
                self.add_mapping(old_category, new_category)
                return new_category

        return old_category

    def suggest(self, unmapped_category: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """Suggest similar target categories using fuzzy matching.

        Returns list of (category, score) tuples sorted by score descending.
        """
        existing = self.get_unique_target_categories()
        if not existing:
            return []

        scored = []
        for target in existing:
            # Hybrid scoring: combine multiple similarity methods
            partial = fuzz.partial_ratio(unmapped_category.lower(), target.lower())
            token_sort = fuzz.token_sort_ratio(unmapped_category.lower(), target.lower())
            ratio = fuzz.ratio(unmapped_category.lower(), target.lower())

            # Weighted combination
            score = (partial * 0.40) + (token_sort * 0.30) + (ratio * 0.30)
            scored.append((target, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_n]

    def add_mapping(self, old_category: str, new_category: str):
        """Add a new mapping and persist to file."""
        self._mappings[old_category] = new_category
        self._save()

    def get_all_mappings(self) -> dict[str, str]:
        """Return all mappings as {old: new} dict."""
        return dict(self._mappings)

    def get_unique_target_categories(self) -> List[str]:
        """Return sorted list of unique target (new) category names."""
        return sorted(set(self._mappings.values()))

    def is_target_category(self, category: str) -> bool:
        """Check if a category name is a known target category."""
        return category in set(self._mappings.values())

    def set_interactive_callback(self, callback: Optional[Callable[[str, Optional[str]], str]]):
        """Set callback for interactive category mapping.

        Callback signature: (original_category, product_name) -> new_category
        """
        self._interactive_callback = callback
