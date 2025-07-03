"""
Data loader service for managing data operations
"""
import pandas as pd
from PyQt5.QtCore import QObject, pyqtSignal

from utils import load_csv_data

class DataManager(QObject):
    """
    Manages data loading, processing, and filtering operations
    Acts as a central data repository for the application
    """
    # Signals
    dataLoaded = pyqtSignal(pd.DataFrame)
    categoriesLoaded = pyqtSignal(list)
    seoPreservedCountUpdated = pyqtSignal(int, pd.DataFrame)
    dataFiltered = pyqtSignal(pd.DataFrame)
    
    def __init__(self):
        super().__init__()
        self.main_df = None
        self.categories = []
        
    def load_csv_file(self, file_path):
        """Load data from CSV file"""
        try:
            self.main_df = load_csv_data(file_path)
            
            if self.main_df is None or self.main_df.empty:
                return False, "CSV súbor je prázdny alebo neobsahuje žiadne dáta."
            
            # Extract categories if the column exists
            if 'Hlavna kategória' in self.main_df.columns:
                self.categories = sorted(self.main_df['Hlavna kategória'].dropna().unique().tolist())
                self.categoriesLoaded.emit(self.categories)
                
                # Signal that data has been loaded successfully
                self.dataLoaded.emit(self.main_df)
                return True, f"Súbor úspešne načítaný: {len(self.main_df)} produktov, {len(self.categories)} kategórií."
            else:
                return False, "V CSV súbore nebol nájdený stĺpec 'Hlavna kategória'. Filtrovanie nie je možné."
                
        except Exception as e:
            return False, f"Nepodarilo sa načítať CSV súbor.\nChyba: {e}"
    
    def filter_data(self, selected_categories, preserve_seo=False):
        """
        Filter data based on selected categories and SEO preservation setting
        Returns a boolean mask for the rows that match the filter criteria
        """
        if self.main_df is None or self.main_df.empty:
            return pd.Series([], dtype=bool)
        
        # Create mask for selected categories
        category_mask = self.main_df['Hlavna kategória'].isin(selected_categories)
        
        # Apply SEO preservation filter if checked
        if preserve_seo:
            seo_mask = (
                (self.main_df['SEO titulka'].notna() & (self.main_df['SEO titulka'] != '')) | 
                (self.main_df['SEO popis'].notna() & (self.main_df['SEO popis'] != '')) | 
                (self.main_df['SEO kľúčové slová'].notna() & (self.main_df['SEO kľúčové slová'] != ''))
            )
            # Either matches category filter or has SEO data
            final_mask = category_mask | seo_mask
            
            # Calculate preserved SEO products (have SEO data but not in selected categories)
            preserved_products = self.main_df[seo_mask & ~category_mask]
            self.seoPreservedCountUpdated.emit(len(preserved_products), preserved_products)
        else:
            final_mask = category_mask
            # No SEO preservation, so no preserved products
            self.seoPreservedCountUpdated.emit(0, pd.DataFrame())
            
        # Get filtered DataFrame
        filtered_df = self.main_df[final_mask].copy()
        self.dataFiltered.emit(filtered_df)
        
        return final_mask
    
    def get_filtered_data(self, selected_categories, preserve_seo=False):
        """
        Get filtered DataFrame based on selected categories and SEO preservation
        """
        mask = self.filter_data(selected_categories, preserve_seo)
        return self.main_df[mask].copy()
    
    def get_categories(self):
        """Get list of available categories"""
        return self.categories.copy()
    
    def get_data(self):
        """Get the main dataframe"""
        return self.main_df.copy() if self.main_df is not None else pd.DataFrame()
    
    def reset(self):
        """Reset the data manager"""
        self.main_df = None
        self.categories = []
