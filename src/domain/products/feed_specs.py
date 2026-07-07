"""Deterministic filter values from structured feed data (ForGastro dims + weight).

Runs AFTER AI enhancement so verified feed numbers win over AI-extracted ones.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

_TO_MM = {"MM": 1.0, "CM": 10.0, "M": 1000.0}
_DIM_TARGETS = [
    ("feedWidth", "filteringProperty:Šírka (mm)"),
    ("feedDepth", "filteringProperty:Hĺbka (mm)"),
    ("feedHeight", "filteringProperty:Výška (mm)"),
]


def _num(val):
    try:
        f = float(str(val).replace(",", "."))
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _fmt(f: float) -> str:
    return str(int(f)) if f == int(f) else str(round(f, 2))


def apply_feed_specs(df: pd.DataFrame) -> pd.DataFrame:
    """Overwrite dimension/weight filters with structured ForGastro feed values."""
    if "source" not in df.columns:
        return df
    mask = df["source"].astype(str).str.lower() == "forgastro"
    written = 0
    for idx in df.index[mask]:
        row = df.loc[idx]
        factor = _TO_MM.get(str(row.get("feedDimUnit") or "MM").strip().upper())
        if factor:
            for src_col, target in _DIM_TARGETS:
                val = _num(row.get(src_col))
                if val is not None:
                    df.at[idx, target] = _fmt(val * factor)
                    written += 1
        weight = _num(row.get("weight"))
        if weight is not None:
            df.at[idx, "filteringProperty:Hmotnosť (kg)"] = _fmt(weight)
            written += 1
    if written:
        logger.info("Feed specs: %d filter values written from ForGastro data", written)
    return df
