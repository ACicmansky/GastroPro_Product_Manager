"""Liebherr OEM Adapter for commercial and professional refrigeration."""

import re
from typing import Any, Dict, Optional
import urllib.parse

from .base_oem import BaseOEMAdapter


class LiebherrAdapter(BaseOEMAdapter):
    """Adapter for verifying Liebherr refrigeration and freezing equipment specifications."""

    # Canonical catalog of common Liebherr commercial & professional units
    KNOWN_SPECS: Dict[str, Dict[str, Any]] = {
        "CTEL 2131": {
            "volume_l": 196,
            "width_mm": 550,
            "depth_mm": 630,
            "height_mm": 1241,
            "temp_range": "+2°C až +9°C / -18°C až -26°C",
            "source_url": "https://home.liebherr.com/sk/svk/catalog/search/?query=CTel+2131",
        },
        "IRF 5101": {
            "volume_l": 286,
            "width_mm": 559,
            "depth_mm": 546,
            "height_mm": 1770,
            "source_url": "https://home.liebherr.com/sk/svk/catalog/search/?query=IRf+5101",
        },
        "SUIB 1550": {
            "volume_l": 80,
            "width_mm": 597,
            "depth_mm": 550,
            "height_mm": 820,
            "source_url": "https://home.liebherr.com/sk/svk/catalog/search/?query=SUIB+1550",
        },
        "MRFVC 3501": {
            "volume_l": 327,
            "width_mm": 597,
            "depth_mm": 654,
            "height_mm": 1684,
            "source_url": "https://home.liebherr.com/sk/svk/catalog/search/?query=MRFvc+3501",
        },
        "MRFVC 4001": {
            "volume_l": 377,
            "width_mm": 597,
            "depth_mm": 654,
            "height_mm": 1884,
            "source_url": "https://home.liebherr.com/sk/svk/catalog/search/?query=MRFvc+4001",
        },
        "MRFVC 5501": {
            "volume_l": 544,
            "width_mm": 747,
            "depth_mm": 769,
            "height_mm": 1684,
            "source_url": "https://home.liebherr.com/sk/svk/catalog/search/?query=MRFvc+5501",
        },
    }

    @property
    def manufacturer_name(self) -> str:
        return "Liebherr"

    def can_handle(self, code: str, name: str) -> bool:
        c = code.upper().strip()
        n = name.lower()
        return c.startswith("LIEBHERR") or c.startswith("LIEB") or "liebherr" in n

    def extract_model(self, code: str, name: str) -> str:
        """Extract clean model identifier from code or name."""
        c = code.strip()
        if c.upper().startswith("LIEBHERR"):
            clean = c[8:].strip()
            # Drop variant suffixes like "PURE", "PREMIUM", "PLUS"
            clean = re.sub(r"\s+(PURE|PREMIUM|PLUS|COMFORT|PRIME).*$", "", clean, flags=re.IGNORECASE)
            return clean.strip()

        # Fallback to name search
        m = re.search(r"Liebherr\s+([A-Za-z0-9-]+(?:\s+[A-Za-z0-9-]+)?)", name, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return c

    def get_specs(self, code: str, name: str) -> Optional[Dict[str, Any]]:
        """Return canonical specs for a Liebherr unit."""
        if not self.can_handle(code, name):
            return None

        model = self.extract_model(code, name)
        model_upper = model.upper()

        # Check known specs table
        for known_key, specs in self.KNOWN_SPECS.items():
            if known_key.upper() in model_upper or model_upper in known_key.upper():
                res = {
                    "insulation_mm": specs.get("insulation_mm"),
                    "volume_l": specs.get("volume_l"),
                    "power_w": specs.get("power_w"),
                    "voltage_v": specs.get("voltage_v", "230"),
                    "temp_range": specs.get("temp_range"),
                    "width_mm": specs.get("width_mm"),
                    "depth_mm": specs.get("depth_mm"),
                    "height_mm": specs.get("height_mm"),
                    "model_code": model,
                    "source_url": specs.get("source_url"),
                }
                return res

        # Generate search lookup URL for unindexed model
        query = urllib.parse.quote_plus(f"Liebherr {model}")
        return {
            "insulation_mm": None,
            "volume_l": None,
            "power_w": None,
            "voltage_v": "230",
            "temp_range": None,
            "width_mm": None,
            "depth_mm": None,
            "height_mm": None,
            "model_code": model,
            "source_url": f"https://home.liebherr.com/sk/svk/catalog/search/?query={query}",
        }
