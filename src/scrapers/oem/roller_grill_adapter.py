"""OEM specification adapter for Roller Grill commercial cooking and display equipment."""

import logging
import re
from typing import Any, Dict, Optional

from .base_oem import BaseOEMAdapter

logger = logging.getLogger(__name__)

# Canonical specifications directly from official Roller Grill technical datasheets
_ROLLER_GRILL_CANONICAL: Dict[str, Dict[str, Any]] = {
    # --- Heated Display Showcases & Cabinets ---
    "WD 100": {
        "model_code": "WD 100",
        "power_w": 650,
        "voltage_v": "230",
        "temp_range": "+20°C až +90°C",
        "width_mm": 590,
        "depth_mm": 350,
        "height_mm": 390,
        "source_url": "https://www.rollergrill.com/en/product/heated-display-cabinet-wd-100",
    },
    "WD 200": {
        "model_code": "WD 200",
        "power_w": 650,
        "voltage_v": "230",
        "temp_range": "+20°C až +90°C",
        "width_mm": 590,
        "depth_mm": 350,
        "height_mm": 480,
        "source_url": "https://www.rollergrill.com/en/product/heated-display-cabinet-wd-200",
    },
    "WDL 100": {
        "model_code": "WDL 100",
        "power_w": 650,
        "voltage_v": "230",
        "temp_range": "+20°C až +90°C",
        "width_mm": 590,
        "depth_mm": 350,
        "height_mm": 390,
        "source_url": "https://www.rollergrill.com/en/product/heated-display-case-wdl-100",
    },
    "WDL 200": {
        "model_code": "WDL 200",
        "power_w": 650,
        "voltage_v": "230",
        "temp_range": "+20°C až +90°C",
        "width_mm": 590,
        "depth_mm": 350,
        "height_mm": 480,
        "source_url": "https://www.rollergrill.com/en/product/heated-display-case-wdl-200",
    },
    "WD 780 S": {
        "model_code": "WD 780 S",
        "power_w": 1200,
        "voltage_v": "230",
        "temp_range": "+20°C až +90°C",
        "width_mm": 780,
        "depth_mm": 490,
        "height_mm": 480,
        "source_url": "https://www.rollergrill.com/en/product/heated-display-case-wd-780-s",
    },
    "WD 780 D": {
        "model_code": "WD 780 D",
        "power_w": 1200,
        "voltage_v": "230",
        "temp_range": "+20°C až +90°C",
        "width_mm": 780,
        "depth_mm": 490,
        "height_mm": 640,
        "source_url": "https://www.rollergrill.com/en/product/heated-display-case-wd-780-d",
    },
    # --- Salamanders ---
    "SGM 600": {
        "model_code": "SGM 600",
        "power_w": 3000,
        "voltage_v": "230",
        "width_mm": 600,
        "depth_mm": 400,
        "height_mm": 590,
        "source_url": "https://www.rollergrill.com/en/product/salamander-sgm-600",
    },
    "SGM 800": {
        "model_code": "SGM 800",
        "power_w": 4000,
        "voltage_v": "400",
        "width_mm": 800,
        "depth_mm": 400,
        "height_mm": 590,
        "source_url": "https://www.rollergrill.com/en/product/salamander-sgm-800",
    },
    "SEM 600": {
        "model_code": "SEM 600",
        "power_w": 3000,
        "voltage_v": "230",
        "width_mm": 600,
        "depth_mm": 590,
        "height_mm": 590,
        "source_url": "https://www.rollergrill.com/en/product/salamander-sem-600",
    },
    "SEM 600 PDS": {
        "model_code": "SEM 600 PDS",
        "power_w": 3000,
        "voltage_v": "230",
        "width_mm": 600,
        "depth_mm": 590,
        "height_mm": 590,
        "source_url": "https://www.rollergrill.com/en/product/salamander-sem-600-pds",
    },
    "SEM 800": {
        "model_code": "SEM 800",
        "power_w": 4500,
        "voltage_v": "400",
        "width_mm": 800,
        "depth_mm": 590,
        "height_mm": 590,
        "source_url": "https://www.rollergrill.com/en/product/salamander-sem-800",
    },
    "SEM 800 PDS": {
        "model_code": "SEM 800 PDS",
        "power_w": 4500,
        "voltage_v": "400",
        "width_mm": 800,
        "depth_mm": 590,
        "height_mm": 590,
        "source_url": "https://www.rollergrill.com/en/product/salamander-sem-800-pds",
    },
    # --- Contact Grills ---
    "PANINI": {
        "model_code": "Panini",
        "power_w": 3000,
        "voltage_v": "230",
        "width_mm": 430,
        "depth_mm": 385,
        "height_mm": 220,
        "temp_range": "+50°C až +300°C",
        "source_url": "https://www.rollergrill.com/en/product/contact-grill-panini",
    },
    "PANINI XL": {
        "model_code": "Panini XL",
        "power_w": 3600,
        "voltage_v": "230",
        "width_mm": 410,
        "depth_mm": 620,
        "height_mm": 280,
        "temp_range": "+50°C až +300°C",
        "source_url": "https://www.rollergrill.com/en/product/contact-grill-panini-xl",
    },
    "MAJESTIC": {
        "model_code": "Majestic",
        "power_w": 4000,
        "voltage_v": "230/400",
        "width_mm": 600,
        "depth_mm": 385,
        "height_mm": 220,
        "temp_range": "+50°C až +300°C",
        "source_url": "https://www.rollergrill.com/en/product/contact-grill-majestic",
    },
    # --- Fryers ---
    "FD 50": {
        "model_code": "FD 50",
        "power_w": 3200,
        "voltage_v": "230",
        "volume_l": 5,
        "width_mm": 215,
        "depth_mm": 425,
        "height_mm": 320,
        "temp_range": "+50°C až +190°C",
        "source_url": "https://www.rollergrill.com/en/product/electric-fryer-fd-50",
    },
    "FD 80": {
        "model_code": "FD 80",
        "power_w": 3600,
        "voltage_v": "230",
        "volume_l": 8,
        "width_mm": 305,
        "depth_mm": 450,
        "height_mm": 360,
        "temp_range": "+50°C až +190°C",
        "source_url": "https://www.rollergrill.com/en/product/electric-fryer-fd-80",
    },
    "MF 120 R": {
        "model_code": "MF 120 R",
        "power_w": 3200,
        "voltage_v": "230",
        "volume_l": 12,
        "width_mm": 350,
        "depth_mm": 470,
        "height_mm": 350,
        "temp_range": "+50°C až +190°C",
        "source_url": "https://www.rollergrill.com/en/product/electric-fryer-mf-120-r",
    },
    # --- Topping & Sauce Warmers ---
    "WI 1": {
        "model_code": "WI 1",
        "power_w": 170,
        "voltage_v": "230",
        "width_mm": 220,
        "depth_mm": 150,
        "height_mm": 200,
        "temp_range": "+20°C až +90°C",
        "source_url": "https://www.rollergrill.com/en/product/topping-warmer-wi-1",
    },
    "WI 2": {
        "model_code": "WI 2",
        "power_w": 340,
        "voltage_v": "230",
        "width_mm": 220,
        "depth_mm": 300,
        "height_mm": 200,
        "temp_range": "+20°C až +90°C",
        "source_url": "https://www.rollergrill.com/en/product/topping-warmer-wi-2",
    },
    # --- Buffet Islands ---
    "SBC 40 F": {
        "model_code": "SBC 40 F",
        "power_w": 500,
        "voltage_v": "230",
        "temp_range": "-2°C až +10°C",
        "width_mm": 1440,
        "depth_mm": 1440,
        "height_mm": 1540,
        "source_url": "https://www.rollergrill.com/en/product/buffet-island-sbc-40-f",
    },
    "SBC 40 C": {
        "model_code": "SBC 40 C",
        "power_w": 3500,
        "voltage_v": "230",
        "temp_range": "+20°C až +90°C",
        "width_mm": 1440,
        "depth_mm": 1440,
        "height_mm": 1540,
        "source_url": "https://www.rollergrill.com/en/product/buffet-island-sbc-40-c",
    },
}


