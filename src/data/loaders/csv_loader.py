"""CSV Loader with encoding fallback (cp1250 → UTF-8)."""

import pandas as pd
from pathlib import Path
from typing import Union


class CSVLoader:
    """Loader for CSV files with encoding fallback."""

    def __init__(self, separator: str = ";"):
        self.separator = separator

    def load(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """Load CSV, trying cp1250 first then UTF-8."""
        file_path = Path(file_path)
        try:
            df = pd.read_csv(file_path, sep=self.separator, encoding="cp1250")
        except (UnicodeDecodeError, Exception):
            df = pd.read_csv(file_path, sep=self.separator, encoding="utf-8")

        for col in df.columns:
            df[col] = df[col].astype(str).replace("nan", "")
        return df

    def save(self, df: pd.DataFrame, file_path: Union[str, Path], encoding: str = "utf-8") -> None:
        """Save DataFrame to CSV."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(file_path, index=False, sep=self.separator, encoding=encoding, errors="replace")
