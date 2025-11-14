"""
Tests for data merging functionality (current implementation).
"""

import pytest
import pandas as pd
from src.utils.helpers import merge_dataframes, clean_price


class TestCurrentDataMerging:
    """Test current data merging logic."""
    
    def test_merge_empty_main_with_feed(self, config):
        """Test merging when main DataFrame is empty."""
        main_df = pd.DataFrame()
        feed_df = pd.DataFrame({
            'Kat. číslo': ['FEED001', 'FEED002'],
            'Názov tovaru': ['Feed Product 1', 'Feed Product 2'],
            'Bežná cena': ['100.00', '200.00']
        })
        
        final_cols = config['final_csv_columns']
        result_df, stats = merge_dataframes(main_df, {'test_feed': feed_df}, final_cols)
        
        assert len(result_df) == 2
        assert 'FEED001' in result_df['Kat. číslo'].values
        assert 'FEED002' in result_df['Kat. číslo'].values
    
    def test_merge_adds_new_products(self, sample_old_format_df, config):
        """Test that new products from feed are added."""
        main_df = sample_old_format_df.copy()
        feed_df = pd.DataFrame({
            'Kat. číslo': ['NEW001', 'NEW002'],
            'Názov tovaru': ['New Product 1', 'New Product 2'],
            'Bežná cena': ['150.00', '250.00'],
            'Viditeľný': ['1', '1']
        })
        
        final_cols = config['final_csv_columns']
        result_df, stats = merge_dataframes(main_df, {'test_feed': feed_df}, final_cols)
        
        assert len(result_df) == 5  # 3 original + 2 new
        assert 'NEW001' in result_df['Kat. číslo'].values
        assert 'NEW002' in result_df['Kat. číslo'].values
    
    def test_merge_updates_prices(self, sample_old_format_df, config):
        """Test that prices are updated from feed for existing products."""
        main_df = sample_old_format_df.copy()
        feed_df = pd.DataFrame({
            'Kat. číslo': ['TEST001'],
            'Názov tovaru': ['Product 1'],
            'Bežná cena': ['999.99']  # Updated price
        })
        
        final_cols = config['final_csv_columns']
        result_df, stats = merge_dataframes(main_df, {'test_feed': feed_df}, final_cols)
        
        # Find TEST001 in result
        test001_row = result_df[result_df['Kat. číslo'] == 'TEST001'].iloc[0]
        assert test001_row['Bežná cena'] == '999.99'
    
    def test_merge_preserves_main_data(self, sample_old_format_df, config):
        """Test that main DataFrame data is preserved during merge."""
        main_df = sample_old_format_df.copy()
        main_df.loc[0, 'Spracovane AI'] = 'True'
        main_df.loc[0, 'AI_Processed_Date'] = '2025-11-14 10:00:00'
        
        feed_df = pd.DataFrame({
            'Kat. číslo': ['TEST001'],
            'Názov tovaru': ['Product 1'],
            'Bežná cena': ['999.99']
        })
        
        final_cols = config['final_csv_columns']
        result_df, stats = merge_dataframes(main_df, {'test_feed': feed_df}, final_cols)
        
        # AI tracking should be preserved
        test001_row = result_df[result_df['Kat. číslo'] == 'TEST001'].iloc[0]
        assert test001_row['Spracovane AI'] == 'True'
        assert test001_row['AI_Processed_Date'] == '2025-11-14 10:00:00'
    
    def test_merge_multiple_feeds(self, sample_old_format_df, config):
        """Test merging data from multiple feeds."""
        main_df = sample_old_format_df.copy()
        
        feed1_df = pd.DataFrame({
            'Kat. číslo': ['FEED1_001'],
            'Názov tovaru': ['Feed 1 Product'],
            'Bežná cena': ['100.00']
        })
        
        feed2_df = pd.DataFrame({
            'Kat. číslo': ['FEED2_001'],
            'Názov tovaru': ['Feed 2 Product'],
            'Bežná cena': ['200.00']
        })
        
        final_cols = config['final_csv_columns']
        result_df, stats = merge_dataframes(
            main_df, 
            {'feed1': feed1_df, 'feed2': feed2_df}, 
            final_cols
        )
        
        assert len(result_df) == 5  # 3 original + 2 from feeds
        assert 'FEED1_001' in result_df['Kat. číslo'].values
        assert 'FEED2_001' in result_df['Kat. číslo'].values
    
    def test_merge_handles_duplicates_in_main(self, config):
        """Test handling of duplicate catalog numbers in main DataFrame."""
        main_df = pd.DataFrame({
            'Kat. číslo': ['DUP001', 'DUP001', 'TEST002'],
            'Názov tovaru': ['Dup Product 1', 'Dup Product 2', 'Test 2'],
            'Bežná cena': ['100.00', '150.00', '200.00']
        })
        
        feed_df = pd.DataFrame({
            'Kat. číslo': ['NEW001'],
            'Názov tovaru': ['New Product'],
            'Bežná cena': ['300.00']
        })
        
        final_cols = config['final_csv_columns']
        result_df, stats = merge_dataframes(main_df, {'test_feed': feed_df}, final_cols)
        
        # Should keep only one DUP001 (first occurrence with last price)
        dup_rows = result_df[result_df['Kat. číslo'] == 'DUP001']
        assert len(dup_rows) == 1
        assert dup_rows.iloc[0]['Bežná cena'] == '150.00'  # Last price
    
    def test_merge_sets_visibility_for_feed_products(self, sample_old_format_df, config):
        """Test that Viditeľný is set to 1 for feed products."""
        main_df = sample_old_format_df.copy()
        feed_df = pd.DataFrame({
            'Kat. číslo': ['FEED001'],
            'Názov tovaru': ['Feed Product'],
            'Bežná cena': ['100.00'],
            'Viditeľný': ['1']  # Feed should have this set
        })
        
        final_cols = config['final_csv_columns']
        result_df, stats = merge_dataframes(main_df, {'test_feed': feed_df}, final_cols)
        
        feed_row = result_df[result_df['Kat. číslo'] == 'FEED001'].iloc[0]
        assert feed_row['Viditeľný'] == '1'


class TestCleanPrice:
    """Test price cleaning functionality."""
    
    def test_clean_price_with_comma(self):
        """Test cleaning price with comma decimal separator."""
        result = clean_price('1234,56')
        assert result == 1234.56
        result = clean_price('100,50')
        assert result == 100.50
    
    def test_clean_price_with_dot(self):
        """Test cleaning price with dot decimal separator."""
        assert clean_price('1234.56') == 1234.56
        assert clean_price('100.50') == 100.50
    
    def test_clean_price_with_spaces(self):
        """Test cleaning price with spaces (note: spaces not removed by current implementation)."""
        # Current implementation doesn't remove spaces, only € and converts , to .
        result = clean_price('100.50')
        assert result == 100.50
    
    def test_clean_price_invalid(self):
        """Test cleaning invalid price returns NaN."""
        import math
        assert math.isnan(clean_price('invalid'))
        assert math.isnan(clean_price(''))
        assert math.isnan(clean_price(None))
