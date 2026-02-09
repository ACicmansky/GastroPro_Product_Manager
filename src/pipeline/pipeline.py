import pandas as pd
from typing import Dict, Tuple, Optional, Any

from src.pipeline.strategies.pipeline_strategy import PipelineStrategy
from src.loaders.data_loader_factory import DataLoaderFactory


class Pipeline:
    """Generic pipeline for data processing using strategy pattern."""

    def __init__(self, strategy: PipelineStrategy):
        """
        Initialize pipeline with strategy.

        Args:
            strategy: Concrete PipelineStrategy instance
        """
        self.strategy = strategy
        self._last_merge_stats = {}

    @property
    def category_mapper(self):
        """Return the category mapper instance from strategy."""
        return self.strategy.category_mapper

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
        selected_categories: Optional[list] = None,
        enable_interactive_mapping: bool = True,
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
            selected_categories: Optional list of selected categories for filtering
            enable_interactive_mapping: Whether to enable interactive category mapping dialogs

        Returns:
            Final DataFrame
        """
        print("\n" + "=" * 60)
        print("PIPELINE EXECUTION")
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
            df = self.strategy.parse_xml(feed_name, xml_content)
            feed_dfs[feed_name] = df
            print(f"  Parsed {feed_name}: {len(df)} products")

        # Add scraped data if provided
        if scraped_data is not None and not scraped_data.empty:
            feed_dfs["web_scraping"] = scraped_data
            print(f"  Added scraped data: {len(scraped_data)} products")

        # Step 3: Merge data
        self._last_merge_stats = {}
        print("\nMerging data...")
        merged_df, self._last_merge_stats = self.strategy.merge(
            main_df, feed_dfs, selected_categories
        )
        print(f"  Total products after merge: {len(merged_df)}")

        # Step 4: Map categories (optional)
        if apply_categories:
            print("\nMapping categories...")
            merged_df = self.strategy.map_categories(
                merged_df, enable_interactive=enable_interactive_mapping
            )

        # Step 5: Apply transformation (optional)
        if apply_transformation:
            print("\nApplying final transformation...")
            result_df = self.strategy.apply_transformation(merged_df)
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
        selected_categories: Optional[list] = None,
        enable_interactive_mapping: bool = True,
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Run pipeline and return statistics.

        Args:
            xml_feeds: Dictionary of feed_name -> xml_content
            output_file: Optional output file path
            main_data_file: Optional main data file
            scraped_data: Optional scraped data DataFrame
            selected_categories: Optional list of selected categories for filtering
            enable_interactive_mapping: Whether to enable interactive category mapping dialogs

        Returns:
            Tuple of (result DataFrame, statistics dict)
        """
        # Run pipeline
        result_df = self.run(
            xml_feeds,
            output_file,
            main_data_file,
            scraped_data,
            selected_categories=selected_categories,
            enable_interactive_mapping=enable_interactive_mapping,
        )

        # Calculate statistics
        stats = {
            "total_products": len(result_df),
            "feeds_processed": len(xml_feeds),
        }

        # Add strategy-specific stats
        stats.update(self.strategy.calculate_stats(result_df))

        # Add merge statistics if available
        if self._last_merge_stats:
            stats.update(self._last_merge_stats)

        return result_df, stats
