"""
Tests for XLSX data loading functionality (new format).
Following TDD approach: Write tests first, then implement.
"""

import pytest
import pandas as pd
from pathlib import Path
import openpyxl


class TestXLSXLoading:
    """Test XLSX file loading functionality."""
    
    def test_load_xlsx_file(self, test_data_dir):
        """Test loading XLSX file."""
        from src.loaders.xlsx_loader import XLSXLoader
        
        # Create a sample XLSX file for testing
        xlsx_path = test_data_dir / "sample_new_format.xlsx"
        
        # Create sample data
        df = pd.DataFrame({
            'code': ['TEST001', 'TEST002'],
            'name': ['Product 1', 'Product 2'],
            'price': ['100.50', '200.00']
        })
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
        
        loader = XLSXLoader()
        result = loader.load(xlsx_path)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'code' in result.columns
        assert 'name' in result.columns
    
    def test_load_xlsx_with_encoding(self, test_data_dir):
        """Test loading XLSX with special characters."""
        from src.loaders.xlsx_loader import XLSXLoader
        
        xlsx_path = test_data_dir / "sample_special_chars.xlsx"
        
        # Create sample data with special characters
        df = pd.DataFrame({
            'code': ['TEST001'],
            'name': ['Produkt č. 1 - špeciálne znaky'],
            'price': ['100.50']
        })
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
        
        loader = XLSXLoader()
        result = loader.load(xlsx_path)
        
        assert result.loc[0, 'name'] == 'Produkt č. 1 - špeciálne znaky'
    
    def test_load_xlsx_empty_file(self, test_data_dir):
        """Test loading empty XLSX file."""
        from src.loaders.xlsx_loader import XLSXLoader
        
        xlsx_path = test_data_dir / "empty.xlsx"
        
        # Create empty DataFrame
        df = pd.DataFrame()
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
        
        loader = XLSXLoader()
        result = loader.load(xlsx_path)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_load_xlsx_preserves_data_types(self, test_data_dir):
        """Test that XLSX loading preserves data correctly."""
        from src.loaders.xlsx_loader import XLSXLoader
        
        xlsx_path = test_data_dir / "sample_types.xlsx"
        
        # Create sample data with various types
        df = pd.DataFrame({
            'code': ['TEST001', 'TEST002'],
            'name': ['Product 1', 'Product 2'],
            'price': ['100.50', '200.00'],
            'stock': ['10', '20']
        })
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
        
        loader = XLSXLoader()
        result = loader.load(xlsx_path)
        
        # Check data is loaded (note: trailing zeros may be removed by Excel)
        assert result.loc[0, 'code'] == 'TEST001'
        # Price is loaded as string, trailing zeros might be removed
        assert result.loc[0, 'price'] in ['100.50', '100.5']


class TestCSVFallback:
    """Test CSV fallback when XLSX is not available."""
    
    def test_load_csv_as_fallback(self, test_data_dir):
        """Test loading CSV file as fallback."""
        from src.loaders.xlsx_loader import XLSXLoader
        
        csv_path = test_data_dir / "sample_fallback.csv"
        
        # Create CSV file
        df = pd.DataFrame({
            'code': ['TEST001'],
            'name': ['Product 1'],
            'price': ['100.50']
        })
        df.to_csv(csv_path, index=False, sep=';', encoding='utf-8')
        
        loader = XLSXLoader()
        result = loader.load(csv_path)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.loc[0, 'code'] == 'TEST001'


class TestDataLoaderFactory:
    """Test data loader factory for automatic format detection."""
    
    def test_factory_detects_xlsx(self, test_data_dir):
        """Test factory detects XLSX format."""
        from src.loaders.data_loader_factory import DataLoaderFactory
        
        xlsx_path = test_data_dir / "test.xlsx"
        
        # Create sample XLSX
        df = pd.DataFrame({'code': ['TEST001']})
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
        
        loader = DataLoaderFactory.get_loader(xlsx_path)
        
        from src.loaders.xlsx_loader import XLSXLoader
        assert isinstance(loader, XLSXLoader)
    
    def test_factory_detects_csv(self, test_data_dir):
        """Test factory detects CSV format."""
        from src.loaders.data_loader_factory import DataLoaderFactory
        
        csv_path = test_data_dir / "test.csv"
        
        # Create sample CSV
        df = pd.DataFrame({'code': ['TEST001']})
        df.to_csv(csv_path, index=False, sep=';', encoding='utf-8')
        
        loader = DataLoaderFactory.get_loader(csv_path)
        
        from src.loaders.csv_loader import CSVLoader
        assert isinstance(loader, CSVLoader)
    
    def test_factory_load_method(self, test_data_dir):
        """Test factory load method."""
        from src.loaders.data_loader_factory import DataLoaderFactory
        
        xlsx_path = test_data_dir / "test_factory.xlsx"
        
        # Create sample XLSX
        df = pd.DataFrame({
            'code': ['TEST001', 'TEST002'],
            'name': ['Product 1', 'Product 2']
        })
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
        
        result = DataLoaderFactory.load(xlsx_path)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2


