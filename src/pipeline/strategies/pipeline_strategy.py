from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, Any
import pandas as pd

class PipelineStrategy(ABC):
    """Abstract base class for pipeline strategies."""

    @abstractmethod
    def parse_xml(self, feed_name: str, xml_content: str) -> pd.DataFrame:
        """
        Parse XML feed content.

        Args:
            feed_name: Name of the feed
            xml_content: Content of the XML file

        Returns:
            Parsed DataFrame
        """
        pass

    @abstractmethod
    def merge(self, main_df: pd.DataFrame, feed_dfs: Dict[str, pd.DataFrame], selected_categories: Optional[list]) -> Tuple[pd.DataFrame, Dict]:
        """
        Merge data sources.

        Args:
            main_df: Main data DataFrame
            feed_dfs: Dictionary of feed DataFrames
            selected_categories: List of categories to filter

        Returns:
            Tuple of (merged DataFrame, merge statistics)
        """
        pass

    @abstractmethod
    def map_categories(self, df: pd.DataFrame, enable_interactive: bool = True) -> pd.DataFrame:
        """
        Map categories.

        Args:
            df: DataFrame to map
            enable_interactive: Whether to allow interactive mapping

        Returns:
            DataFrame with mapped categories
        """
        pass

    @abstractmethod
    def apply_transformation(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply final transformation.

        Args:
            df: DataFrame to transform

        Returns:
            Transformed DataFrame
        """
        pass

    @property
    @abstractmethod
    def category_mapper(self) -> Any:
        """Return the category mapper instance."""
        pass

    def calculate_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate statistics from result DataFrame.

        Args:
            df: Result DataFrame

        Returns:
            Dictionary of statistics
        """
        return {}
