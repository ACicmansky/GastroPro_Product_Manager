"""
Tests for CSV data loading functionality (current implementation).
"""

import pytest
import pandas as pd
from pathlib import Path


class TestCurrentCSVLoading:
    """Test current CSV loading functionality."""
    
    def test_load_csv_with_semicolon_separator(self, test_data_dir):
        """Test loading CSV with semicolon separator."""
        csv_path = test_data_dir / "sample_old_format_utf8.csv"
        
        # Load CSV with UTF-8 encoding
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
        
        assert len(df) == 3
        assert 'Kat. číslo' in df.columns
        assert 'Názov tovaru' in df.columns
        
    def test_csv_columns_present(self, test_data_dir):
        """Verify expected columns are present in loaded CSV."""
        csv_path = test_data_dir / "sample_old_format_utf8.csv"
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
        
        expected_columns = [
            'Kat. číslo', 'Názov tovaru', 'Bežná cena', 'Výrobca',
            'Hlavna kategória', 'Krátky popis', 'Dlhý popis', 'Váha',
            'Obrázky', 'Viditeľný', 'Spracovane AI', 'AI_Processed_Date'
        ]
        
        for col in expected_columns:
            assert col in df.columns, f"Column '{col}' not found"
    
    def test_csv_data_types(self, test_data_dir):
        """Test that data is loaded with correct types."""
        csv_path = test_data_dir / "sample_old_format_utf8.csv"
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
        
        # Catalog number and names should be strings/objects
        assert df['Kat. číslo'].dtype == object
        assert df['Názov tovaru'].dtype == object
        # Price might be auto-detected as float or object depending on pandas version
        assert df['Bežná cena'].dtype in [object, 'float64']
    
    def test_empty_catalog_number_detection(self, sample_old_format_df):
        """Test detection of empty catalog numbers."""
        # Add row with empty catalog number
        df = sample_old_format_df.copy()
        df.loc[len(df)] = ['', 'Product without code', '100', 'Mfr', 'Cat', '', '', '', '', '1', 'False', '']
        
        # Filter out empty catalog numbers (as current implementation does)
        filtered_df = df[df['Kat. číslo'].notna() & (df['Kat. číslo'] != '')]
        
        assert len(filtered_df) == 3  # Original 3 products
        assert len(df) == 4  # Before filtering
    
    def test_encoding_fallback(self, test_data_dir):
        """Test that UTF-8 encoding works for our test files."""
        csv_path = test_data_dir / "sample_old_format_utf8.csv"
        
        # Load with UTF-8 (our test files are UTF-8)
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
        
        assert len(df) > 0
        assert 'Kat. číslo' in df.columns


class TestDataFrameBasics:
    """Test basic DataFrame operations used in the application."""
    
    def test_dataframe_copy(self, sample_old_format_df):
        """Test DataFrame copy operation."""
        df_copy = sample_old_format_df.copy()
        
        # Modify copy
        df_copy.loc[0, 'Názov tovaru'] = 'Modified'
        
        # Original should be unchanged
        assert sample_old_format_df.loc[0, 'Názov tovaru'] == 'Product 1'
        assert df_copy.loc[0, 'Názov tovaru'] == 'Modified'
    
    def test_dataframe_filtering(self, sample_old_format_df):
        """Test DataFrame filtering by category."""
        df = sample_old_format_df.copy()
        
        # Filter by category
        filtered = df[df['Hlavna kategória'] == 'Category1/SubCat1']
        
        assert len(filtered) == 2
        assert all(filtered['Hlavna kategória'] == 'Category1/SubCat1')
    
    def test_dataframe_column_addition(self, sample_old_format_df):
        """Test adding new columns to DataFrame."""
        df = sample_old_format_df.copy()
        
        # Add new column
        df['New Column'] = 'default value'
        
        assert 'New Column' in df.columns
        assert all(df['New Column'] == 'default value')
