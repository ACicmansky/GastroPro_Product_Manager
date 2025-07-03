"""
Worker class for handling background processing tasks
"""
import pandas as pd
from PyQt5.QtCore import QObject, pyqtSignal

from utils import fetch_xml_feed, parse_xml_feed, merge_dataframes

class Worker(QObject):
    """Worker class for processing data in a background thread"""
    # Signals
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    progress = pyqtSignal(str)
    result = pyqtSignal(object)

    def __init__(self, filtered_df, selected_categories, config, preserve_seo=False):
        super().__init__()
        self.filtered_df = filtered_df  # Already filtered data from the UI
        self.selected_categories = selected_categories
        self.config = config
        self.preserve_seo = preserve_seo

    def run(self):
        try:
            # Using already filtered data from the output table model
            self.progress.emit("Spracovanie filtrovaných dát...")
            
            if self.filtered_df.empty:
                self.error.emit(("Prázdny výsledok", "Žiadne produkty nespĺňajú vybrané kritériá."))
                self.finished.emit()
                return

            # Process XML feeds
            feed_count = len(self.config['xml_feeds'])
            self.progress.emit(f"Načítavanie {feed_count} XML feedov...")
            
            feed_dataframes = []
            for feed_name, feed_info in self.config['xml_feeds'].items():
                self.progress.emit(f"Načítavanie: {feed_name}")
                try:
                    root = fetch_xml_feed(feed_info['url'])
                    if root is None:
                        self.progress.emit(f"Feed {feed_name} nedostupný, pokračujem ďalej...")
                        continue
                    
                    self.progress.emit(f"Parsovanie: {feed_name}")
                    df = parse_xml_feed(root, feed_info['root_element'], feed_info['mapping'], feed_name)
                    
                    if df is not None and not df.empty:
                        feed_dataframes.append(df)
                        self.progress.emit(f"Feed {feed_name} spracovaný: {len(df)} produktov")
                    else:
                        self.progress.emit(f"Feed {feed_name} neobsahuje žiadne dáta")
                        
                except Exception as e:
                    self.error.emit(("Chyba pri spracovaní feedu", f"Chyba pri spracovaní feedu {feed_name}: {e}"))

            self.progress.emit("Spájanie dát...")
            final_df = merge_dataframes(self.filtered_df, feed_dataframes, self.config['final_csv_columns'])
            self.progress.emit(f"Výsledný počet produktov: {len(final_df)}")
            self.result.emit(final_df)
        except Exception as e:
            self.error.emit(("Chyba generovania", f"Pri generovaní došlo k chybe:\n{e}"))
        finally:
            self.finished.emit()
