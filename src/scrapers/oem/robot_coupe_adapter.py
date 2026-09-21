"""OEM specification adapter for Robot-Coupe commercial food preparation equipment."""

import logging
import re
from typing import Any, Dict, Optional

from .base_oem import BaseOEMAdapter

logger = logging.getLogger(__name__)

# Canonical specifications directly from official Robot-Coupe datasheets and technical documentation
_ROBOT_COUPE_CANONICAL: Dict[str, Dict[str, Any]] = {
    # --- Tabletop & Floor-Standing Cutters ---
    "R 2": {
        "model_code": "R 2",
        "power_w": 550,
        "voltage_v": "230",
        "volume_l": 2.9,
        "width_mm": 200,
        "depth_mm": 280,
        "height_mm": 350,
        "source_url": "https://www.robot-coupe.com/en-gb/p/table-top-cutters/r-2",
    },
    "R 3": {
        "model_code": "R 3",
        "power_w": 650,
        "voltage_v": "230",
        "volume_l": 3.7,
        "width_mm": 210,
        "depth_mm": 320,
        "height_mm": 400,
        "source_url": "https://www.robot-coupe.com/en-gb/p/table-top-cutters/r-3",
    },
    "R 4": {
        "model_code": "R 4",
        "power_w": 900,
        "voltage_v": "230",
        "volume_l": 4.5,
        "width_mm": 226,
        "depth_mm": 304,
        "height_mm": 440,
        "source_url": "https://www.robot-coupe.com/en-gb/p/table-top-cutters/r-4",
    },
    "R 4 V.V.": {
        "model_code": "R 4 V.V.",
        "power_w": 1000,
        "voltage_v": "230",
        "volume_l": 4.5,
        "width_mm": 226,
        "depth_mm": 304,
        "height_mm": 460,
        "source_url": "https://www.robot-coupe.com/en-gb/p/table-top-cutters/r-4-v-v",
    },
    "R 5": {
        "model_code": "R 5",
        "power_w": 1500,
        "voltage_v": "400",
        "volume_l": 5.9,
        "width_mm": 280,
        "depth_mm": 350,
        "height_mm": 490,
        "source_url": "https://www.robot-coupe.com/en-gb/p/table-top-cutters/r-5",
    },
    "R 5 V.V.": {
        "model_code": "R 5 V.V.",
        "power_w": 1500,
        "voltage_v": "230",
        "volume_l": 5.9,
        "width_mm": 280,
        "depth_mm": 350,
        "height_mm": 490,
        "source_url": "https://www.robot-coupe.com/en-gb/p/table-top-cutters/r-5-v-v",
    },
    "R 7": {
        "model_code": "R 7",
        "power_w": 1500,
        "voltage_v": "400",
        "volume_l": 7.5,
        "width_mm": 280,
        "depth_mm": 350,
        "height_mm": 520,
        "source_url": "https://www.robot-coupe.com/en-gb/p/table-top-cutters/r-7",
    },
    "R 7 V.V.": {
        "model_code": "R 7 V.V.",
        "power_w": 1500,
        "voltage_v": "230",
        "volume_l": 7.5,
        "width_mm": 280,
        "depth_mm": 350,
        "height_mm": 520,
        "source_url": "https://www.robot-coupe.com/en-gb/p/table-top-cutters/r-7-v-v",
    },
    "R 8": {
        "model_code": "R 8",
        "power_w": 2200,
        "voltage_v": "400",
        "volume_l": 8.0,
        "width_mm": 315,
        "depth_mm": 545,
        "height_mm": 585,
        "source_url": "https://www.robot-coupe.com/en-gb/p/table-top-cutters/r-8",
    },
    "R 10": {
        "model_code": "R 10",
        "power_w": 2600,
        "voltage_v": "400",
        "volume_l": 11.5,
        "width_mm": 345,
        "depth_mm": 560,
        "height_mm": 660,
        "source_url": "https://www.robot-coupe.com/en-gb/p/table-top-cutters/r-10",
    },
    "R 15": {
        "model_code": "R 15",
        "power_w": 3000,
        "voltage_v": "400",
        "volume_l": 15.0,
        "width_mm": 370,
        "depth_mm": 615,
        "height_mm": 680,
        "source_url": "https://www.robot-coupe.com/en-gb/p/table-top-cutters/r-15",
    },
    "R 20": {
        "model_code": "R 20",
        "power_w": 4400,
        "voltage_v": "400",
        "volume_l": 20.0,
        "width_mm": 380,
        "depth_mm": 630,
        "height_mm": 760,
        "source_url": "https://www.robot-coupe.com/en-gb/p/table-top-cutters/r-20",
    },
    "R 30": {
        "model_code": "R 30",
        "power_w": 5400,
        "voltage_v": "400",
        "volume_l": 28.0,
        "width_mm": 720,
        "depth_mm": 600,
        "height_mm": 1250,
        "source_url": "https://www.robot-coupe.com/en-gb/p/floor-standing-cutters/r-30",
    },
    "R 45": {
        "model_code": "R 45",
        "power_w": 10000,
        "voltage_v": "400",
        "volume_l": 45.0,
        "width_mm": 760,
        "depth_mm": 600,
        "height_mm": 1400,
        "source_url": "https://www.robot-coupe.com/en-gb/p/floor-standing-cutters/r-45",
    },
    "R 60": {
        "model_code": "R 60",
        "power_w": 11000,
        "voltage_v": "400",
        "volume_l": 60.0,
        "width_mm": 810,
        "depth_mm": 600,
        "height_mm": 1400,
        "source_url": "https://www.robot-coupe.com/en-gb/p/floor-standing-cutters/r-60",
    },
    # --- Thermal Cooking Cutter Blender ---
    "ROBOT COOK": {
        "model_code": "Robot Cook",
        "power_w": 1800,
        "voltage_v": "230",
        "volume_l": 3.7,
        "temp_range": "+20°C až +140°C",
        "width_mm": 226,
        "depth_mm": 338,
        "height_mm": 522,
        "source_url": "https://www.robot-coupe.com/en-gb/p/robot-cook/robot-cook",
    },
    # --- Vegetable Preparation Machines ---
    "CL 50": {
        "model_code": "CL 50",
        "power_w": 550,
        "voltage_v": "230",
        "width_mm": 350,
        "depth_mm": 320,
        "height_mm": 590,
        "source_url": "https://www.robot-coupe.com/en-gb/p/vegetable-preparation-machines/cl-50",
    },
    "CL 50 GOURMET": {
        "model_code": "CL 50 Gourmet",
        "power_w": 550,
        "voltage_v": "230",
        "width_mm": 350,
        "depth_mm": 320,
        "height_mm": 590,
        "source_url": "https://www.robot-coupe.com/en-gb/p/vegetable-preparation-machines/cl-50-gourmet",
    },
    "CL 52": {
        "model_code": "CL 52",
        "power_w": 750,
        "voltage_v": "230",
        "width_mm": 360,
        "depth_mm": 340,
        "height_mm": 690,
        "source_url": "https://www.robot-coupe.com/en-gb/p/vegetable-preparation-machines/cl-52",
    },
    "CL 55": {
        "model_code": "CL 55",
        "power_w": 1100,
        "voltage_v": "400",
        "width_mm": 380,
        "depth_mm": 320,
        "height_mm": 920,
        "source_url": "https://www.robot-coupe.com/en-gb/p/vegetable-preparation-machines/cl-55",
    },
    "CL 60": {
        "model_code": "CL 60",
        "power_w": 1500,
        "voltage_v": "400",
        "width_mm": 425,
        "depth_mm": 613,
        "height_mm": 1159,
        "source_url": "https://www.robot-coupe.com/en-gb/p/vegetable-preparation-machines/cl-60",
    },
    # --- Combination Food Processors ---
    "R 201": {
        "model_code": "R 201",
        "power_w": 550,
        "voltage_v": "230",
        "volume_l": 2.9,
        "width_mm": 220,
        "depth_mm": 280,
        "height_mm": 495,
        "source_url": "https://www.robot-coupe.com/en-gb/p/combination-processors/r-201",
    },
    "R 301": {
        "model_code": "R 301",
        "power_w": 650,
        "voltage_v": "230",
        "volume_l": 3.7,
        "width_mm": 220,
        "depth_mm": 340,
        "height_mm": 550,
        "source_url": "https://www.robot-coupe.com/en-gb/p/combination-processors/r-301",
    },
    "R 402": {
        "model_code": "R 402",
        "power_w": 750,
        "voltage_v": "230",
        "volume_l": 4.5,
        "width_mm": 226,
        "depth_mm": 304,
        "height_mm": 590,
        "source_url": "https://www.robot-coupe.com/en-gb/p/combination-processors/r-402",
    },
    "R 502": {
        "model_code": "R 502",
        "power_w": 1000,
        "voltage_v": "400",
        "volume_l": 5.9,
        "width_mm": 380,
        "depth_mm": 350,
        "height_mm": 665,
        "source_url": "https://www.robot-coupe.com/en-gb/p/combination-processors/r-502",
    },
    "R 752": {
        "model_code": "R 752",
        "power_w": 1800,
        "voltage_v": "400",
        "volume_l": 7.5,
        "width_mm": 380,
        "depth_mm": 350,
        "height_mm": 710,
        "source_url": "https://www.robot-coupe.com/en-gb/p/combination-processors/r-752",
    },
    # --- Immersion Blenders ---
    "MP 350": {
        "model_code": "MP 350 Ultra",
        "power_w": 440,
        "voltage_v": "230",
        "source_url": "https://www.robot-coupe.com/en-gb/p/power-mixers/mp-350-ultra",
    },
    "MP 450": {
        "model_code": "MP 450 Ultra",
        "power_w": 500,
        "voltage_v": "230",
        "source_url": "https://www.robot-coupe.com/en-gb/p/power-mixers/mp-450-ultra",
    },
    "MP 550": {
        "model_code": "MP 550 Ultra",
        "power_w": 750,
        "voltage_v": "230",
        "source_url": "https://www.robot-coupe.com/en-gb/p/power-mixers/mp-550-ultra",
    },
    # --- Juicers ---
    "J 80": {
        "model_code": "J 80 Ultra",
        "power_w": 700,
        "voltage_v": "230",
        "width_mm": 235,
        "depth_mm": 420,
        "height_mm": 505,
        "source_url": "https://www.robot-coupe.com/en-gb/p/juice-extractors/j-80-ultra",
    },
    "J 100": {
        "model_code": "J 100 Ultra",
        "power_w": 1000,
        "voltage_v": "230",
        "width_mm": 235,
        "depth_mm": 538,
        "height_mm": 596,
        "source_url": "https://www.robot-coupe.com/en-gb/p/juice-extractors/j-100-ultra",
    },
}


