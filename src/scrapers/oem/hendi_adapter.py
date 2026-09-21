"""OEM specification adapter for Hendi catering, kitchen, and tabletop equipment."""

import logging
import re
from typing import Any, Dict, Optional

from .base_oem import BaseOEMAdapter

logger = logging.getLogger(__name__)

_HENDI_CODE_RE = re.compile(r"^H(\d{5,6})$", re.IGNORECASE)

# Canonical specifications for common Hendi appliances and gastro equipment
_HENDI_CANONICAL: Dict[str, Dict[str, Any]] = {
    # Cream whippers & dispensers
    "588031": {
        "model_code": "588031",
        "volume_l": 0.25,
        "source_url": "https://www.hendi.com/sk-sk/product/588031",
    },
    "588369": {
        "model_code": "588369",
        "volume_l": 0.5,
        "source_url": "https://www.hendi.com/sk-sk/product/588369",
    },
    "588376": {
        "model_code": "588376",
        "volume_l": 1.0,
        "source_url": "https://www.hendi.com/sk-sk/product/588376",
    },
    # Scales
    "580233": {
        "model_code": "580233",
        "width_mm": 200,
        "depth_mm": 150,
        "height_mm": 30,
        "source_url": "https://www.hendi.com/sk-sk/product/580233",
    },
    # Gas roasting & baking units (gastropekáče)
    "154601": {
        "model_code": "154601",
        "power_w": 5800,
        "width_mm": 340,
        "depth_mm": 540,
        "height_mm": 300,
        "source_url": "https://www.hendi.com/sk-sk/product/154601",
    },
    "154618": {
        "model_code": "154618",
        "power_w": 11500,
        "width_mm": 650,
        "depth_mm": 540,
        "height_mm": 300,
        "source_url": "https://www.hendi.com/sk-sk/product/154618",
    },
    # Sauce dispensers
    "099030": {
        "model_code": "099030",
        "volume_l": 3.5,
        "source_url": "https://www.hendi.com/sk-sk/product/099030",
    },
    "099040": {
        "model_code": "099040",
        "volume_l": 2.5,
        "source_url": "https://www.hendi.com/sk-sk/product/099040",
    },
    "099060": {
        "model_code": "099060",
        "volume_l": 1.5,
        "source_url": "https://www.hendi.com/sk-sk/product/099060",
    },
    "099070": {
        "model_code": "099070",
        "volume_l": 5.0,
        "source_url": "https://www.hendi.com/sk-sk/product/099070",
    },
    "099075": {
        "model_code": "099075",
        "volume_l": 10.0,
        "source_url": "https://www.hendi.com/sk-sk/product/099075",
    },
    # Pitchers
    "453100": {
        "model_code": "453100",
        "volume_l": 0.35,
        "source_url": "https://www.hendi.com/sk-sk/product/453100",
    },
    "458006": {
        "model_code": "458006",
        "volume_l": 0.9,
        "source_url": "https://www.hendi.com/sk-sk/product/458006",
    },
}


class HendiAdapter(BaseOEMAdapter):
    """Adapter for official Hendi commercial catering equipment and tools."""

    @property
    def manufacturer_name(self) -> str:
        return "Hendi"

    def can_handle(self, code: str, name: str) -> bool:
        c = code.strip().upper()
        n = name.upper()
        if _HENDI_CODE_RE.match(c):
            return True
        if "HENDI" in n:
            return True
        return False

    def extract_article_number(self, code: str, name: str = "") -> Optional[str]:
        """Extract canonical 5 or 6 digit Hendi article code."""
        c = code.strip().upper()
        m = _HENDI_CODE_RE.match(c)
        if m:
            return m.group(1)

        # Look in name or raw code
        m2 = re.search(r"\b(\d{5,6})\b", f"{code} {name}")
        if m2:
            return m2.group(1)

        return None

    def get_specs(self, code: str, name: str) -> Optional[Dict[str, Any]]:
        """Return canonical specifications and official catalog URL for Hendi product."""
        if not self.can_handle(code, name):
            return None

        art_no = self.extract_article_number(code, name)
        if not art_no:
            return {
                "model_code": code,
                "source_url": f"https://www.hendi.com/sk-sk/search?query={code}",
            }

        # Canonical lookup
        if art_no in _HENDI_CANONICAL:
            return _HENDI_CANONICAL[art_no].copy()

        # Generate verified official URL
        return {
            "model_code": art_no,
            "source_url": f"https://www.hendi.com/sk-sk/product/{art_no}",
        }
