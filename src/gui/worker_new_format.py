"""
Worker for new 138-column format pipeline.
Handles background processing with progress updates.
"""

from PyQt5.QtCore import QObject, pyqtSignal, QEventLoop
import pandas as pd
from typing import Dict, Optional
from pathlib import Path

from src.pipeline.pipeline_new_format import PipelineNewFormat
from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat
from src.scrapers.mebella_scraper import MebellaScraper
from src.scrapers.topchladenie_scraper import TopchladenieScraper


class WorkerNewFormat(QObject):
    """Worker for processing data in new 138-column format."""

    finished = pyqtSignal()
    error = pyqtSignal(tuple)  # (title, message)
    progress = pyqtSignal(str)  # progress message
    result = pyqtSignal(object)  # result DataFrame
    statistics = pyqtSignal(dict)  # statistics dict
    category_mapping_request = pyqtSignal(str, str)  # (original_category, product_name)
    price_mapping_request = pyqtSignal(dict, object)  # (product_data, prices_df)

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
        self.price_mapping_result = None
        self.price_mapping_event_loop = None

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
            if self.options.get("enable_web_scraping", False) or self.options.get(
                "enable_mebella_scraping", False
            ):
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
            all_scraped_dfs = []

            # 1. TopChladenie.sk
            if self.options.get("enable_web_scraping", False):
                self.progress.emit("Web scraping (TopChladenie.sk): spúšťam...")
                scraper = TopchladenieScraper(
                    config=self.config,
                    progress_callback=lambda msg: self.progress.emit(
                        f"TopChladenie: {msg}"
                    ),
                    max_threads=8,
                )
                df = scraper.scrape_products()
                if df is not None and not df.empty:
                    all_scraped_dfs.append(df)
                    self.progress.emit(f"TopChladenie: hotovo ({len(df)} produktov)")

            # 2. Mebella.pl
            if self.options.get("enable_mebella_scraping", False):
                self.progress.emit("Web scraping (Mebella.pl): spúšťam...")
                scraper_mebella = MebellaScraper(
                    progress_callback=lambda msg: self.progress.emit(f"Mebella: {msg}"),
                )
                df_mebella = scraper_mebella.scrape_products()
                if df_mebella is not None and not df_mebella.empty:
                    # Load table_bases.json that is in root directory
                    prices = pd.read_json(
                        Path(__file__).parent.parent.parent / "table_bases_prices.json"
                    )

                    # Update prices
                    # Update prices
                    prices_path = (
                        Path(__file__).parent.parent.parent / "table_bases_prices.json"
                    )

                    # Identify products needing mapping upfront
                    codes_needing_mapping = []
                    for _, row in df_mebella.iterrows():
                        if prices[prices["code"] == row["code"]].empty:
                            codes_needing_mapping.append(row["code"])

                    mapped_count = 0
                    total_to_map = len(codes_needing_mapping)

                    for index, row in df_mebella.iterrows():
                        product_code = row["code"]
                        match = prices[prices["code"] == product_code]

                        if not match.empty:
                            df_mebella.at[index, "price"] = match["price"].values[0]
                        else:
                            # No match found - request user input
                            remaining_count = total_to_map - mapped_count
                            self.progress.emit(
                                f"Cena nenájdená pre: {product_code}, vyžaduje sa vstup (ostáva {remaining_count})..."
                            )
                            # Prepare product data
                            product_data = {
                                "code": product_code,
                                "width": row.get("width"),
                                "depth": row.get("depth"),
                                "height": row.get("height"),
                                "image_url": row.get("image"),
                                "remaining_count": remaining_count,
                            }
                            new_price = self._request_price_mapping(
                                product_data, prices
                            )

                            if new_price:
                                mapped_count += 1
                                # Update DataFrame
                                df_mebella.at[index, "price"] = new_price

                                # Add to prices DataFrame and save to JSON
                                dimension = f"{row.get('width')}x{row.get('depth')}x{row.get('height')}"
                                new_row = pd.DataFrame(
                                    [
                                        {
                                            "code": product_code,
                                            "price": new_price,
                                            "dimension": dimension,
                                        }
                                    ]
                                )
                                prices = pd.concat([prices, new_row], ignore_index=True)

                                try:
                                    prices.to_json(
                                        prices_path, orient="records", indent=4
                                    )
                                    self.progress.emit(
                                        f"Nová cena uložená pre: {product_code}"
                                    )
                                except Exception as e:
                                    self.progress.emit(f"Chyba pri ukladaní ceny: {e}")

                    # Add pairCode for variants (remove last word from code if it is a variant suffix)
                    # Example: "BEA BIG BAR" -> "BEA BIG"
                    # Valid suffixes: BAR, DINING, COFFEE
                    if "code" in df_mebella.columns:

                        def get_pair_code(code):
                            if not code:
                                return ""
                            code_str = str(code).strip()
                            valid_suffixes = ["BAR", "DINING", "COFFEE"]
                            parts = code_str.split()
                            if len(parts) > 1 and parts[-1] in valid_suffixes:
                                return " ".join(parts[:-1])
                            return ""

                        df_mebella["pairCode"] = df_mebella["code"].apply(get_pair_code)

                    all_scraped_dfs.append(df_mebella)
                    self.progress.emit(f"Mebella: hotovo ({len(df_mebella)} produktov)")

            if not all_scraped_dfs:
                self.progress.emit("Web scraping: žiadne dáta nezískané")
                return None

            # Combine results
            final_df = pd.concat(all_scraped_dfs, ignore_index=True)
            self.progress.emit(f"Web scraping: celkom {len(final_df)} produktov")
            return final_df

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
        # Quit the event loop to unblock worker thread
        if self.category_mapping_event_loop:
            self.category_mapping_event_loop.quit()

    def _request_price_mapping(
        self, product_data: Dict, prices_df: pd.DataFrame
    ) -> Optional[str]:
        """
        Request interactive price mapping from GUI.

        Args:
            product_data: Dictionary with product info (code, dimensions)
            prices_df: DataFrame containing existing prices

        Returns:
            New price string or None
        """
        self.price_mapping_result = None

        # Emit signal to GUI
        self.price_mapping_request.emit(product_data, prices_df)

        # Create event loop
        self.price_mapping_event_loop = QEventLoop()
        self.price_mapping_event_loop.exec_()

        return self.price_mapping_result

    def set_price_mapping_result(self, price: str):
        """
        Set the price mapping result from GUI.

        Args:
            price: The selected price
        """
        self.price_mapping_result = price

        if self.price_mapping_event_loop:
            self.price_mapping_event_loop.quit()