class RobotCoupeAdapter(BaseOEMAdapter):
    """Adapter for Robot-Coupe food preparation machines and accessories."""

    @property
    def manufacturer_name(self) -> str:
        return "Robot-Coupe"

    def can_handle(self, code: str, name: str) -> bool:
        c = code.strip().upper()
        n = name.upper()
        if c.startswith("ROC_") or c.startswith("ROC "):
            return True
        if "ROBOT-COUPE" in n or "ROBOT COUPE" in n:
            return True
        return False

    def extract_model(self, code: str, name: str) -> str:
        """Extract canonical model identifier or part number."""
        c = code.strip()
        if c.upper().startswith("ROC_"):
            raw = c[4:].strip()
            # If it's a numeric part/accessory code, e.g. " 27046" -> "27046"
            part_match = re.match(r"^\s*(\d{4,6})$", raw)
            if part_match:
                return part_match.group(1)

            # Check for well-known prefixes
            # Normalize e.g. R502VV -> R 502 V.V., R4_1500 -> R 4 - 1500, ROBOTCOOK -> ROBOT COOK
            upper_raw = raw.upper().replace("_", " ")
            if "ROBOTCOOK" in upper_raw:
                return "ROBOT COOK"
            # Format R 5 VV or R 5
            m = re.match(r"^(R|CL|MP|J)\s*(\d+)(.*)$", upper_raw)
            if m:
                family = m.group(1)
                num = m.group(2)
                rest = m.group(3).strip()
                if "VV" in rest or "V.V" in rest:
                    return f"{family} {num} V.V."
                if "GOURMET" in rest:
                    return f"{family} {num} GOURMET"
                return f"{family} {num}"
            return raw

        # Fallback from product name
        m = re.search(r"Robot\s*Cook", name, re.IGNORECASE)
        if m:
            return "ROBOT COOK"
        m = re.search(r"\b(CL|MP|J|R)\s*(\d+)\b", name, re.IGNORECASE)
        if m:
            return f"{m.group(1).upper()} {m.group(2)}"

        return c

    def get_specs(self, code: str, name: str) -> Optional[Dict[str, Any]]:
        """Return canonical specifications for Robot-Coupe machines or accessories."""
        if not self.can_handle(code, name):
            return None

        model = self.extract_model(code, name)
        model_upper = model.upper().strip()

        # Check exact known specs table
        for known_key, specs in _ROBOT_COUPE_CANONICAL.items():
            if model_upper == known_key or model_upper == known_key.replace(" ", ""):
                return specs.copy()

        # Check partial/series match
        for known_key, specs in _ROBOT_COUPE_CANONICAL.items():
            if known_key in model_upper:
                return specs.copy()

        # If it's a 5-digit accessory/disc, return accessory metadata
        if re.match(r"^\d{4,6}$", model_upper):
            return {
                "model_code": model_upper,
                "source_url": f"https://www.robot-coupe.com/en-gb/search?query={model_upper}",
            }

        return {
            "model_code": model,
            "source_url": f"https://www.robot-coupe.com/en-gb/search?query={model.replace(' ', '+')}",
        }
