# src/utils/config_loader.py
import json
import os
from typing import Dict, List
from threading import Lock

# Thread-safe lock for category mappings file
_category_mappings_lock = Lock()


def load_config(config_path: str = "config.json") -> Dict:
    """Loads configuration from a JSON file."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Konfiguračný súbor '{config_path}' nebol nájdený.")
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Chyba pri parsovaní súboru '{config_path}'. Skontrolujte syntax JSON."
        ) from e


def load_category_mappings(mappings_path: str = "categories.json") -> List:
    """Loads category mappings from a JSON file.

    Returns:
        list: List containing category mappings, or an empty list if file not found.
    """
    try:
        if os.path.exists(mappings_path):
            with open(mappings_path, "r", encoding="utf-8") as f:
                mappings = json.load(f)
                print(f"Loaded {len(mappings)} category mappings from {mappings_path}")
                return mappings
        else:
            print(
                f"Category mappings file '{mappings_path}' not found, using default category processing"
            )
            return []
    except Exception as e:
        print(f"Error loading category mappings: {e}")
        return []


def save_category_mapping(
    old_category: str, new_category: str, mappings_path: str = "categories.json"
) -> bool:
    """Saves a new category mapping to the categories.json file.

    Args:
        old_category: The original category name/URL to map from
        new_category: The new category name to map to
        mappings_path: Path to the category mappings JSON file

    Returns:
        bool: True if successfully saved, False otherwise
    """
    with _category_mappings_lock:
        try:
            # Load existing mappings
            mappings = []
            if os.path.exists(mappings_path):
                with open(mappings_path, "r", encoding="utf-8") as f:
                    mappings = json.load(f)

            # Check if mapping already exists
            for mapping in mappings:
                if mapping.get("oldCategory") == old_category:
                    print(f"Mapping for '{old_category}' already exists, skipping.")
                    return False

            # Add new mapping
            new_mapping = {"oldCategory": old_category, "newCategory": new_category}
            mappings.append(new_mapping)

            # Save back to file with proper formatting
            with open(mappings_path, "w", encoding="utf-8") as f:
                json.dump(mappings, f, ensure_ascii=False, indent=2)

            print(f"Saved new category mapping: '{old_category}' -> '{new_category}'")
            return True

        except Exception as e:
            print(f"Error saving category mapping: {e}")
            return False


class CategoryMappingManager:
    """Centralized manager for category mappings with in-memory caching.

    Provides a single source of truth for category mappings, eliminating the need
    for repeated disk I/O and ensuring that newly added mappings are immediately
    available to all components during processing.
    """

    def __init__(self, mappings_path: str = "categories.json"):
        """Initialize the manager and load mappings from disk.

        Args:
            mappings_path: Path to the category mappings JSON file
        """
        self._mappings_path = mappings_path
        self._mappings = []
        self._lock = _category_mappings_lock  # Reuse existing lock
        self.reload()

    def reload(self):
        """Load or reload mappings from disk into memory cache."""
        with self._lock:
            self._mappings = load_category_mappings(self._mappings_path)

    def get_all(self) -> List[Dict]:
        """Get a copy of all current mappings.

        Returns:
            List of mapping dictionaries
        """
        with self._lock:
            return self._mappings.copy()

    def find_mapping(self, old_category: str) -> str:
        """Find the mapped category for a given old category.

        Args:
            old_category: The original category name/URL to look up

        Returns:
            The mapped category name, or None if not found
        """
        if not old_category:
            return None

        with self._lock:
            for mapping in self._mappings:
                if mapping.get("oldCategory") == old_category:
                    return mapping.get("newCategory")
        return None

    def add_mapping(self, old_category: str, new_category: str) -> bool:
        """Add a new category mapping to both memory cache and disk.

        This ensures the mapping is immediately available for subsequent products
        in the same processing run, eliminating duplicate prompts for the same category.

        Args:
            old_category: The original category name/URL to map from
            new_category: The new category name to map to

        Returns:
            True if mapping was added, False if it already exists
        """
        with self._lock:
            # Check if already exists in memory cache
            for mapping in self._mappings:
                if mapping.get("oldCategory") == old_category:
                    print(
                        f"Mapping for '{old_category}' already exists in cache, skipping."
                    )
                    return False

            # Add to memory cache immediately
            new_mapping = {"oldCategory": old_category, "newCategory": new_category}
            self._mappings.append(new_mapping)
            print(f"Added mapping to cache: '{old_category}' -> '{new_category}'")

        # Save to disk (outside lock to minimize lock duration)
        success = save_category_mapping(old_category, new_category, self._mappings_path)
        return success

    def get_unique_categories(self) -> List[str]:
        """Get a list of unique target categories (newCategory values).

        Useful for populating category suggestions.

        Returns:
            List of unique category names
        """
        with self._lock:
            categories = set()
            for mapping in self._mappings:
                new_cat = mapping.get("newCategory")
                if new_cat:
                    categories.add(new_cat)
            return list(categories)

    def is_target_category(self, category: str) -> bool:
        """Check if the category already exists as a target (newCategory) in mappings.

        Args:
            category: The category to check

        Returns:
            True if the category is a valid target category, False otherwise
        """
        if not category:
            return False

        with self._lock:
            for mapping in self._mappings:
                if mapping.get("newCategory") == category:
                    return True
        return False


def save_config(config: Dict, config_path: str = "config.json") -> bool:
    """Saves configuration to a JSON file.

    Args:
        config: Configuration dictionary to save
        config_path: Path to the configuration file

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False
