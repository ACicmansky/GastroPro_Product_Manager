# src/utils/config_loader.py
import json
import os
from typing import Dict, List

def load_config(config_path: str = 'config.json') -> Dict:
    """Loads configuration from a JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Konfiguračný súbor '{config_path}' nebol nájdený.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Chyba pri parsovaní súboru '{config_path}'. Skontrolujte syntax JSON.") from e

def load_category_mappings(mappings_path: str = 'categories.json') -> List:
    """Loads category mappings from a JSON file.
    
    Returns:
        list: List containing category mappings, or an empty list if file not found.
    """
    try:
        if os.path.exists(mappings_path):
            with open(mappings_path, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
                print(f"Loaded {len(mappings)} category mappings from {mappings_path}")
                return mappings
        else:
            print(f"Category mappings file '{mappings_path}' not found, using default category processing")
            return []
    except Exception as e:
        print(f"Error loading category mappings: {e}")
        return []
