"""
Tests for OutputTransformer module (new 147-column format).
Following TDD approach: Write tests first, then implement.
"""

import pytest
import pandas as pd
from datetime import datetime


class TestOutputTransformerBasics:
    """Test basic OutputTransformer functionality."""
    
    def test_transformer_initialization(self, config):
        """Test that OutputTransformer initializes correctly."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        assert transformer is not None
        assert transformer.config == config
    
    def test_transformer_has_required_methods(self, config):
        """Test that OutputTransformer has all required methods."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        assert hasattr(transformer, 'transform')
        assert hasattr(transformer, 'apply_direct_mappings')
        assert hasattr(transformer, 'split_images')
        assert hasattr(transformer, 'transform_category')
        assert hasattr(transformer, 'uppercase_code')
        assert hasattr(transformer, 'apply_default_values')


class TestDirectMappings:
    """Test direct column mappings."""
    
    def test_direct_mapping_basic(self, config):
        """Test basic direct mapping from old to new format."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        # Create sample data
        df = pd.DataFrame({
            'Kat. číslo': ['TEST001'],
            'Názov tovaru': ['Product 1'],
            'Bežná cena': ['100.50']
        })
        
        result = transformer.apply_direct_mappings(df)
        
        # Check mapped columns exist
        assert 'code' in result.columns
        assert 'name' in result.columns
        assert 'price' in result.columns
        
        # Check values are mapped correctly
        assert result.loc[0, 'code'] == 'TEST001'
        assert result.loc[0, 'name'] == 'Product 1'
        assert result.loc[0, 'price'] == '100.50'
    
    def test_direct_mapping_all_columns(self, sample_old_format_df, config):
        """Test that all configured direct mappings work."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        result = transformer.apply_direct_mappings(sample_old_format_df)
        
        # Get mappings from config
        mappings = config['output_mapping']['mappings']
        
        # Check that mapped columns exist (only those with source columns in input)
        for old_col, new_col in mappings.items():
            if old_col in sample_old_format_df.columns and new_col != 'Obrázky':
                assert new_col in result.columns, f"Mapped column '{new_col}' not found"


class TestImageSplitting:
    """Test image URL splitting functionality."""
    
    def test_split_single_image(self, config):
        """Test splitting single image URL."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        df = pd.DataFrame({
            'Obrázky': ['http://example.com/img1.jpg']
        })
        
        result = transformer.split_images(df)
        
        # Check all 8 image columns exist
        assert 'defaultImage' in result.columns
        assert 'image' in result.columns
        for i in range(2, 8):
            assert f'image{i}' in result.columns
        
        # Check first image is in defaultImage
        assert result.loc[0, 'defaultImage'] == 'http://example.com/img1.jpg'
        # Other columns should be empty
        assert result.loc[0, 'image'] == ''
    
    def test_split_multiple_images(self, config):
        """Test splitting multiple comma-separated image URLs."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        df = pd.DataFrame({
            'Obrázky': ['http://img1.jpg,http://img2.jpg,http://img3.jpg']
        })
        
        result = transformer.split_images(df)
        
        assert result.loc[0, 'defaultImage'] == 'http://img1.jpg'
        assert result.loc[0, 'image'] == 'http://img2.jpg'
        assert result.loc[0, 'image2'] == 'http://img3.jpg'
        assert result.loc[0, 'image3'] == ''
    
    def test_split_max_8_images(self, config):
        """Test that only first 8 images are kept."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        # Create 10 images
        images = ','.join([f'http://img{i}.jpg' for i in range(1, 11)])
        df = pd.DataFrame({'Obrázky': [images]})
        
        result = transformer.split_images(df)
        
        # Check first 8 are populated
        assert result.loc[0, 'defaultImage'] == 'http://img1.jpg'
        assert result.loc[0, 'image7'] == 'http://img8.jpg'
        # 9th and 10th should not be included
    
    def test_split_empty_images(self, config):
        """Test handling of empty image column."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        df = pd.DataFrame({'Obrázky': ['']})
        
        result = transformer.split_images(df)
        
        # All image columns should be empty
        assert result.loc[0, 'defaultImage'] == ''
        assert result.loc[0, 'image'] == ''


