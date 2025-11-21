"""
Worker for new 138-column format pipeline.
Handles background processing with progress updates.
"""

from PyQt5.QtCore import QObject, pyqtSignal, QEventLoop
import pandas as pd
from typing import Dict, Optional

from src.pipeline.pipeline_new_format import PipelineNewFormat
from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat
from src.scrapers.scraper_new_format import EnhancedScraperNewFormat


class WorkerNewFormat(QObject):
    """Worker for processing data in new 138-column format."""

    finished = pyqtSignal()
    error = pyqtSignal(tuple)  # (title, message)
    progress = pyqtSignal(str)  # progress message
    result = pyqtSignal(object)  # result DataFrame
    statistics = pyqtSignal(dict)  # statistics dict
    category_mapping_request = pyqtSignal(str, str)  # (original_category, product_name)

    def __init__(self, config: Dict, options: Dict):
        """
        Initialize worker.

        Args:
            config: Configuration dictionary
            options: Processing options
        """
        super().__init__()
        self.config = config
        self.options = options
        self.pipeline = PipelineNewFormat(self.config, self.options)
        self.category_mapping_result = None
        self.category_mapping_event_loop = None

    def run(self):
        """Run the complete pipeline."""
        try:
            self.progress.emit("Inicializácia...")

            # Set up interactive category mapping callback
            self.pipeline.category_mapper.set_interactive_callback(
                self._request_category_mapping
            )

            # Prepare XML feeds
            xml_feeds = self._prepare_xml_feeds()

            # Prepare scraped data if requested
            scraped_data = None
            if self.options.get("enable_web_scraping", False):
                scraped_data = self._scrape_products()

            # Get main data file if provided
            main_data_file = self.options.get("main_data_file")

            # Get selected categories
            selected_categories = self.options.get("selected_categories")

            # Run pipeline with category filtering and interactive mapping
            self.progress.emit("Spracovanie feedov...")
            result_df, stats = self.pipeline.run_with_stats(
                xml_feeds=xml_feeds,
                main_data_file=main_data_file,
                scraped_data=scraped_data,
                selected_categories=selected_categories,
                enable_interactive_mapping=True,  # Enable interactive category mapping dialogs
            )

            # Update stats with category info
            if selected_categories:
                stats["filtered_categories"] = len(selected_categories)

            # Apply AI enhancement if requested
            if self.options.get("enable_ai_enhancement", False):
                self.progress.emit("Aplikácia AI vylepšenia...")
                result_df = self._apply_ai_enhancement(result_df, stats)

            # Emit results
            self.progress.emit("Dokončené!")
            self.statistics.emit(stats)
            self.result.emit(result_df)

        except Exception as e:
            import traceback

            error_msg = f"Chyba pri spracovaní:\n{str(e)}\n\n{traceback.format_exc()}"
            self.error.emit(("Chyba spracovania", error_msg))
        finally:
            self.finished.emit()

    def _prepare_xml_feeds(self) -> Dict[str, str]:
        """
        Prepare XML feeds from options.

        Returns:
            Dictionary of feed_name -> xml_content
        """
        xml_feeds = {}

        # Gastromarket
        if self.options.get("enable_gastromarket", False):
            xml_url = (
                self.config.get("xml_feeds", {}).get("gastromarket", {}).get("url")
            )
            if xml_url:
                self.progress.emit("Sťahovanie Gastromarket XML...")
                xml_content = self._download_xml(xml_url)
                if xml_content:
                    xml_feeds["gastromarket"] = xml_content

        # ForGastro
        if self.options.get("enable_forgastro", False):
            xml_url = self.config.get("xml_feeds", {}).get("forgastro", {}).get("url")
            if xml_url:
                self.progress.emit("Sťahovanie ForGastro XML...")
                xml_content = self._download_xml(xml_url)
                if xml_content:
                    xml_feeds["forgastro"] = xml_content

        return xml_feeds

    def _download_xml(self, url: str) -> Optional[str]:
        """
        Download XML from URL.

        Args:
            url: XML feed URL

        Returns:
            XML content as string or None
        """
        try:
            import requests

            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.progress.emit(f"Chyba sťahovania XML: {e}")
            return None

    def _scrape_products(self) -> Optional[pd.DataFrame]:
        """
        Scrape products from TopChladenie.sk.

        Returns:
            DataFrame with scraped products or None
        """
        try:
            self.progress.emit("Web scraping: inicializácia...")

            # Create scraper with progress callback
            scraper = EnhancedScraperNewFormat(
                config=self.config,
                progress_callback=lambda msg: self.progress.emit(
                    f"Web scraping: {msg}"
                ),
                max_threads=8,
            )

            self.progress.emit("Web scraping: spúšťam...")
            scraped_df = scraper.scrape_products()

            self.progress.emit(f"Web scraping: dokončené ({len(scraped_df)} produktov)")
            return scraped_df

        except Exception as e:
            self.progress.emit(f"Web scraping: chyba - {str(e)}")
            return None

    def _apply_ai_enhancement(self, df: pd.DataFrame, stats: Dict) -> pd.DataFrame:
        """
        Apply AI enhancement to products.

        Args:
            df: DataFrame to enhance
            stats: Statistics dict to update

        Returns:
            Enhanced DataFrame
        """
        enhancer = AIEnhancerNewFormat(self.config)

        # Count products to process
        to_process = (
            len(df[df["aiProcessed"] != "1"])
            if "aiProcessed" in df.columns
            else len(df)
        )

        if to_process > 0:
            self.progress.emit(f"AI vylepšenie: {to_process} produktov...")
            result_df, ai_stats = enhancer.enhance_dataframe_with_stats(df)

            # Update statistics
            stats["ai_processed"] = ai_stats.get("newly_processed", 0)
            stats["ai_total"] = ai_stats.get("total_processed", 0)

            return result_df
        else:
            self.progress.emit("AI vylepšenie: všetky produkty už spracované")
            return df

    def _request_category_mapping(
        self, original_category: str, product_name: Optional[str] = None
    ) -> str:
        """
        Request interactive category mapping from GUI.

        This method blocks the worker thread until the user responds in the GUI.

        Args:
            original_category: The unmapped category
            product_name: Optional product name for context

        Returns:
            New category name from user or original if cancelled
        """
        # Reset result
        self.category_mapping_result = None

        # Emit signal to GUI (runs in main thread)
        self.category_mapping_request.emit(original_category, product_name or "")

        # Create event loop to wait for response
        self.category_mapping_event_loop = QEventLoop()
        self.category_mapping_event_loop.exec_()  # Block until set_category_mapping_result is called

        # Return result (or original if None)
        return (
            self.category_mapping_result
            if self.category_mapping_result
            else original_category
        )

    def set_category_mapping_result(self, new_category: str):
        """
        Set the category mapping result from GUI.

        This unblocks the worker thread.

        Args:
            new_category: The new category name from user
        """
        self.category_mapping_result = new_category

        # Quit the event loop to unblock worker thread
        if self.category_mapping_event_loop:
            self.category_mapping_event_loop.quit()