class RollerGrillAdapter(BaseOEMAdapter):
    """Adapter for Roller Grill commercial cooking, snack, and display equipment."""

    @property
    def manufacturer_name(self) -> str:
        return "Roller Grill"

    def can_handle(self, code: str, name: str) -> bool:
        c = code.strip().upper()
        n = name.upper()
        if c.startswith("ROLLER GRILL_") or c.startswith("ROLLER_GRILL_"):
            return True
        if "ROLLER GRILL" in n or "ROLLER-GRILL" in n:
            return True
        return False

    def extract_model(self, code: str, name: str) -> str:
        """Extract canonical Roller Grill model name."""
        c = code.strip()
        if c.upper().startswith("ROLLER GRILL_") or c.upper().startswith("ROLLER_GRILL_"):
            raw = re.sub(r"^ROLLER[ _]GRILL_", "", c, flags=re.IGNORECASE).strip()
            # Normalize e.g. WDL200 -> WDL 200, WD780S -> WD 780 S, SEM800PDS -> SEM 800 PDS
            m = re.match(r"^([A-Za-z]+)\s*(\d+)\s*(.*)$", raw)
            if m:
                prefix = m.group(1).upper()
                digits = m.group(2)
                suffix = m.group(3).upper().strip()
                res = f"{prefix} {digits}"
                if suffix:
                    res += f" {suffix}"
                return res
            return raw.upper()

        # Fallback to product name
        m = re.search(r"Roller\s*Grill\s+([A-Za-z0-9-]+(?:\s+[A-Za-z0-9-]+)*)", name, re.IGNORECASE)
        if m:
            return m.group(1).strip().upper()

        return c.upper()

    def get_specs(self, code: str, name: str) -> Optional[Dict[str, Any]]:
        """Return canonical specifications for Roller Grill equipment."""
        if not self.can_handle(code, name):
            return None

        model = self.extract_model(code, name)
        model_upper = model.upper().strip()

        # Check exact known specs
        for known_key, specs in _ROLLER_GRILL_CANONICAL.items():
            if model_upper == known_key or model_upper.replace(" ", "") == known_key.replace(" ", ""):
                return specs.copy()

        # Check partial match (e.g. "SEM 800 PDS" inside model)
        for known_key, specs in _ROLLER_GRILL_CANONICAL.items():
            if known_key in model_upper:
                return specs.copy()

        return {
            "model_code": model,
            "source_url": f"https://www.rollergrill.com/en/search?query={model.replace(' ', '+')}",
        }
