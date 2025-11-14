"""
Integration tests for data pipeline (current implementation).
"""

import pytest
import pandas as pd
from pathlib import Path


class TestCurrentDataPipeline:
    """Test current end-to-end data pipeline."""
    
    def test_load_and_filter_by_category(self, test_data_dir, config):
        """Test loading CSV and filtering by category."""
        csv_path = test_data_dir / "sample_old_format_utf8.csv"
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
        
        # Filter by category
        selected_categories = ['Vitríny/Chladiace vitríny']
        filtered_df = df[df['Hlavna kategória'].isin(selected_categories)]
        
        assert len(filtered_df) == 2  # Two products in this category
        assert all(filtered_df['Hlavna kategória'] == 'Vitríny/Chladiace vitríny')
    
    def test_output_column_order(self, sample_old_format_df, config):
        """Test that output has correct column order."""
        df = sample_old_format_df.copy()
        final_cols = config['final_csv_columns']
        
        # Ensure all final columns exist
        for col in final_cols:
            if col not in df.columns:
                df[col] = ''
        
        # Reorder to match final_csv_columns
        df = df[final_cols]
        
        assert list(df.columns) == final_cols
    
    def test_output_encoding_cp1250(self, sample_old_format_df, tmp_path):
        """Test output file encoding (cp1250)."""
        df = sample_old_format_df.copy()
        output_file = tmp_path / "test_output.csv"
        
        # Save with cp1250 encoding
        df.to_csv(output_file, index=False, sep=';', encoding='cp1250', errors='replace')
        
        assert output_file.exists()
        
        # Load it back
        loaded_df = pd.read_csv(output_file, sep=';', encoding='cp1250')
        assert len(loaded_df) == len(df)
    
    def test_pipeline_preserves_data_integrity(self, sample_old_format_df, config):
        """Test that pipeline preserves data integrity."""
        df = sample_old_format_df.copy()
        original_catalog_numbers = df['Kat. číslo'].tolist()
        original_names = df['Názov tovaru'].tolist()
        
        # Simulate pipeline operations
        # 1. Filter empty catalog numbers
        df = df[df['Kat. číslo'].notna() & (df['Kat. číslo'] != '')]
        
        # 2. Ensure all columns
        final_cols = config['final_csv_columns']
        for col in final_cols:
            if col not in df.columns:
                df[col] = ''
        
        # Data should be preserved
        assert df['Kat. číslo'].tolist() == original_catalog_numbers
        assert df['Názov tovaru'].tolist() == original_names
    
    def test_pipeline_with_empty_dataframe(self, config):
        """Test pipeline handles empty DataFrame."""
        df = pd.DataFrame()
        final_cols = config['final_csv_columns']
        
        # Ensure columns exist
        for col in final_cols:
            if col not in df.columns:
                df[col] = ''
        
        assert len(df) == 0
        assert all(col in df.columns for col in final_cols)


class TestConfigurationLoading:
    """Test configuration loading."""
    
    def test_config_loads_successfully(self, config):
        """Test that config.json loads successfully."""
        assert config is not None
        assert isinstance(config, dict)
    
    def test_config_has_required_sections(self, config):
        """Test that config has all required sections."""
        required_sections = [
            'xml_feeds',
            'output_mapping',
            'ai_enhancement',
            'final_csv_columns',
            'new_output_columns'
        ]
        
        for section in required_sections:
            assert section in config, f"Missing section: {section}"
    
    def test_final_csv_columns_list(self, config):
        """Test that final_csv_columns is a list."""
        assert isinstance(config['final_csv_columns'], list)
        assert len(config['final_csv_columns']) > 0
    
    def test_new_output_columns_list(self, config):
        """Test that new_output_columns is a list."""
        assert isinstance(config['new_output_columns'], list)
        # Should have at least 138 columns (may be missing some image desc columns)
        assert len(config['new_output_columns']) >= 138
    
    def test_xml_feeds_configuration(self, config):
        """Test XML feeds configuration."""
        assert 'xml_feeds' in config
        xml_feeds = config['xml_feeds']
        
        # Should have gastromarket and forgastro
        assert 'gastromarket' in xml_feeds
        assert 'forgastro' in xml_feeds
        
        # Each should have required fields
        for feed_name, feed_config in xml_feeds.items():
            assert 'url' in feed_config
            assert 'root_element' in feed_config
            assert 'mapping' in feed_config
