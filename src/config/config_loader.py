"""Configuration loading and saving."""

import json
from typing import Dict


def load_config(config_path: str = "config.json") -> Dict:
    """Load configuration from JSON file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: Dict, config_path: str = "config.json") -> bool:
    """Save configuration to JSON file."""
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
