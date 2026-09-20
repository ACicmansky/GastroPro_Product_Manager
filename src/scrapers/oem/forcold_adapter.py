"""OEM specification adapter for Forcold (Forcar) products."""

import logging
from typing import Any, Dict, Optional

from .base_oem import BaseOEMAdapter


logger = logging.getLogger(__name__)

# Canonical specifications directly from official forcold.it manufacturer datasheets
# Format: code/model -> specs
_FORCOLD_CANONICAL: Dict[str, Dict[str, Any]] = {
    # 1300L Double-Door Cabinets
    "F840130": {
        "model_code": "M-GN1410TN-FC",
        "insulation_mm": 60,
        "volume_l": 1300,
        "power_w": 508,
        "voltage_v": "230",
        "temp_range": "0 až 8",
        "width_mm": 1480,
        "depth_mm": 830,
        "height_mm": 2010,
        "source_url": "https://www.forcold.it/en/product/refrigerated-cabinets-gn2-1-ventilated-g-gn1410tn-fc/",
    },
    "F840131": {
        "model_code": "M-GN1410BT-FC",
        "insulation_mm": 60,
        "volume_l": 1300,
        "power_w": 920,
        "voltage_v": "230",
        "temp_range": "-18 až -22",
        "width_mm": 1480,
        "depth_mm": 830,
        "height_mm": 2010,
        "source_url": "https://www.forcold.it/en/product/refrigerated-cabinets-gn2-1-ventilated-g-gn1410bt-fc/",
    },
    # 650L Single-Door Cabinets
    "F840650": {
        "model_code": "M-GN650TN-FC",
        "insulation_mm": 60,
        "volume_l": 650,
        "power_w": 360,
        "voltage_v": "230",
        "temp_range": "0 až 8",
        "width_mm": 740,
        "depth_mm": 830,
        "height_mm": 2010,
        "source_url": "https://www.forcold.it/en/product/refrigerated-cabinets-gn2-1-ventilated-g-gn650tn-fc/",
    },
    "F840651": {
        "model_code": "M-GN650BT-FC",
        "insulation_mm": 60,
        "volume_l": 650,
        "power_w": 560,
        "voltage_v": "230",
        "temp_range": "-18 až -22",
        "width_mm": 740,
        "depth_mm": 830,
        "height_mm": 2010,
        "source_url": "https://www.forcold.it/en/product/refrigerated-cabinets-gn2-1-ventilated-g-gn650bt-fc/",
    },
}


class ForcoldAdapter(BaseOEMAdapter):
    """Adapter for official Forcold (Forcar) refrigeration specifications."""

    @property
    def manufacturer_name(self) -> str:
        return "Forcold"

    def can_handle(self, code: str, name: str) -> bool:
        c = code.upper().strip()
        n = name.upper()
        if c in _FORCOLD_CANONICAL:
            return True
        if c.startswith("F840") or c.startswith("F841") or c.startswith("F852"):
            return True
        if "FORCOLD" in n or "FORCAR" in n:
            return True
        return False

    def get_specs(self, code: str, name: str) -> Optional[Dict[str, Any]]:
        c = code.strip().upper()
        # 1. Check canonical dictionary
        if c in _FORCOLD_CANONICAL:
            return _FORCOLD_CANONICAL[c].copy()

        # 2. Check model name patterns (e.g. GN1410TN, GN650TN, etc.)
        combined = f"{code} {name}".upper()
        if "1410TN" in combined:
            return _FORCOLD_CANONICAL["F840130"].copy()
        if "1410BT" in combined:
            return _FORCOLD_CANONICAL["F840131"].copy()
        if "650TN" in combined:
            return _FORCOLD_CANONICAL["F840650"].copy()
        if "650BT" in combined:
            return _FORCOLD_CANONICAL["F840651"].copy()

        return None
