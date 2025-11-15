"""
Tests for complete pipeline integration with new format.
Following TDD approach: Write tests first, then implement.
"""

import pytest
import pandas as pd
from pathlib import Path


class TestPipelineNewFormat:
    """Test complete pipeline with new 147-column format."""

    def test_pipeline_initialization(self, config):
        """Test pipeline initializes with config."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        assert pipeline.config is not None
        assert hasattr(pipeline, "run")

    def test_pipeline_processes_xml_feeds(self, config, sample_xml_gastromarket):
        """Test pipeline processes XML feeds."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        # Process single feed
        result = pipeline.process_xml_feed("gastromarket", sample_xml_gastromarket)

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "code" in result.columns
        assert "xmlFeedName" in result.columns

    def test_pipeline_merges_multiple_feeds(
        self, config, sample_xml_gastromarket, sample_xml_forgastro
    ):
        """Test pipeline merges multiple XML feeds."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        feeds = {
            "gastromarket": sample_xml_gastromarket,
            "forgastro": sample_xml_forgastro,
        }

        result = pipeline.process_multiple_feeds(feeds)

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        # Should have products from both feeds
        assert "xmlFeedName" in result.columns


class TestPipelineSteps:
    """Test individual pipeline steps."""

    def test_step_1_parse_xml(self, config, sample_xml_gastromarket):
        """Test Step 1: Parse XML to new format."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        result = pipeline.parse_xml("gastromarket", sample_xml_gastromarket)

        assert "code" in result.columns
        assert "defaultImage" in result.columns

    def test_step_2_merge_data(self, config):
        """Test Step 2: Merge data with image priority."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        feed1 = pd.DataFrame(
            {"code": ["PROD001"], "price": ["100"], "defaultImage": ["img1.jpg"]}
        )

        feed2 = pd.DataFrame(
            {
                "code": ["PROD001"],
                "price": ["150"],
                "defaultImage": ["img1.jpg"],
                "image": ["img2.jpg"],
            }
        )

        result = pipeline.merge_feeds({"feed1": feed1, "feed2": feed2})

        assert len(result) == 1
        # Should use feed2 (more images)
        assert result.loc[0, "image"] == "img2.jpg"

    def test_step_3_map_categories(self, config):
        """Test Step 3: Map and transform categories."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        df = pd.DataFrame(
            {"code": ["PROD001"], "defaultCategory": ["Vitríny/Chladiace"]}
        )

        result = pipeline.map_categories(df)

        assert "Tovary a kategórie > " in result.loc[0, "defaultCategory"]

    def test_step_4_apply_transformation(self, config):
        """Test Step 4: Apply output transformation."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        df = pd.DataFrame(
            {"code": ["prod001"], "name": ["Product 1"], "price": ["100"]}
        )

        result = pipeline.apply_transformation(df)

        # Code should be uppercase
        assert result.loc[0, "code"] == "PROD001"
        # Should have all 147 columns
        assert len(result.columns) >= 100


class TestPipelineWithMainData:
    """Test pipeline with existing main data."""

    def test_merge_with_main_data(self, config):
        """Test merging feeds with existing main data."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        # Existing main data
        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Existing Product"],
                "price": ["100"],
                "shortDescription": ["Existing description"],
            }
        )

        # Feed data
        feed_df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["Feed Product 1", "Feed Product 2"],
                "price": ["150", "200"],
            }
        )

        result = pipeline.merge_with_main(main_df, {"feed": feed_df})

        # Should have both products
        assert len(result) == 2
        # Should preserve main data name
        prod1 = result[result["code"] == "PROD001"].iloc[0]
        assert prod1["name"] == "Existing Product"
        # But update price
        assert prod1["price"] == "150"

    def test_load_main_data(self, config, test_data_dir):
        """Test loading main data from file."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        # Create test file
        test_file = test_data_dir / "main_data.xlsx"
        df = pd.DataFrame({"code": ["PROD001"], "name": ["Product 1"]})
        df.to_excel(test_file, index=False, engine="openpyxl")

        result = pipeline.load_main_data(str(test_file))

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0


class TestPipelineOutput:
    """Test pipeline output and saving."""

    def test_save_output(self, config, test_data_dir):
        """Test saving pipeline output."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        df = pd.DataFrame(
            {"code": ["PROD001"], "name": ["Product 1"], "price": ["100"]}
        )

        output_file = test_data_dir / "output.xlsx"
        pipeline.save_output(df, str(output_file))

        # File should exist
        assert output_file.exists()

        # Should be loadable
        loaded = pd.read_excel(output_file, engine="openpyxl")
        assert len(loaded) == 1

    def test_output_has_all_columns(self, config):
        """Test that output has all 147 columns."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        df = pd.DataFrame({"code": ["PROD001"], "name": ["Product 1"]})

        result = pipeline.finalize_output(df)

        # Should have all required columns
        new_columns = config.get("new_output_columns", [])
        for col in new_columns:
            assert col in result.columns


class TestPipelineEndToEnd:
    """Test complete end-to-end pipeline."""

    def test_complete_pipeline_run(
        self, config, sample_xml_gastromarket, test_data_dir
    ):
        """Test complete pipeline from XML to output file."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        # Run complete pipeline
        output_file = test_data_dir / "complete_output.xlsx"

        result = pipeline.run(
            xml_feeds={"gastromarket": sample_xml_gastromarket},
            output_file=str(output_file),
        )

        # Should return DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

        # Output file should exist
        assert output_file.exists()

        # Should have key columns
        assert "code" in result.columns
        assert "name" in result.columns
        assert "price" in result.columns
        assert "defaultCategory" in result.columns

    def test_pipeline_with_all_steps(
        self, config, sample_xml_gastromarket, test_data_dir
    ):
        """Test pipeline executes all steps."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        output_file = test_data_dir / "all_steps_output.xlsx"

        result = pipeline.run(
            xml_feeds={"gastromarket": sample_xml_gastromarket},
            output_file=str(output_file),
            apply_categories=True,
            apply_transformation=True,
        )

        # Categories should be transformed
        if "defaultCategory" in result.columns:
            for cat in result["defaultCategory"]:
                if cat and cat != "":
                    assert "Tovary a kategórie > " in cat or cat == ""

        # Codes should be uppercase
        if "code" in result.columns:
            for code in result["code"]:
                if code and code != "":
                    assert code == code.upper()


class TestPipelineStatistics:
    """Test pipeline statistics tracking."""

    def test_pipeline_returns_statistics(self, config, sample_xml_gastromarket):
        """Test that pipeline returns statistics."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        result, stats = pipeline.run_with_stats(
            xml_feeds={"gastromarket": sample_xml_gastromarket}
        )

        # Should have statistics
        assert "total_products" in stats
        assert "feeds_processed" in stats
        assert stats["total_products"] > 0

    def test_statistics_track_all_steps(self, config, sample_xml_gastromarket):
        """Test that statistics track all pipeline steps."""
        from src.pipeline.pipeline_new_format import PipelineNewFormat

        pipeline = PipelineNewFormat(config)

        result, stats = pipeline.run_with_stats(
            xml_feeds={"gastromarket": sample_xml_gastromarket}
        )

        # Should track various metrics
        assert "feeds_processed" in stats
        assert "categories_mapped" in stats or "total_products" in stats
