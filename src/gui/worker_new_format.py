"""
Worker for new 147-column format pipeline.
Handles background processing with progress updates.
"""

from PyQt5.QtCore import QObject, pyqtSignal
import pandas as pd
from typing import Dict, Optional

from src.pipeline.pipeline_new_format import PipelineNewFormat
from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat


class WorkerNewFormat(QObject):
    """Worker for processing data in new 147-column format."""

    finished = pyqtSignal()
    error = pyqtSignal(tuple)  # (title, message)
    progress = pyqtSignal(str)  # progress message
    result = pyqtSignal(object)  # result DataFrame
    statistics = pyqtSignal(dict)  # statistics dict

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
        self.pipeline = PipelineNewFormat(config)

    def run(self):
        """Run the complete pipeline."""
        try:
            self.progress.emit("Inicializácia...")

            # Prepare XML feeds
            xml_feeds = self._prepare_xml_feeds()

            # Get main data file if provided
            main_data_file = self.options.get("main_data_file")

            # Run pipeline
            self.progress.emit("Spracovanie XML feedov...")
            result_df, stats = self.pipeline.run_with_stats(
                xml_feeds=xml_feeds, main_data_file=main_data_file
            )

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
