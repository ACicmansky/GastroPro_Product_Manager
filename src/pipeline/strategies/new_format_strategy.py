from typing import Dict, Optional, Tuple, Any
import pandas as pd

from src.pipeline.strategies.pipeline_strategy import PipelineStrategy

from src.parsers.xml_parser_new_format import XMLParserNewFormat
from src.mergers.data_merger_new_format import DataMergerNewFormat
from src.mappers.category_mapper_new_format import CategoryMapperNewFormat
from src.transformers.output_transformer import OutputTransformer


class NewFormatStrategy(PipelineStrategy):
    """Strategy for new 138-column format data processing."""

    def __init__(self, config: Dict, options: Dict):
        """
        Initialize strategy with configuration.

        Args:
            config: Configuration dictionary from config.json
            options: Options from GUI
        """
        # Initialize components
        self.xml_parser = XMLParserNewFormat(config)
        self.merger = DataMergerNewFormat(options)
        self._category_mapper = CategoryMapperNewFormat(config)
        self.transformer = OutputTransformer(config)
        self._last_merge_stats = {}

    @property
    def category_mapper(self) -> CategoryMapperNewFormat:
        return self._category_mapper

    def parse_xml(self, feed_name: str, xml_content: str) -> pd.DataFrame:
        """
        Parse XML feed to new format.

        Args:
            feed_name: Name of the feed
            xml_content: XML content as string

        Returns:
            Parsed DataFrame
        """
        if feed_name.lower() == "gastromarket":
            return self.xml_parser.parse_gastromarket(xml_content)
        elif feed_name.lower() == "forgastro":
            return self.xml_parser.parse_forgastro(xml_content)
        else:
            raise ValueError(f"Unknown feed: {feed_name}")

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
        merged_df, stats = self.merger.merge(
            main_df, feed_dfs, selected_categories
        )
        self._last_merge_stats = stats
        return merged_df, stats

    def map_categories(self, df: pd.DataFrame, enable_interactive: bool = True) -> pd.DataFrame:
        """
        Map categories.

        Args:
            df: DataFrame to map
            enable_interactive: Whether to allow interactive mapping

        Returns:
            DataFrame with mapped categories
        """
        return self._category_mapper.map_dataframe(
            df, enable_interactive=enable_interactive
        )

    def apply_transformation(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply output transformation (uppercase codes, all columns, defaults).

        For data already in new format, just ensure columns and apply defaults.

        Args:
            df: DataFrame to transform

        Returns:
            Transformed DataFrame
        """
        # Data from XML is already in new format, so we just:
        # 1. Ensure all columns exist
        # 2. Apply defaults
        # 3. Change GastroMarket to Gastro in shortDescription, description, metaDescription, seoTitle

        result_df = df.copy()

        result_df = self.transformer._ensure_all_columns(result_df)

        result_df = self.transformer.apply_default_values(result_df)

        result_df = self.transformer._change_GastroMarket_string(result_df)

        result_df = self.transformer._update_variantVisibility(result_df)

        return result_df

    def calculate_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate statistics from result DataFrame.

        Args:
            df: Result DataFrame

        Returns:
            Dictionary of statistics
        """
        stats = {}
        if "defaultCategory" in df.columns:
            stats["categories_mapped"] = (
                df["defaultCategory"].str.contains("Tovary a kategórie > ", na=False)
            ).sum()
        else:
            stats["categories_mapped"] = 0

        return stats
