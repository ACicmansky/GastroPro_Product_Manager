"""Audit engine for detecting factual contradictions and physical plausibility issues in product data."""

import logging
import re
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Regex patterns for extracting numbers with units from text
_INSULATION_RE = re.compile(
    r"(?:izol[aá]ci[a-z]*|hr[uú]bk[a-z]*\s+sten[a-z]*|sten[a-z]*\s+s\s+hr[uú]bk[a-z]*)\s*[:\s-]*(\d+)\s*mm\b",
    re.IGNORECASE,
)
_POWER_KW_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*kW\b", re.IGNORECASE)
_POWER_W_RE = re.compile(r"\b(\d+)\s*W\b", re.IGNORECASE)
_VOLT_RE = re.compile(r"\b(230|400|12|24|220-240|380-415)\s*V\b", re.IGNORECASE)
_VOLUME_RE = re.compile(r"\b(\d+)\s*(?:l|litr(?:ov|a|y)?)\b", re.IGNORECASE)
_DIMS_3D_RE = re.compile(r"\b(\d{2,4})\s*[xX*×]\s*(\d{2,4})\s*[xX*×]\s*(\d{2,4})\b")


def _to_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip().replace(",", ".")
    if not s or s.lower() in ("nan", "none"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(val: Any) -> Optional[int]:
    f = _to_float(val)
    return int(round(f)) if f is not None else None


class CatalogAuditor:
    """Detects contradictions, physical impossibilities, and spec discrepancies in product data."""

    def __init__(self):
        pass

    def audit_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run all audit rules on a DataFrame of products and return issues found."""
        issues: List[Dict[str, Any]] = []

        for idx, row in df.iterrows():
            code = str(row.get("code") or "")
            name = str(row.get("name") or "")
            cat = str(row.get("defaultCategory") or row.get("category") or "")
            source = str(row.get("source") or "")

            short_desc = str(row.get("shortDescription") or "")
            desc = str(row.get("description") or "")
            full_text = f"{short_desc} {desc}"

            # 1. Contradiction: Insulation thickness in text vs filteringProperty
            ins_param = _to_int(row.get("filteringProperty:Hrúbka izolácie (mm)"))
            ins_matches = set(_INSULATION_RE.findall(full_text))
            if len(ins_matches) > 1:
                issues.append(
                    {
                        "code": code,
                        "name": name,
                        "category": cat,
                        "source": source,
                        "field": "Hrúbka izolácie (mm)",
                        "detected_in_text": ", ".join(sorted(ins_matches)),
                        "param_value": str(ins_param) if ins_param is not None else "",
                        "issue_type": "CONFLICTING_TEXT_VALUES",
                        "severity": "WARNING",
                        "description": f"Multiple insulation thicknesses found in text: {ins_matches}",
                    }
                )
            elif ins_matches and ins_param is not None:
                text_val = int(next(iter(ins_matches)))
                if text_val != ins_param:
                    issues.append(
                        {
                            "code": code,
                            "name": name,
                            "category": cat,
                            "source": source,
                            "field": "Hrúbka izolácie (mm)",
                            "detected_in_text": str(text_val),
                            "param_value": str(ins_param),
                            "issue_type": "TEXT_PARAM_MISMATCH",
                            "severity": "ERROR",
                            "description": f"Text states {text_val} mm insulation, but filter parameter is {ins_param} mm",
                        }
                    )

            # 2. Contradiction: Power (W / kW)
            power_param = _to_float(row.get("filteringProperty:Príkon (W)"))
            kw_match = _POWER_KW_RE.search(full_text)
            if kw_match and power_param is not None:
                kw_val = float(kw_match.group(1).replace(",", "."))
                w_from_kw = kw_val * 1000
                # Allow 5% tolerance for rounding (e.g. 0.52 kW vs 508 W)
                if abs(w_from_kw - power_param) / max(power_param, 1) > 0.15:
                    issues.append(
                        {
                            "code": code,
                            "name": name,
                            "category": cat,
                            "source": source,
                            "field": "Príkon (W)",
                            "detected_in_text": f"{kw_val} kW ({w_from_kw:.0f} W)",
                            "param_value": f"{power_param:.0f}",
                            "issue_type": "TEXT_PARAM_MISMATCH",
                            "severity": "WARNING",
                            "description": f"Text states {kw_val} kW ({w_from_kw:.0f} W) but filter has {power_param:.0f} W",
                        }
                    )

            # 3. Contradiction: Voltage (V)
            volt_param = str(row.get("filteringProperty:Napätie (V)") or "").strip()
            volt_match = _VOLT_RE.search(full_text)
            if volt_match and volt_param and volt_param.lower() not in ("nan", ""):
                v_text = volt_match.group(1).replace("-", "/")
                # Normalize 220V / 230V, 380V / 400V
                v_text_norm = "230" if "230" in v_text or "220" in v_text else v_text
                v_param_norm = "230" if "230" in volt_param or "220" in volt_param else volt_param
                if v_text_norm != v_param_norm and volt_param not in ("230/400", "220-240", "380-415"):
                    issues.append(
                        {
                            "code": code,
                            "name": name,
                            "category": cat,
                            "source": source,
                            "field": "Napätie (V)",
                            "detected_in_text": v_text,
                            "param_value": volt_param,
                            "issue_type": "TEXT_PARAM_MISMATCH",
                            "severity": "INFO",
                            "description": f"Text mentions {v_text} V but filter has {volt_param} V",
                        }
                    )

            # 4. Contradiction: Dimensions in text vs filtering properties
            width_p = _to_float(row.get("filteringProperty:Šírka (mm)"))
            depth_p = _to_float(row.get("filteringProperty:Hĺbka (mm)"))
            height_p = _to_float(row.get("filteringProperty:Výška (mm)"))

            dims_match = _DIMS_3D_RE.search(full_text)
            if dims_match and width_p and depth_p and height_p:
                tw, td, th = (
                    float(dims_match.group(1)),
                    float(dims_match.group(2)),
                    float(dims_match.group(3)),
                )
                text_dims_sorted = sorted([tw, td, th])
                param_dims_sorted = sorted([width_p, depth_p, height_p])
                # Check if dimensions diverge significantly (>20mm)
                diffs = [abs(a - b) for a, b in zip(text_dims_sorted, param_dims_sorted)]
                if any(d > 25 for d in diffs):
                    issues.append(
                        {
                            "code": code,
                            "name": name,
                            "category": cat,
                            "source": source,
                            "field": "Rozmery (ŠxHxV)",
                            "detected_in_text": f"{tw:.0f}x{td:.0f}x{th:.0f}",
                            "param_value": f"{width_p:.0f}x{depth_p:.0f}x{height_p:.0f}",
                            "issue_type": "TEXT_PARAM_MISMATCH",
                            "severity": "WARNING",
                            "description": f"Text dimensions {tw:.0f}x{td:.0f}x{th:.0f} diverge from filter {width_p:.0f}x{depth_p:.0f}x{height_p:.0f}",
                        }
                    )

            # 5. Geometric Sanity: Volume vs External Dimensions
            vol_p = _to_float(row.get("filteringProperty:Objem (l)"))
            if vol_p and width_p and depth_p and height_p:
                gross_volume_l = (width_p * depth_p * height_p) / 1_000_000.0
                if gross_volume_l > 0:
                    # Inner net volume cannot exceed external gross volume!
                    if vol_p > gross_volume_l * 1.05:  # Allow 5% tolerance for slight dim rounding
                        issues.append(
                            {
                                "code": code,
                                "name": name,
                                "category": cat,
                                "source": source,
                                "field": "Objem (l)",
                                "detected_in_text": "",
                                "param_value": f"{vol_p:.0f} L (Gross: {gross_volume_l:.0f} L)",
                                "issue_type": "GEOMETRIC_IMPOSSIBILITY",
                                "severity": "ERROR",
                                "description": f"Claimed volume {vol_p:.0f}L exceeds gross outer volume {gross_volume_l:.0f}L ({width_p:.0f}x{depth_p:.0f}x{height_p:.0f}mm)",
                            }
                        )
                    # Also flag if volume is suspiciously tiny (< 5% of external volume for fridges/freezers)
                    elif vol_p < gross_volume_l * 0.1 and "chlad" in cat.lower() and gross_volume_l > 100:
                        issues.append(
                            {
                                "code": code,
                                "name": name,
                                "category": cat,
                                "source": source,
                                "field": "Objem (l)",
                                "detected_in_text": "",
                                "param_value": f"{vol_p:.0f} L (Gross: {gross_volume_l:.0f} L)",
                                "issue_type": "SUSPICIOUS_RATIO",
                                "severity": "WARNING",
                                "description": f"Claimed volume {vol_p:.0f}L is suspiciously small (<10%) for cabinet volume {gross_volume_l:.0f}L",
                            }
                        )

            # 6. Physical Bounds Check
            if power_param is not None and power_param <= 0:
                issues.append(
                    {
                        "code": code,
                        "name": name,
                        "category": cat,
                        "source": source,
                        "field": "Príkon (W)",
                        "detected_in_text": "",
                        "param_value": str(power_param),
                        "issue_type": "OUT_OF_BOUNDS",
                        "severity": "ERROR",
                        "description": "Power must be positive",
                    }
                )

        return pd.DataFrame(
            issues,
            columns=[
                "code",
                "name",
                "category",
                "source",
                "field",
                "detected_in_text",
                "param_value",
                "issue_type",
                "severity",
                "description",
            ],
        )