class TestXLSXSaving:
    """Test XLSX file saving functionality."""
    
    def test_save_xlsx_file(self, tmp_path):
        """Test saving DataFrame to XLSX."""
        from src.loaders.xlsx_loader import XLSXLoader
        
        df = pd.DataFrame({
            'code': ['TEST001', 'TEST002'],
            'name': ['Product 1', 'Product 2'],
            'price': ['100.50', '200.00']
        })
        
        output_path = tmp_path / "output.xlsx"
        
        loader = XLSXLoader()
        loader.save(df, output_path)
        
        # Verify file was created
        assert output_path.exists()
        
        # Load it back and verify
        loaded_df = pd.read_excel(output_path, engine='openpyxl')
        assert len(loaded_df) == 2
        assert list(loaded_df.columns) == ['code', 'name', 'price']
    
    def test_save_xlsx_with_special_chars(self, tmp_path):
        """Test saving XLSX with special characters."""
        from src.loaders.xlsx_loader import XLSXLoader
        
        df = pd.DataFrame({
            'code': ['TEST001'],
            'name': ['Produkt č. 1 - špeciálne znaky'],
            'defaultCategory': ['Tovary a kategórie > Vitríny']
        })
        
        output_path = tmp_path / "output_special.xlsx"
        
        loader = XLSXLoader()
        loader.save(df, output_path)
        
        # Load it back and verify
        loaded_df = pd.read_excel(output_path, engine='openpyxl')
        assert loaded_df.loc[0, 'name'] == 'Produkt č. 1 - špeciálne znaky'
    
    def test_save_preserves_column_order(self, tmp_path):
        """Test that saving preserves column order."""
        from src.loaders.xlsx_loader import XLSXLoader
        
        columns = ['code', 'name', 'price', 'defaultImage', 'defaultCategory']
        df = pd.DataFrame({col: ['test'] for col in columns})
        
        output_path = tmp_path / "output_order.xlsx"
        
        loader = XLSXLoader()
        loader.save(df, output_path)
        
        # Load it back and verify column order
        loaded_df = pd.read_excel(output_path, engine='openpyxl')
        assert list(loaded_df.columns) == columns


class TestCSVLoader:
    """Test CSV loader for backward compatibility."""
    
    def test_csv_loader_with_semicolon(self, test_data_dir):
        """Test CSV loader with semicolon separator."""
        from src.loaders.csv_loader import CSVLoader
        
        csv_path = test_data_dir / "test_semicolon.csv"
        
        # Create CSV with semicolon
        df = pd.DataFrame({
            'code': ['TEST001'],
            'name': ['Product 1'],
            'price': ['100.50']
        })
        df.to_csv(csv_path, index=False, sep=';', encoding='utf-8')
        
        loader = CSVLoader()
        result = loader.load(csv_path)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
    
    def test_csv_loader_encoding_fallback(self, test_data_dir):
        """Test CSV loader with encoding fallback."""
        from src.loaders.csv_loader import CSVLoader
        
        csv_path = test_data_dir / "test_encoding.csv"
        
        # Create CSV
        df = pd.DataFrame({
            'code': ['TEST001'],
            'name': ['Produkt č. 1']
        })
        df.to_csv(csv_path, index=False, sep=';', encoding='utf-8')
        
        loader = CSVLoader()
        result = loader.load(csv_path)
        
        assert 'code' in result.columns
        assert 'name' in result.columns


class TestDataLoadingIntegration:
    """Test integration of data loading with new format."""
    
    def test_load_new_format_xlsx(self, test_data_dir, config):
        """Test loading new 147-column format from XLSX."""
        from src.loaders.data_loader_factory import DataLoaderFactory
        
        xlsx_path = test_data_dir / "new_format.xlsx"
        
        # Create sample with new format columns
        new_columns = config.get('new_output_columns', [])[:10]  # First 10 for testing
        df = pd.DataFrame({col: ['test'] for col in new_columns})
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
        
        result = DataLoaderFactory.load(xlsx_path)
        
        assert isinstance(result, pd.DataFrame)
        for col in new_columns:
            assert col in result.columns
    
    def test_load_handles_missing_columns(self, test_data_dir):
        """Test loading handles files with missing columns gracefully."""
        from src.loaders.data_loader_factory import DataLoaderFactory
        
        xlsx_path = test_data_dir / "partial_columns.xlsx"
        
        # Create with only some columns
        df = pd.DataFrame({
            'code': ['TEST001'],
            'name': ['Product 1']
        })
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
        
        result = DataLoaderFactory.load(xlsx_path)
        
        # Should load successfully even with missing columns
        assert isinstance(result, pd.DataFrame)
        assert 'code' in result.columns
        assert 'name' in result.columns
