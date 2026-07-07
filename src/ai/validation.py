"""Plausibility checks for filter values (AI-extracted or feed-derived)."""

import re

import pandas as pd

# ponytail: static bounds tuned to gastro equipment; extend the dicts when new outliers show up
PLAUSIBLE_ENUM = {
    "Napätie (V)": {"12", "24", "230", "400", "230/400"},
}
PLAUSIBLE_RANGE = {
    "Šírka (mm)": (50, 6000),
    "Hĺbka (mm)": (50, 6000),
    "Výška (mm)": (30, 6000),
    "Hmotnosť (kg)": (0.1, 2000),
    "Príkon (W)": (5, 100000),
}
_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")


def find_implausible(df: pd.DataFrame) -> pd.DataFrame:
    """Return review rows (code, name, parameter, value, reason) for suspect values."""
    issues = []

    def _add(idx, param, value, reason):
        issues.append({
            "code": str(df.at[idx, "code"]) if "code" in df.columns else "",
            "name": str(df.at[idx, "name"]) if "name" in df.columns else "",
            "parameter": param,
            "value": value,
            "reason": reason,
        })

    for param, allowed in PLAUSIBLE_ENUM.items():
        col = f"filteringProperty:{param}"
        if col not in df.columns:
            continue
        for idx, val in df[col].dropna().items():
            val = str(val).strip()
            if val.endswith(".0"):  # xlsx round-trip turns "230" into 230.0
                val = val[:-2]
            if val and val.lower() != "nan" and val not in allowed:
                _add(idx, param, val, f"not in {sorted(allowed)}")

    for param, (lo, hi) in PLAUSIBLE_RANGE.items():
        col = f"filteringProperty:{param}"
        if col not in df.columns:
            continue
        for idx, val in df[col].dropna().items():
            val = str(val).strip()
            if not val or val.lower() == "nan":
                continue
            m = _NUMBER.search(val)
            if not m:
                _add(idx, param, val, "not numeric")
                continue
            num = float(m.group(0).replace(",", "."))
            if not (lo <= num <= hi):
                _add(idx, param, val, f"outside [{lo}, {hi}]")

    return pd.DataFrame(issues, columns=["code", "name", "parameter", "value", "reason"])