class TestCategoryTransformation:
    """Test category transformation with prefix and separator."""
    
    def test_category_add_prefix(self, config):
        """Test adding 'Tovary a kategórie > ' prefix."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        df = pd.DataFrame({
            'Hlavna kategória': ['Vitríny/Chladiace vitríny']
        })
        
        result = transformer.transform_category(df)
        
        expected = 'Tovary a kategórie > Vitríny > Chladiace vitríny'
        assert result.loc[0, 'defaultCategory'] == expected
        assert result.loc[0, 'categoryText'] == expected
    
    def test_category_replace_separator(self, config):
        """Test replacing '/' with ' > '."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        df = pd.DataFrame({
            'Hlavna kategória': ['Cat1/Cat2/Cat3']
        })
        
        result = transformer.transform_category(df)
        
        expected = 'Tovary a kategórie > Cat1 > Cat2 > Cat3'
        assert result.loc[0, 'defaultCategory'] == expected
    
    def test_category_empty(self, config):
        """Test handling of empty category."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        df = pd.DataFrame({'Hlavna kategória': ['']})
        
        result = transformer.transform_category(df)
        
        # Should still add prefix
        assert result.loc[0, 'defaultCategory'] == 'Tovary a kategórie > '


class TestCodeUppercase:
    """Test catalog code uppercase transformation."""
    
    def test_code_to_uppercase(self, config):
        """Test converting catalog code to uppercase."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        df = pd.DataFrame({
            'code': ['test001', 'Test002', 'TEST003']
        })
        
        result = transformer.uppercase_code(df)
        
        assert result.loc[0, 'code'] == 'TEST001'
        assert result.loc[1, 'code'] == 'TEST002'
        assert result.loc[2, 'code'] == 'TEST003'
    
    def test_code_empty(self, config):
        """Test handling of empty code."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        df = pd.DataFrame({'code': ['']})
        
        result = transformer.uppercase_code(df)
        
        assert result.loc[0, 'code'] == ''


class TestDefaultValues:
    """Test application of default values."""
    
    def test_apply_defaults_to_empty_cells(self, config):
        """Test that defaults are applied only to empty cells."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        df = pd.DataFrame({
            'currency': ['', 'USD'],
            'percentVat': ['', ''],
            'itemType': ['product', '']
        })
        
        result = transformer.apply_default_values(df)
        
        # Empty cells should get defaults
        assert result.loc[0, 'currency'] == 'EUR'
        assert result.loc[0, 'percentVat'] == '23'
        
        # Non-empty cells should be preserved
        assert result.loc[1, 'currency'] == 'USD'
        assert result.loc[0, 'itemType'] == 'product'
        
        # Empty cells should get defaults
        assert result.loc[1, 'itemType'] == 'product'
    
    def test_defaults_from_config(self, config):
        """Test that default values come from config."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        default_values = config['output_mapping']['default_values']
        
        # Create empty DataFrame with columns
        df = pd.DataFrame({col: [''] for col in default_values.keys()})
        
        result = transformer.apply_default_values(df)
        
        # Check all defaults are applied
        for col, default_val in default_values.items():
            if col in result.columns:
                assert result.loc[0, col] == default_val


class TestFullTransformation:
    """Test complete transformation pipeline."""
    
    def test_transform_complete(self, sample_old_format_df, config):
        """Test complete transformation from old to new format."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        result = transformer.transform(sample_old_format_df)
        
        # Check result is DataFrame
        assert isinstance(result, pd.DataFrame)
        
        # Check has 147 columns (or at least 138 if some are missing)
        assert len(result.columns) >= 138
        
        # Check key columns exist
        assert 'code' in result.columns
        assert 'name' in result.columns
        assert 'price' in result.columns
        assert 'defaultImage' in result.columns
        assert 'defaultCategory' in result.columns
        assert 'aiProcessed' in result.columns
    
    def test_transform_preserves_row_count(self, sample_old_format_df, config):
        """Test that transformation preserves number of rows."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        result = transformer.transform(sample_old_format_df)
        
        assert len(result) == len(sample_old_format_df)
    
    def test_transform_all_columns_present(self, sample_old_format_df, config):
        """Test that all 147 columns are present after transformation."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        result = transformer.transform(sample_old_format_df)
        
        new_output_columns = config.get('new_output_columns', [])
        
        # Check all configured columns exist
        for col in new_output_columns:
            assert col in result.columns, f"Column '{col}' missing"
    
    def test_transform_no_formatting(self, sample_old_format_df, config):
        """Test that transformation doesn't format values (raw data)."""
        from src.transformers.output_transformer import OutputTransformer
        
        transformer = OutputTransformer(config)
        
        result = transformer.transform(sample_old_format_df)
        
        # Prices should remain as strings, not formatted
        assert isinstance(result.loc[0, 'price'], str)
