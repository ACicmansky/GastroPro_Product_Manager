# src/core/data_pipeline.py
import logging
import pandas as pd

from .models import PipelineResult
from ..services.scraper import get_scraped_products
from ..services.variant_matcher import ProductVariantMatcher
from ..services.ai_enhancer import AIEnhancementProcessor
from ..utils.config_loader import CategoryMappingManager
from ..utils.category_mapper import map_dataframe_categories
from ..utils.feed_processor import fetch_xml_feed, parse_xml_feed
from ..utils.helpers import merge_dataframes, clean_html_text

logger = logging.getLogger(__name__)

class DataPipeline:
    def __init__(self, config, progress_callback=None, category_mapping_callback=None):
        self.config = config
        self.progress_callback = progress_callback
        self.category_mapping_callback = category_mapping_callback
        # Initialize centralized category mapping manager
        self.category_manager = CategoryMappingManager()

    def _log_progress(self, message):
        if self.progress_callback:
            self.progress_callback(message)

    def run(self, main_df, selected_categories, options):
        try:
            # Step 1: Filter main dataframe
            self._log_progress("Filtering main CSV by selected categories...")
            if selected_categories:
                filtered_df = main_df[main_df['Hlavna kategória'].isin(selected_categories)].copy()
            else:
                filtered_df = pd.DataFrame()
            self._log_progress(f"Filtered to {len(filtered_df)} products.")

            # Step 2: Category Mapping
            if options.get('map_categories') and 'Hlavna kategória' in filtered_df.columns:
                self._log_progress("Applying category mappings...")
                category_mappings = self.category_manager.get_all()
                if category_mappings:
                    filtered_df = map_dataframe_categories(filtered_df, category_mappings)

            # Step 3: XML Feeds
            feed_dataframes = self._process_feeds(options)
            gastromarket_count = len(feed_dataframes.get('gastromarket', []))
            forgastro_count = len(feed_dataframes.get('forgastro', []))

            # Step 4: Scraped Data
            if options.get('scrape_topchladenie'):
                scraped_df, topchladenie_count = self._process_scraping(options)
            else:
                scraped_df = pd.DataFrame()
                topchladenie_count = 0

            # Step 5: Clean and Merge
            self._log_progress("Cleaning and merging all data sources...")
            final_df, merge_stats = self._clean_and_merge(filtered_df, feed_dataframes, scraped_df)

            # Step 6: Variant Matching
            if options.get('variant_checkbox'):
                self._log_progress("Analyzing products for variant detection...")
                variant_matcher = ProductVariantMatcher(progress_callback=self._log_progress)
                final_df, group_data = variant_matcher.identify_variants(final_df, generate_report=True)
                self._log_progress("Extracting product dimensions and differences...")
                variant_matcher.extract_product_differences(final_df, group_data)

            # Step 7: AI Enhancement
            ai_stats = {}
            if options.get('ai_enhancement_checkbox') and self.config.get('ai_enhancement', {}).get('enabled', False):
                final_df, ai_stats = self._run_ai_enhancement(final_df)

            # Prepare statistics
            statistics = {
                'original_csv': len(filtered_df),
                'gastromarket': gastromarket_count,
                'forgastro': forgastro_count,
                'topchladenie': topchladenie_count,
                'total': len(final_df),
                'merge_stats': merge_stats
            }
            statistics.update(ai_stats)

            self._log_progress(f"Final dataset ready with {len(final_df)} total products.")
            return PipelineResult(dataframe=final_df, statistics=statistics)

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            raise

    def _process_feeds(self, options):
        feed_dataframes = {}
        enabled_feeds = []
        if options.get('enable_gastromarket'):
            enabled_feeds.append('gastromarket')
        if options.get('enable_forgastro'):
            enabled_feeds.append('forgastro')

        if not enabled_feeds:
            self._log_progress("No XML feeds enabled.")
            return {}

        self._log_progress(f"Fetching {len(enabled_feeds)} XML feeds...")
        for feed_name in enabled_feeds:
            try:
                feed_info = self.config['xml_feeds'][feed_name]
                self._log_progress(f"Fetching feed: {feed_name}")
                root = fetch_xml_feed(feed_info['url'])
                if root is not None:
                    self._log_progress(f"Parsing feed: {feed_name}")
                    df = parse_xml_feed(
                        root, 
                        feed_info['root_element'], 
                        feed_info['mapping'], 
                        feed_name,
                        category_manager=self.category_manager,
                        category_mapping_callback=self.category_mapping_callback
                    )
                    if df is not None and not df.empty:
                        feed_dataframes[feed_name] = df
                        self._log_progress(f"Parsed {len(df)} products from {feed_name}")
            except Exception as e:
                logger.error(f"Error processing feed {feed_name}: {e}")
        return feed_dataframes

    def _process_scraping(self, options):
        scraped_df = None
        topchladenie_count = 0
        if options.get('scrape_topchladenie'):
            self._log_progress("Scraping latest data from Topchladenie.sk...")
            scraped_df = get_scraped_products(
                use_fast_scraper=True, 
                progress_callback=lambda x: self._log_progress(x),
                category_manager=self.category_manager,
                category_mapping_callback=self.category_mapping_callback
            )
            if scraped_df is not None and not scraped_df.empty:
                topchladenie_count = len(scraped_df)
                self._log_progress(f"Scraped {topchladenie_count} products.")
        elif options.get('topchladenie_csv_df') is not None:
            self._log_progress("Using loaded Topchladenie.sk CSV data...")
            scraped_df = options['topchladenie_csv_df'].copy()
            topchladenie_count = len(scraped_df)
        return scraped_df, topchladenie_count

    def _clean_and_merge(self, main_df, feed_dfs, scraped_df):
        join_column = "Kat. číslo"

        def clean_df(df, name):
            if df is None or df.empty or join_column not in df.columns:
                return pd.DataFrame(columns=df.columns if df is not None else [])
            before_count = len(df)
            cleaned = df[df[join_column].notna() & (df[join_column].str.strip() != "")]
            removed = before_count - len(cleaned)
            if removed > 0:
                self._log_progress(f"Removed {removed} products with empty catalog numbers from {name}")
            return cleaned

        main_df_cleaned = clean_df(main_df, "main CSV")
        if 'Kat. číslo rodiča' in main_df_cleaned.columns:
            main_df_cleaned['Kat. číslo rodiča'] = main_df_cleaned['Kat. číslo rodiča'].replace([0, "0"], "")

        cleaned_feed_dfs = {name: clean_df(df, name) for name, df in feed_dfs.items()}
        scraped_df_cleaned = clean_df(scraped_df, "scraped data")

        # For merging, combine all data sources into one dictionary
        all_sources_to_merge = cleaned_feed_dfs.copy()
        if scraped_df_cleaned is not None and not scraped_df_cleaned.empty:
            all_sources_to_merge['topchladenie'] = scraped_df_cleaned

        final_df, merge_stats = merge_dataframes(main_df_cleaned, all_sources_to_merge, self.config['final_csv_columns'])
        
        # Final cleaning - EXCLUDE AI tracking columns to prevent corruption
        ai_tracking_columns = {'Spracovane AI', 'AI_Processed_Date'}
        for col in final_df.columns:
            if col not in ai_tracking_columns and final_df[col].dtype == 'object':
                final_df[col] = final_df[col].fillna("").astype(str).replace("nan", "").str.strip()

        for col in ['Krátky popis', 'Dlhý popis', 'Názov tovaru']:
            if col in final_df.columns:
                final_df[col] = final_df[col].apply(clean_html_text)
        
        final_df.loc[final_df['Názov tovaru'].isin([None, ""]), 'Názov tovaru'] = final_df['Kat. číslo']

        return final_df, merge_stats

    def _run_ai_enhancement(self, df):
        self._log_progress("Enhancing product descriptions with AI...")
        try:
            ai_processor = AIEnhancementProcessor(self.config.get('ai_enhancement', {}))
            
            def ai_progress_callback(processed, total):
                self._log_progress(f"AI enhancement: {processed}/{total} products processed")
            
            return ai_processor.process_dataframe(df, progress_callback=ai_progress_callback)
        except ImportError as e:
            self._log_progress(f"AI enhancement: Required packages not installed - {e}")
        except Exception as e:
            self._log_progress(f"AI enhancement: Error - {str(e)}")
        return df, {}
