"""Configuration loading and saving."""

import json
import os
from typing import Dict


def load_config(config_path: str = "config.json") -> Dict:
    """Load configuration from JSON file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_api_key(env_path: str = ".env") -> str:
    """Read GOOGLE_API_KEY from environment or .env file."""
    key = os.environ.get("GOOGLE_API_KEY", "")
    if key:
        return key
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("GOOGLE_API_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def save_api_key(key: str, env_path: str = ".env"):
    """Write GOOGLE_API_KEY to .env (keeping other lines) and current process env."""
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = [
                line.rstrip("\n") for line in f
                if not line.strip().startswith("GOOGLE_API_KEY=")
            ]
    lines.append(f"GOOGLE_API_KEY={key}")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    # effective immediately — load_dotenv() won't override an already-set var
    os.environ["GOOGLE_API_KEY"] = key


def save_config(config: Dict, config_path: str = "config.json") -> bool:
    """Save configuration to JSON file."""
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
