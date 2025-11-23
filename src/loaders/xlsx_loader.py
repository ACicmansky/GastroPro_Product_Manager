"""
XLSX Loader for reading and writing Excel files.
Primary format for new 138-column e-shop data.
"""

import pandas as pd
from pathlib import Path
from typing import Union


class XLSXLoader:
    """Loader for XLSX (Excel) files."""

    def __init__(self):
        """Initialize XLSX loader."""
        self.engine = "openpyxl"

    def load(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """
        Load data from XLSX file.

        Args:
            file_path: Path to XLSX file

        Returns:
            DataFrame with loaded data
        """
        file_path = Path(file_path)

        print(f"\nLoading XLSX file: {file_path}")

        try:
            # Load XLSX file
            df = pd.read_excel(file_path, engine=self.engine)

            # Convert all columns to string to preserve data
            for col in df.columns:
                df[col] = df[col].astype(str).replace("nan", "")

            print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")
            return df

        except Exception as e:
            print(f"  Error loading XLSX: {e}")
            raise

    def save(self, df: pd.DataFrame, file_path: Union[str, Path]) -> None:
        """
        Save DataFrame to XLSX file.

        Args:
            df: DataFrame to save
            file_path: Path to output XLSX file
        """
        file_path = Path(file_path)

        print(f"\nSaving to XLSX file: {file_path}")

        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Save to XLSX
            df.to_excel(file_path, index=False, engine=self.engine)

            print(f"  Saved {len(df)} rows, {len(df.columns)} columns")

        except Exception as e:
            print(f"  Error saving XLSX: {e}")
            raise
