"""Output file writing."""

from pathlib import Path
from typing import Union

import pandas as pd


def write_xlsx(df: pd.DataFrame, file_path: Union[str, Path]):
    """Write DataFrame to XLSX file."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(str(file_path), index=False, engine="openpyxl")
