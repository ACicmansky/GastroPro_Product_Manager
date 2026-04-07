"""
Tests for complete pipeline integration with new format.
"""

import pytest
import pandas as pd
from pathlib import Path


class TestPipelineNewFormat:
    """Test complete pipeline with new 138-column format."""

    def test_pipeline_processes_xml_feeds(self, config, sample_xml_gastromarket):
        """Test pipeline parses XML feeds."""
        from src.pipeline.pipeline import Pipeline

        pipeline = Pipeline(config)

        result = pipeline.parse_xml("gastromarket", sample_xml_gastromarket)

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "code" in result.columns
        assert "source" in result.columns

    def test_pipeline_merges_multiple_feeds(
        self, config, sample_xml_gastromarket, sample_xml_forgastro
    ):
        """Test pipeline merges multiple XML feeds."""
        from src.pipeline.pipeline import Pipeline

        pipeline = Pipeline(config)

        feed_dfs = {
            "gastromarket": pipeline.parse_xml("gastromarket", sample_xml_gastromarket),
            "forgastro": pipeline.parse_xml("forgastro", sample_xml_forgastro),
        }

        merge_result = pipeline.merger.merge(pd.DataFrame(), feed_dfs)
        result = merge_result.products

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "source" in result.columns


class TestPipelineSteps:
    """Test individual pipeline steps."""

    def test_step_1_parse_xml(self, config, sample_xml_gastromarket):
        """Test Step 1: Parse XML to new format."""
        from src.pipeline.pipeline import Pipeline

        pipeline = Pipeline(config)

        result = pipeline.parse_xml("gastromarket", sample_xml_gastromarket)

        assert "code" in result.columns
        assert "image" in result.columns

    def test_step_2_merge_data(self, config):
        """Test Step 2: Merge data with image priority."""
        from src.pipeline.pipeline import Pipeline

        pipeline = Pipeline(config)

        feed1 = pd.DataFrame(
            {"code": ["PROD001"], "price": ["100"], "image": ["img1.jpg"]}
        )

        feed2 = pd.DataFrame(
            {
                "code": ["PROD001"],
                "price": ["150"],
                "image": ["img1.jpg"],
                "image2": ["img2.jpg"],
            }
        )

        merge_result = pipeline.merger.merge(
            pd.DataFrame(), {"feed1": feed1, "feed2": feed2}
        )
        result = merge_result.products

        assert len(result) == 1
        assert result.loc[0, "image"] == "img1.jpg"

    def test_step_3_map_categories(self, config):
        """Test Step 3: Map and transform categories."""
        from src.pipeline.pipeline import Pipeline

        pipeline = Pipeline(config)

        df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "defaultCategory": ["Nerezový nábytok/Pracovné stoly, pevné"],
            }
        )

        result = pipeline.map_categories(df)

        assert "Gastro Prevádzky a Profesionáli > " in result.loc[0, "defaultCategory"]

    def test_step_4_apply_transformation(self, config):
        """Test Step 4: Apply output transformation."""
        from src.pipeline.pipeline import Pipeline

        pipeline = Pipeline(config)

        df = pd.DataFrame(
            {"code": ["prod001"], "name": ["Product 1"], "price": ["100"]}
        )

        result = pipeline.apply_transformation(df)

        # Transformer uppercases codes
        assert result.loc[0, "code"] == "PROD001"
        assert len(result.columns) >= 100


class TestPipelineWithMainData:
    """Test pipeline with existing main data."""

    def test_merge_with_main_data(self, config):
        """Test merging feeds with existing main data."""
        from src.pipeline.pipeline import Pipeline

        pipeline = Pipeline(config)

        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Existing Product"],
                "price": ["100"],
                "shortDescription": ["Existing description"],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["Feed Product 1", "Feed Product 2"],
                "price": ["150", "200"],
            }
        )

        merge_result = pipeline.merger.merge(main_df, {"feed": feed_df})
        result = merge_result.products

        assert len(result) == 2
        prod1 = result[result["code"] == "PROD001"].iloc[0]
        # Name preserved from main (PRESERVED_FIELDS)
        assert prod1["name"] == "Existing Product"
        # Price updated from feed
        assert prod1["price"] == "150"

    def test_pipeline_preserves_ai_processed_flags(self, config):
        """Test that pipeline maintains aiProcessed flags (main=1, new=0)."""
        from src.pipeline.pipeline import Pipeline

        pipeline = Pipeline(config)

        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Existing Product"],
                "price": ["100"],
                "aiProcessed": ["1"],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["Feed Product 1", "New Feed Product"],
                "price": ["150", "200"],
            }
        )

        merge_result = pipeline.merger.merge(main_df, {"feed": feed_df})
        result = merge_result.products
        result = pipeline.apply_transformation(result)

        assert "aiProcessed" in result.columns

        prod1 = result[result["code"] == "PROD001"].iloc[0]
        assert prod1["aiProcessed"] == "1"

        prod2 = result[result["code"] == "PROD002"].iloc[0]
        assert prod2["aiProcessed"] == "0"

    def test_load_main_data(self, config, test_data_dir):
        """Test loading main data from file."""
        from src.pipeline.pipeline import Pipeline

        pipeline = Pipeline(config)

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
        from src.pipeline.pipeline import Pipeline

        pipeline = Pipeline(config)

        df = pd.DataFrame(
            {"code": ["PROD001"], "name": ["Product 1"], "price": ["100"]}
        )

        output_file = test_data_dir / "output.xlsx"
        pipeline.save_output(df, str(output_file))

        assert output_file.exists()

        loaded = pd.read_excel(output_file, engine="openpyxl")
        assert len(loaded) == 1

    def test_output_has_all_columns(self, config):
        """Test that output has all required columns after transformation."""
        from src.pipeline.pipeline import Pipeline

        pipeline = Pipeline(config)

        df = pd.DataFrame({"code": ["PROD001"], "name": ["Product 1"]})

        result = pipeline.apply_transformation(df)

        from src.config.schema import get_output_columns
        for col in get_output_columns():
            assert col in result.columns
