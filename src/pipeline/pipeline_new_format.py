"""
Complete pipeline for new 138-column format.
Integrates all components: XML parsing, merging, category mapping, transformation.
"""

import pandas as pd
from typing import Dict, Tuple, Optional
from pathlib import Path

from src.parsers.xml_parser_new_format import XMLParserNewFormat
from src.mergers.data_merger_new_format import DataMergerNewFormat
from src.mappers.category_mapper_new_format import CategoryMapperNewFormat
from src.transformers.output_transformer import OutputTransformer
from src.loaders.data_loader_factory import DataLoaderFactory


class PipelineNewFormat:
    """Complete pipeline for new format data processing."""

    def __init__(self, config: Dict):
        """
        Initialize pipeline with configuration.

        Args:
            config: Configuration dictionary from config.json
        """
        self.config = config

        # Initialize components
        self.xml_parser = XMLParserNewFormat(config)
        self.merger = DataMergerNewFormat(config)
        self.category_mapper = CategoryMapperNewFormat(config)
        self.transformer = OutputTransformer(config)

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

    def process_xml_feed(self, feed_name: str, xml_content: str) -> pd.DataFrame:
        """
        Process single XML feed.

        Args:
            feed_name: Name of the feed
            xml_content: XML content

        Returns:
            Processed DataFrame
        """
        return self.parse_xml(feed_name, xml_content)

    def process_multiple_feeds(self, feeds: Dict[str, str]) -> pd.DataFrame:
        """
        Process multiple XML feeds and merge them.

        Args:
            feeds: Dictionary of feed_name -> xml_content

        Returns:
            Merged DataFrame
        """
        feed_dfs = {}

        for feed_name, xml_content in feeds.items():
            df = self.parse_xml(feed_name, xml_content)
            feed_dfs[feed_name] = df

        # Merge all feeds
        return self.merger.merge(pd.DataFrame(), feed_dfs)

    def merge_feeds(self, feed_dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Merge multiple feed DataFrames.

        Args:
            feed_dfs: Dictionary of feed_name -> DataFrame

        Returns:
            Merged DataFrame
        """
        return self.merger.merge(pd.DataFrame(), feed_dfs)

    def merge_with_main(
        self, main_df: pd.DataFrame, feed_dfs: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Merge feeds with existing main data.

        Args:
            main_df: Main DataFrame
            feed_dfs: Dictionary of feed DataFrames

        Returns:
            Merged DataFrame
        """
        return self.merger.merge(main_df, feed_dfs)

    def map_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map and transform categories.

        Args:
            df: DataFrame with categories

        Returns:
            DataFrame with transformed categories
        """
        return self.category_mapper.map_dataframe(df)

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

        result_df = df.copy()

        # Ensure all columns exist
        result_df = self.transformer._ensure_all_columns(result_df)

        # Apply defaults
        result_df = self.transformer.apply_default_values(result_df)

        return result_df

    def finalize_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Finalize output with all columns and defaults.

        Args:
            df: DataFrame to finalize

        Returns:
            Finalized DataFrame with all 138 columns
        """
        return self.apply_transformation(df)

    def load_main_data(self, file_path: str) -> pd.DataFrame:
        """
        Load main data from file.

        Args:
            file_path: Path to data file

        Returns:
            Loaded DataFrame
        """
        return DataLoaderFactory.load(file_path)

    def save_output(self, df: pd.DataFrame, file_path: str):
        """
        Save output to file.

        Args:
            df: DataFrame to save
            file_path: Output file path
        """
        DataLoaderFactory.save(df, file_path)
        print(f"\nSaved output to: {file_path}")

    def run(
        self,
        xml_feeds: Dict[str, str],
        output_file: Optional[str] = None,
        main_data_file: Optional[str] = None,
        scraped_data: Optional[pd.DataFrame] = None,
        apply_categories: bool = True,
        apply_transformation: bool = True,
    ) -> pd.DataFrame:
        """
        Run complete pipeline.

        Args:
            xml_feeds: Dictionary of feed_name -> xml_content
            output_file: Optional output file path
            main_data_file: Optional main data file to merge with
            scraped_data: Optional scraped data DataFrame
            apply_categories: Whether to apply category mapping
            apply_transformation: Whether to apply final transformation

        Returns:
            Final DataFrame
        """
        print("\n" + "=" * 60)
        print("PIPELINE EXECUTION - NEW FORMAT")
        print("=" * 60)

        # Step 1: Load main data if provided
        if main_data_file:
            print(f"\nLoading main data from: {main_data_file}")
            main_df = self.load_main_data(main_data_file)
        else:
            main_df = pd.DataFrame()

        # Step 2: Parse XML feeds
        print(f"\nParsing {len(xml_feeds)} XML feed(s)...")
        feed_dfs = {}
        for feed_name, xml_content in xml_feeds.items():
            df = self.parse_xml(feed_name, xml_content)
            feed_dfs[feed_name] = df
            print(f"  Parsed {feed_name}: {len(df)} products")
        
        # Add scraped data if provided
        if scraped_data is not None and not scraped_data.empty:
            feed_dfs["web_scraping"] = scraped_data
            print(f"  Added scraped data: {len(scraped_data)} products")

        # Step 3: Merge data
        print("\nMerging data with image priority...")
        merged_df = self.merger.merge(main_df, feed_dfs)
        print(f"  Total products after merge: {len(merged_df)}")

        # Step 4: Map categories (optional)
        if apply_categories:
            print("\nMapping categories...")
            merged_df = self.map_categories(merged_df)

        # Step 5: Apply transformation (optional)
        if apply_transformation:
            print("\nApplying final transformation...")
            result_df = self.apply_transformation(merged_df)
        else:
            result_df = merged_df

        # Step 6: Save output if path provided
        if output_file:
            self.save_output(result_df, output_file)

        print("\n" + "=" * 60)
        print(f"PIPELINE COMPLETE: {len(result_df)} products")
        print("=" * 60)

        return result_df

    def run_with_stats(
        self,
        xml_feeds: Dict[str, str],
        output_file: Optional[str] = None,
        main_data_file: Optional[str] = None,
        scraped_data: Optional[pd.DataFrame] = None,
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Run pipeline and return statistics.

        Args:
            xml_feeds: Dictionary of feed_name -> xml_content
            output_file: Optional output file path
            main_data_file: Optional main data file
            scraped_data: Optional scraped data DataFrame

        Returns:
            Tuple of (result DataFrame, statistics dict)
        """
        # Run pipeline
        result_df = self.run(xml_feeds, output_file, main_data_file, scraped_data)

        # Calculate statistics
        stats = {
            "total_products": len(result_df),
            "feeds_processed": len(xml_feeds),
            "categories_mapped": (
                (
                    result_df["defaultCategory"].str.contains(
                        "Tovary a kategórie > ", na=False
                    )
                ).sum()
                if "defaultCategory" in result_df.columns
                else 0
            ),
        }

        return result_df, stats
