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
_POWER_KW_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*kW\b", re.IGNORECASE)
_POWER_W_RE = re.compile(r"(?<!\d)(\d{1,2}(?:\s+\d{3})|\d+)\s*W\b", re.IGNORECASE)
_MULTI_POWER_RE = re.compile(r"(\d+)\s*[xX*]\s*(\d+(?:[.,]\d+)?)\s*(k?W)\b", re.IGNORECASE)
_SPLIT_SUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*\+\s*(\d+(?:[.,]\d+)?)\s*(k?W)\b", re.IGNORECASE)
_VOLT_RE = re.compile(r"\b(230|400|12|24|220-240|380-415)\s*V\b", re.IGNORECASE)
_VOLUME_RE = re.compile(r"\b(\d+)\s*(?:l|litr(?:ov|a|y)?)\b", re.IGNORECASE)
_DIMS_3D_RE = re.compile(
    r"(?<!\d)(\d{1,2}(?:\s+\d{3})|\d+(?:[.,]\d+)?)\s*[xX*×]\s*(\d{1,2}(?:\s+\d{3})|\d+(?:[.,]\d+)?)\s*[xX*×]\s*(\d{1,2}(?:\s+\d{3})|\d+(?:[.,]\d+)?)\s*(mm|cm)?(?!\d)",
    re.IGNORECASE,
)
_SUB_COMPONENTS_RE = re.compile(
    r"(drez|vani[cč]k|kom[oô]r|vn[uú]torn|dutin|polic|z[aá]suvk|ro[sš]t|pieck|balen|k[oô][sš]|[lľ]ad|kock|kali[sš]k|vaf[lľ]|zlo[zž]en|panv|n[aá]dob)",
    re.IGNORECASE,
)


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
            full_text = f"{name} {short_desc} {desc}"

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
            if power_param is not None and power_param > 0:
                kw_vals = [float(x.replace(",", ".")) * 1000 for x in _POWER_KW_RE.findall(full_text)]
                w_vals = [float(x.replace(" ", "")) for x in _POWER_W_RE.findall(full_text)]
                multi_vals = []
                for count, p_str, unit in _MULTI_POWER_RE.findall(full_text):
                    mult = 1000.0 if unit.lower() == "kw" else 1.0
                    multi_vals.append(float(count) * float(p_str.replace(",", ".")) * mult)

                split_vals = []
                for a_str, b_str, unit in _SPLIT_SUM_RE.findall(full_text):
                    mult = 1000.0 if unit.lower() == "kw" else 1.0
                    split_vals.append((float(a_str.replace(",", ".")) + float(b_str.replace(",", "."))) * mult)

                all_powers = kw_vals + w_vals + multi_vals + split_vals
                if all_powers:
                    # 2a. Check if ANY detected wattage matches within 15% tolerance
                    matched = any(abs(v - power_param) / max(power_param, 1) <= 0.15 for v in all_powers)
                    # 2b. Check split kW power sum (e.g. 0.24 + 0.12 kW = 0.36 kW = 360 W)
                    if not matched and len(kw_vals) > 1:
                        if abs(sum(kw_vals) - power_param) / max(power_param, 1) <= 0.15:
                            matched = True

                    # 2c. Check multi-zone / multi-burner commercial ranges (e.g. 4 zones * 3.5 kW = 14 kW)
                    burners = _to_float(row.get("filteringProperty:Počet horákov/platní"))
                    if not matched and burners and burners > 1:
                        if any(abs((v * burners) - power_param) / max(power_param, 1) <= 0.15 for v in all_powers):
                            matched = True
                        # Combined hob + oven (e.g. 4x 2.6 kW + 7.5 kW oven = 17.9 kW)
                        elif len(kw_vals) >= 2:
                            for kw_a in kw_vals:
                                for kw_b in kw_vals:
                                    if kw_a != kw_b:
                                        if abs((kw_a * burners + kw_b) - power_param) / max(power_param, 1) <= 0.15:
                                            matched = True
                                            break

                    if not matched:
                        detected_str = f"{all_powers[0]:.0f} W" if all_powers else ""
                        issues.append(
                            {
                                "code": code,
                                "name": name,
                                "category": cat,
                                "source": source,
                                "field": "Príkon (W)",
                                "detected_in_text": detected_str,
                                "param_value": f"{power_param:.0f}",
                                "issue_type": "TEXT_PARAM_MISMATCH",
                                "severity": "WARNING",
                                "description": f"Text mentions power {detected_str} but filter has {power_param:.0f} W",
                            }
                        )

            # 3. Contradiction: Voltage (V)
            volt_param = str(row.get("filteringProperty:Napätie (V)") or "").strip()
            v_matches = _VOLT_RE.findall(full_text)
            if v_matches and volt_param and volt_param.lower() not in ("nan", ""):
                # Normalize voltages (220/230, 380/400)
                norm = lambda v: "230" if "230" in v or "220" in v else ("400" if "400" in v or "380" in v else v)
                param_norm = norm(volt_param)
                is_dual_text = any(("230" in v and "400" in v) or ("220" in v and "380" in v) for v in v_matches)
                is_dual_param = "230" in volt_param and "400" in volt_param

                # Consistent if dual voltage on either side or if any detected voltage matches param
                v_matched = (
                    is_dual_text
                    or is_dual_param
                    or any(norm(v) == param_norm for v in v_matches)
                    or volt_param in ("230/400", "220-240", "380-415")
                )
                if not v_matched:
                    issues.append(
                        {
                            "code": code,
                            "name": name,
                            "category": cat,
                            "source": source,
                            "field": "Napätie (V)",
                            "detected_in_text": v_matches[0],
                            "param_value": volt_param,
                            "issue_type": "TEXT_PARAM_MISMATCH",
                            "severity": "INFO",
                            "description": f"Text mentions {v_matches[0]} V but filter has {volt_param} V",
                        }
                    )

            # 4. Contradiction: Dimensions in text vs filtering properties
            width_p = _to_float(row.get("filteringProperty:Šírka (mm)"))
            depth_p = _to_float(row.get("filteringProperty:Hĺbka (mm)"))
            height_p = _to_float(row.get("filteringProperty:Výška (mm)"))

            if width_p and depth_p and height_p:
                param_dims_sorted = sorted([width_p, depth_p, height_p])
                raw_matches = []
                for match in _DIMS_3D_RE.finditer(full_text):
                    g = match.groups()
                    unit = (g[3] or "mm").lower()
                    mult = 10.0 if unit == "cm" else 1.0
                    dims = [float(g[i].replace(" ", "").replace(",", ".")) * mult for i in range(3)]
                    if any(d < 30 for d in dims):
                        continue
                    start, end = match.start(), match.end()
                    surrounding = full_text[max(0, start - 50) : min(len(full_text), end + 50)]
                    is_sub = bool(_SUB_COMPONENTS_RE.search(surrounding))
                    raw_matches.append((dims, is_sub))

                if raw_matches:
                    # 4a. Check if ANY detected 3D dimension matches filter parameters within 20mm
                    any_matched = False
                    for dims, _ in raw_matches:
                        diffs = [abs(a - b) for a, b in zip(sorted(dims), param_dims_sorted)]
                        if all(d <= 20 for d in diffs):
                            any_matched = True
                            break

                    if not any_matched:
                        # 4b. Check if non-sub-component matches exist
                        non_sub = [dims for dims, is_sub in raw_matches if not is_sub]
                        if non_sub:
                            tw, td, th = non_sub[0]
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
                is_immersion = bool(
                    re.search(
                        r"(sous-vide|cirkul[aá]tor|ponorn[yý]|termocirkul[aá]tor)", f"{name} {cat}", re.IGNORECASE
                    )
                )
                if gross_volume_l > 0 and not is_immersion:
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
