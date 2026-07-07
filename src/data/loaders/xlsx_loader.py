"""XLSX loading. Primary format for the 138-column e-shop data."""

import logging
from pathlib import Path
from typing import Union

import pandas as pd

logger = logging.getLogger(__name__)


def load_xlsx(file_path: Union[str, Path]) -> pd.DataFrame:
    """Load an XLSX file with every column as string (preserves codes/prices)."""
    df = pd.read_excel(Path(file_path), engine="openpyxl")
    for col in df.columns:
        df[col] = df[col].astype(str).replace("nan", "")
    logger.info("Loaded %s: %d rows, %d columns", file_path, len(df), len(df.columns))
    return df
