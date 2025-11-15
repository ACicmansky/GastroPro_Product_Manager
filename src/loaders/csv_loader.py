"""
CSV Loader for reading CSV files with encoding fallback.
Supports both old format (cp1250) and new format (UTF-8).
"""

import pandas as pd
from pathlib import Path
from typing import Union


class CSVLoader:
    """Loader for CSV files with encoding fallback."""

    def __init__(self, separator: str = ";"):
        """
        Initialize CSV loader.

        Args:
            separator: CSV separator (default: semicolon)
        """
        self.separator = separator

    def load(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """
        Load data from CSV file with encoding fallback.

        Tries cp1250 first (old format), then UTF-8 (new format).

        Args:
            file_path: Path to CSV file

        Returns:
            DataFrame with loaded data
        """
        file_path = Path(file_path)

        print(f"\nLoading CSV file: {file_path}")

        # Try cp1250 first (old format)
        try:
            df = pd.read_csv(file_path, sep=self.separator, encoding="cp1250")
            print(f"  Loaded with cp1250 encoding")
        except (UnicodeDecodeError, Exception):
            # Fallback to UTF-8
            try:
                df = pd.read_csv(file_path, sep=self.separator, encoding="utf-8")
                print(f"  Loaded with UTF-8 encoding")
            except Exception as e:
                print(f"  Error loading CSV: {e}")
                raise

        # Convert all columns to string to preserve data
        for col in df.columns:
            if col in df.columns:
                df[col] = df[col].astype(str).replace("nan", "")

        print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")
        return df

    def save(
        self, df: pd.DataFrame, file_path: Union[str, Path], encoding: str = "utf-8"
    ) -> None:
        """
        Save DataFrame to CSV file.

        Args:
            df: DataFrame to save
            file_path: Path to output CSV file
            encoding: File encoding (default: utf-8)
        """
        file_path = Path(file_path)

        print(f"\nSaving to CSV file: {file_path}")

        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Save to CSV
            df.to_csv(
                file_path,
                index=False,
                sep=self.separator,
                encoding=encoding,
                errors="replace",
            )

            print(f"  Saved {len(df)} rows, {len(df.columns)} columns")

        except Exception as e:
            print(f"  Error saving CSV: {e}")
            raise
