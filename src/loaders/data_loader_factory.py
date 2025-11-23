"""
Data Loader Factory for automatic format detection.
Detects file format and returns appropriate loader.
"""

from pathlib import Path
from typing import Union
import pandas as pd

from src.loaders.xlsx_loader import XLSXLoader


class DataLoaderFactory:
    """Factory for creating appropriate data loaders based on file type."""

    @staticmethod
    def get_loader(file_path: Union[str, Path]):
        """
        Get appropriate loader based on file extension.

        Args:
            file_path: Path to data file

        Returns:
            Appropriate loader instance (XLSXLoader or CSVLoader)
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()

        if extension in [".xlsx", ".xls"]:
            return XLSXLoader()

    @staticmethod
    def load(file_path: Union[str, Path]) -> pd.DataFrame:
        """
        Load data file automatically detecting format.

        Args:
            file_path: Path to data file

        Returns:
            DataFrame with loaded data
        """
        loader = DataLoaderFactory.get_loader(file_path)
        return loader.load(file_path)

    @staticmethod
    def save(df: pd.DataFrame, file_path: Union[str, Path]) -> None:
        """
        Save DataFrame automatically detecting format from extension.

        Args:
            df: DataFrame to save
            file_path: Path to output file
        """
        loader = DataLoaderFactory.get_loader(file_path)
        loader.save(df, file_path)
