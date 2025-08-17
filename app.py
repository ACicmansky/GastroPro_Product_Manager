# app.py
import sys
import logging
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QListWidget,
    QListWidgetItem, QDesktopWidget, QFrame, QLineEdit, QProgressBar,
    QCheckBox, QGroupBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QStandardPaths

from scraping import get_scraped_products
from utils import load_config, fetch_xml_feed, parse_xml_feed, merge_dataframes, load_csv_data, load_category_mappings, map_dataframe_categories, clean_html_text
from product_variant_matcher import ProductVariantMatcher

logger = logging.getLogger(__name__)

class DropArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.label = QLabel("Presuňte CSV súbor sem alebo kliknite sem pre výber súboru")
        self.label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)  # Change cursor to indicate clickable area

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith('.csv'):
                self.parent().load_csv_file(file_path)
    
    def mousePressEvent(self, event):
        # Handle mouse click event
        if event.button() == Qt.LeftButton:
            self.parent().parent().select_csv_file()
        super().mousePressEvent(event)

class TopchladenieCsvDropArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.label = QLabel("Presuňte Topchladenie.sk CSV súbor sem alebo kliknite sem pre výber súboru")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("QLabel { color: #666; font-size: 12px; }")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMaximumHeight(60)
        self.topchladenie_df = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith('.csv'):
                self.parent().load_topchladenie_csv_file(file_path)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent().parent().parent().select_topchladenie_csv_file()
        super().mousePressEvent(event)
    
    def clear_file(self):
        """Clear the loaded file"""
        self.topchladenie_df = None
        self.label.setText("Presuňte Topchladenie.sk CSV súbor sem alebo kliknite sem pre výber súboru")
        self.label.setStyleSheet("QLabel { color: #666; font-size: 12px; }")

class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    progress = pyqtSignal(str)
    result = pyqtSignal(object, dict)  # Pass dataframe and statistics dictionary

    def __init__(self, main_df, selected_categories, config, map_categories=False, variant_checkbox=False, scrape_topchladenie=False, topchladenie_csv_df=None, enable_gastromarket=True, enable_forgastro=True, ai_enhancement_checkbox=False):
        super().__init__()
        self.main_df = main_df.copy()
        self.selected_categories = selected_categories
        self.config = config
        self.map_categories = map_categories
        self.variant_checkbox = variant_checkbox
        self.scrape_topchladenie = scrape_topchladenie
        self.topchladenie_csv_df = topchladenie_csv_df
        self.enable_gastromarket = enable_gastromarket
        self.enable_forgastro = enable_forgastro
        self.ai_enhancement_checkbox = ai_enhancement_checkbox

    def run(self):
        try:
            # STEP 1: Filter main dataframe by selected categories first (most efficient)
            self.progress.emit("Filtering main CSV by selected categories...")
            filtered_df = self.main_df[self.main_df['Hlavna kategória'].isin(self.selected_categories)].copy()
            self.progress.emit(f"Filtered to {len(filtered_df)} products from selected categories")
            
            # STEP 2: Apply category mapping to filtered products only (more efficient)
            if self.map_categories and 'Hlavna kategória' in filtered_df.columns:
                self.progress.emit("Applying category mappings to filtered CSV...")
                category_mappings = load_category_mappings()
                if category_mappings:
                    filtered_df = map_dataframe_categories(filtered_df, category_mappings)
                    self.progress.emit("Category mapping completed on filtered data")
            
            # STEP 3: Download and parse XML feeds (only enabled ones)
            enabled_feeds = []
            if self.enable_gastromarket and 'gastromarket' in self.config['xml_feeds']:
                enabled_feeds.append('gastromarket')
            if self.enable_forgastro and 'forgastro' in self.config['xml_feeds']:
                enabled_feeds.append('forgastro')
            
            # Track individual feed counts
            feed_dataframes = []
            gastromarket_count = 0
            forgastro_count = 0
            
            if enabled_feeds:
                self.progress.emit(f"Starting to fetch {len(enabled_feeds)} enabled XML feeds...")
                for feed_name in enabled_feeds:
                    feed_info = self.config['xml_feeds'][feed_name]
                    self.progress.emit(f"Fetching feed: {feed_name}")
                    try:
                        root = fetch_xml_feed(feed_info['url'])
                        if root is None:
                            continue
                        
                        self.progress.emit(f"Parsing feed: {feed_name}")
                        df = parse_xml_feed(root, feed_info['root_element'], feed_info['mapping'], feed_name)
                        
                        if df is not None and not df.empty:
                            feed_dataframes.append(df)
                            # Track counts by feed name
                            if feed_name == 'gastromarket':
                                gastromarket_count = len(df)
                            elif feed_name == 'forgastro':
                                forgastro_count = len(df)
                            self.progress.emit(f"Successfully parsed {len(df)} products from {feed_name}")
                    except Exception as e:
                        self.error.emit(("Chyba pri spracovaní feedu", f"Chyba pri spracovaní feedu {feed_name}: {e}"))
            else:
                self.progress.emit("No XML feeds enabled, skipping XML feed processing")
                feed_dataframes = []
            
            # STEP 4: Get Topchladenie.sk data (scraping or loaded CSV)
            scraped_df = None
            topchladenie_count = 0
            if self.scrape_topchladenie:
                self.progress.emit("Sťahovanie najnovších údajov z Topchladenie.sk...")
                scraped_df = get_scraped_products(include_scraping=True)
                
                if scraped_df is not None and not scraped_df.empty:
                    topchladenie_count = len(scraped_df)
                    self.progress.emit(f"Získané údaje o {len(scraped_df)} najnovších produktoch z Topchladenie.sk")
                else:
                    self.progress.emit("Neboli nájdené žiadne údaje z Topchladenie.sk")
                    scraped_df = None
                    
            elif self.topchladenie_csv_df is not None and not self.topchladenie_csv_df.empty:
                self.progress.emit("Používanie načítaných údajov z Topchladenie.sk CSV súboru...")
                scraped_df = self.topchladenie_csv_df.copy()
                topchladenie_count = len(scraped_df)
                self.progress.emit(f"Používané údaje o {len(scraped_df)} produktoch z načítaného CSV súboru")
        
            # STEP 5: Clean and merge all data sources in the correct order
            self.progress.emit("Cleaning and merging all data sources...")
            
            # Clean the main dataframe - filter out rows with empty catalog numbers
            join_column = "Kat. číslo"  # Same as used in merge_dataframes
            if join_column in filtered_df.columns:
                # Count products before filtering
                before_count = len(filtered_df)
                # Remove empty catalog numbers (empty strings, NaN or None)
                filtered_df = filtered_df[filtered_df[join_column].notna() & (filtered_df[join_column].str.strip() != "")]
                removed_count = before_count - len(filtered_df)
                if removed_count > 0:
                    self.progress.emit(f"Removed {removed_count} products with empty catalog numbers from main CSV")

            # Process each DataFrame in the list to check and update 'Kat. číslo rodiča' from 0 to ""
            if 'Kat. číslo rodiča' in filtered_df.columns:
                # Check for both numeric 0 and string "0"
                filtered_df.loc[filtered_df['Kat. číslo rodiča'].isin([0, "0"]), 'Kat. číslo rodiča'] = ""
                self.progress.emit("Replaced '0' values in 'Kat. číslo rodiča' with empty strings")
            
            # Clean feed dataframes
            cleaned_feed_dataframes = []
            for i, feed_df in enumerate(feed_dataframes):
                if join_column in feed_df.columns and not feed_df.empty:
                    before_count = len(feed_df)
                    # Remove empty catalog numbers
                    feed_df = feed_df[feed_df[join_column].notna() & (feed_df[join_column].str.strip() != "")]
                    removed_count = before_count - len(feed_df)
                    if removed_count > 0:
                        feed_name = "GastroMarket" if i == 0 else "ForGastro"
                        self.progress.emit(f"Removed {removed_count} products with empty catalog numbers from {feed_name}")
                cleaned_feed_dataframes.append(feed_df)
            
            # Clean scraped data if available
            if scraped_df is not None and not scraped_df.empty and join_column in scraped_df.columns:
                before_count = len(scraped_df)
                # Remove empty catalog numbers
                scraped_df = scraped_df[scraped_df[join_column].notna() & (scraped_df[join_column].str.strip() != "")]
                removed_count = before_count - len(scraped_df)
                if removed_count > 0:
                    self.progress.emit(f"Removed {removed_count} products with empty catalog numbers from Topchladenie data")
            
            # Start with filtered CSV data
            all_dataframes = [filtered_df]
            
            # Add cleaned XML feed data
            if cleaned_feed_dataframes:
                all_dataframes.extend(cleaned_feed_dataframes)
                self.progress.emit(f"Added {len(cleaned_feed_dataframes)} cleaned XML feed datasets")        
            
            # Add cleaned scraped data last (freshest data has priority)
            if scraped_df is not None and not scraped_df.empty:
                all_dataframes.append(scraped_df)
                self.progress.emit("Added cleaned scraped data as final dataset")
            
            # Merge everything
            final_df = merge_dataframes(filtered_df, cleaned_feed_dataframes + ([scraped_df] if scraped_df is not None and not scraped_df.empty else []), self.config['final_csv_columns'])
            
            # Ensure all values are clean strings and strip whitespace
            # But only for object columns and only at the end of processing
            for col in final_df.columns:
                if final_df[col].dtype == 'object':
                    # Fill NaN values with empty string and convert to string
                    final_df[col] = final_df[col].fillna("")
                    final_df[col] = final_df[col].astype(str)
                    # Handle the special case where pandas converts NaN to the string "nan"
                    final_df[col] = final_df[col].replace("nan", "")
                    # Strip whitespace
                    final_df[col] = final_df[col].str.strip()
            
            # Replace all \n with <br /> in Krátky popis and Dlhý popis and replace " with ''
            # Ensure columns exist before processing
            final_df['Krátky popis'] = final_df['Krátky popis'].apply(clean_html_text)
            final_df['Dlhý popis'] = final_df['Dlhý popis'].apply(clean_html_text)
            final_df['Názov tovaru'] = final_df['Názov tovaru'].apply(clean_html_text)

            # Replace empty 'Názov tovaru' with Kat. číslo
            final_df.loc[final_df['Názov tovaru'].isna() | (final_df['Názov tovaru'] == ""), 'Názov tovaru'] = final_df['Kat. číslo']

            # Find all products with empty 'Hlavna kategória' (NaN or empty string) and set their values
            mask_f841622 = (final_df['Kat. číslo'] == "F841622") & (final_df['Hlavna kategória'].isna() | (final_df['Hlavna kategória'] == ""))
            mask_l131712 = (final_df['Kat. číslo'] == "L131712") & (final_df['Hlavna kategória'].isna() | (final_df['Hlavna kategória'] == ""))
            mask_roc_cl201 = (final_df['Kat. číslo'] == "ROC_CL201") & (final_df['Hlavna kategória'].isna() | (final_df['Hlavna kategória'] == ""))
            
            final_df.loc[mask_f841622, 'Hlavna kategória'] = "Chladenie a mrazenie/Chladiace a mraziace stoly"
            final_df.loc[mask_l131712, 'Hlavna kategória'] = "Stolový inventár/Dochucovacie súpravy a mlynčeky"
            final_df.loc[mask_roc_cl201, 'Hlavna kategória'] = "Príprava surovín/Krájače zeleniny"

            # Identify product variants and assign parent catalog numbers
            if self.variant_checkbox:
                self.progress.emit("Analyzing products for variant detection...")
                variant_matcher = ProductVariantMatcher(progress_callback=self.progress.emit)
                
                # Extract product differences (dimensions, power, volume, etc.)
                self.progress.emit("Extracting product dimensions and differences...")
                final_df, group_data = variant_matcher.identify_variants(final_df, generate_report=True)
                
                variant_matcher.extract_product_differences(final_df, group_data)

            # AI Enhancement for descriptions
            if self.ai_enhancement_checkbox and self.config.get('ai_enhancement', {}).get('enabled', False):
                try:
                    from ai_enhancement import AIEnhancementProcessor
                    self.progress.emit("Enhancing product descriptions with AI...")
                    ai_processor = AIEnhancementProcessor(self.config.get('ai_enhancement', {}))
                    
                    def ai_progress_callback(processed, total):
                        self.progress.emit(f"AI enhancement: {processed}/{total} products processed")
                    
                    final_df, ai_stats = ai_processor.process_dataframe(final_df, progress_callback=ai_progress_callback)
                except ImportError as e:
                    self.progress.emit(f"AI enhancement: Required packages not installed - {e}")
                    logger.error(f"AI enhancement: Required packages not installed - {e}")
                except Exception as e:
                    self.progress.emit(f"AI enhancement: Error - {str(e)}")
                    logger.error(f"AI enhancement: Error - {str(e)}")

            # Prepare statistics
            statistics = {
                'original_csv': len(filtered_df),
                'gastromarket': gastromarket_count,
                'forgastro': forgastro_count,
                'topchladenie': topchladenie_count,
                'total': len(final_df)
            }
            
            # Add AI enhancement statistics if applicable
            if 'ai_stats' in locals():
                statistics.update(ai_stats)
            
            # Update progress message with AI statistics if applicable
            if 'ai_stats' in locals() and ai_stats.get('ai_should_process', 0) > 0:
                self.progress.emit(f"Final dataset ready with {len(final_df)} total products. "
                                 f"AI processed {ai_stats['ai_processed']}/{ai_stats['ai_should_process']} products.")
            else:
                self.progress.emit(f"Final dataset ready with {len(final_df)} total products")
            self.result.emit(final_df, statistics)
        except Exception as e:
            self.error.emit(("Chyba generovania", f"Pri generovaní došlo k chybe:\n{e}"))
        finally:
            self.finished.emit()

class ProductManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GASTROPRO Product Manager")
        self.setGeometry(100, 100, 600, 600)
        self.main_df = None
        self.categories = []
        self.config = load_config()
        self.last_statistics = None  # Store statistics from last processing

        if not self.config:
            QMessageBox.critical(self, "Chyba konfigurácie", "Nepodarilo sa načítať konfiguračný súbor. Aplikácia sa ukončí.")
            sys.exit(1)
        
        self.init_ui()
        self.center_window()
        self.load_stylesheet()

    def load_stylesheet(self):
        try:
            with open('styles/main.qss', 'r') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("Stylesheet not found.")

    def center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def init_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setObjectName("central_widget")
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # --- CSV Upload ---
        self.drop_area = DropArea(self)
        self.layout.addWidget(self.drop_area)

        # --- Category Filter ---
        self.filter_group = QWidget()
        self.filter_group.setObjectName("glass")
        filter_layout = QVBoxLayout(self.filter_group)
        filter_label = QLabel("Vyberte kategórie na export:")
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Hľadať kategórie...")
        self.search_bar.textChanged.connect(self.filter_categories)
        
        # Create horizontal layout for buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setAlignment(Qt.AlignLeft)
        
        # Button for filtered categories
        self.toggle_filtered_button = QPushButton("Prepnúť filtrované")
        self.toggle_filtered_button.clicked.connect(self.toggle_filtered_categories)
        self.toggle_filtered_button.setToolTip("Označiť/odznačiť všetky filtrované kategórie")
        self.toggle_filtered_button.setMaximumWidth(140)
        
        # Add button to horizontal layout
        buttons_layout.addWidget(self.toggle_filtered_button)
        buttons_layout.addStretch(1)
        
        self.category_list = QListWidget()
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.search_bar)
        filter_layout.addLayout(buttons_layout)
        filter_layout.addWidget(self.category_list)
        self.layout.addWidget(self.filter_group)
        self.filter_group.setVisible(False)

        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.layout.addWidget(self.progress_bar)
        self.progress_bar.setVisible(False)

        # --- Data Sources Options (above export button) ---
        self.options_group = QGroupBox("Možnosti exportu")
        self.options_group.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; padding-top: 10px; }")
        options_layout = QVBoxLayout()
        self.options_group.setLayout(options_layout)
        self.options_group.setVisible(False)
        
        # Row 1: CSV and Category options
        row1_layout = QHBoxLayout()
        self.map_categories_checkbox = QCheckBox("Migrovať pôvodné CSV kategórie")
        self.map_categories_checkbox.setChecked(False)
        self.map_categories_checkbox.setToolTip("Použiť mapovanie kategórií na vstupný CSV súbor")

        self.variant_checkbox = QCheckBox("Analyzovať produkty na varianty")
        self.variant_checkbox.setChecked(False)
        self.variant_checkbox.setToolTip("Analyzovať produkty na varianty")

        self.ai_enhancement_checkbox = QCheckBox("Použiť AI vylepšenie")
        self.ai_enhancement_checkbox.setChecked(True)
        self.ai_enhancement_checkbox.setToolTip("Použiť AI vylepšenie")

        row1_layout.addWidget(self.map_categories_checkbox)
        row1_layout.addWidget(self.variant_checkbox)
        row1_layout.addWidget(self.ai_enhancement_checkbox)
        row1_layout.addStretch(1)
        options_layout.addLayout(row1_layout)
        
        # Row 2: XML Feeds options
        row2_layout = QHBoxLayout()
        self.gastromarket_checkbox = QCheckBox("Načítať z GastroMarket XML")
        self.gastromarket_checkbox.setChecked(False)
        self.gastromarket_checkbox.setToolTip("Načítať produkty z GastroMarket XML feedu")
        
        self.forgastro_checkbox = QCheckBox("Načítať z ForGastro XML")
        self.forgastro_checkbox.setChecked(False)
        self.forgastro_checkbox.setToolTip("Načítať produkty z ForGastro XML feedu")
        
        row2_layout.addWidget(self.gastromarket_checkbox)
        row2_layout.addWidget(self.forgastro_checkbox)
        row2_layout.addStretch(1)
        options_layout.addLayout(row2_layout)
        
        # Row 3: Topchladenie.sk options
        row3_layout = QVBoxLayout()
        
        # Scraping checkbox
        scrape_layout = QHBoxLayout()
        self.scrape_topchladenie_checkbox = QCheckBox("Stiahnuť z Topchladenie.sk")
        self.scrape_topchladenie_checkbox.setChecked(False)
        self.scrape_topchladenie_checkbox.setToolTip("Stiahnuť aktuálne údaje o produktoch z topchladenie.sk")
        self.scrape_topchladenie_checkbox.stateChanged.connect(self.on_scrape_topchladenie_changed)
        
        scrape_layout.addWidget(self.scrape_topchladenie_checkbox)
        scrape_layout.addStretch(1)
        row3_layout.addLayout(scrape_layout)
        
        # CSV drop area
        self.topchladenie_csv_drop_area = TopchladenieCsvDropArea(self)
        row3_layout.addWidget(self.topchladenie_csv_drop_area)
        
        options_layout.addLayout(row3_layout)
        
        self.layout.addWidget(self.options_group)

        # --- Export Button ---
        self.generate_button = QPushButton("Generovať a Exportovať CSV")
        self.generate_button.clicked.connect(self.generate_and_export_csv)
        self.layout.addWidget(self.generate_button)
        self.generate_button.setVisible(False)

    def filter_categories(self, text):
        from rapidfuzz import fuzz
        
        # If search text is empty, show all items
        if not text:
            for i in range(self.category_list.count()):
                item = self.category_list.item(i)
                item.setHidden(False)
            return
            
        # Set the similarity threshold (0-100)
        # Lower values will match more items but with less precision
        threshold = 70
        
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item_text = item.text()
            
            # Calculate similarity scores using different methods
            # 1. Check if search is a substring (original method)
            substring_match = text.lower() in item_text.lower()
            
            # 2. Check for partial ratio (fuzzy substring matching)
            partial_score = fuzz.partial_ratio(text.lower(), item_text.lower())
            
            # 3. Check for token sort ratio (for word order independence)
            token_score = fuzz.token_sort_ratio(text.lower(), item_text.lower())
            
            # Hide item if it doesn't meet any of the match criteria
            item.setHidden(not (substring_match or partial_score >= threshold or token_score >= threshold))

    def reset_ui(self):
        self.categories = []
        self.category_list.clear()
        self.main_df = None
        self.drop_area.label.setText("Presuňte CSV súbor sem alebo kliknite sem pre výber súboru")
        self.topchladenie_csv_drop_area.clear_file()
        self.scrape_topchladenie_checkbox.setChecked(True)
        self.filter_group.setVisible(False)
        self.options_group.setVisible(False)
        self.generate_button.setVisible(False)
        self.progress_bar.setVisible(False)

    def select_csv_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Vyberte CSV súbor", QStandardPaths.writableLocation(QStandardPaths.DownloadLocation), "CSV files (*.csv)")
        if file_path:
            self.load_csv_file(file_path)

    def load_csv_file(self, file_path):
        try:
            # Load the CSV data
            self.main_df = load_csv_data(file_path)
            
            if self.main_df is None or self.main_df.empty:
                self._reset_ui()
                return

            self.drop_area.label.setText(f"Nahraný súbor: {file_path.split('/')[-1]}")
            
            if 'Hlavna kategória' in self.main_df.columns:
                self.categories = sorted(self.main_df['Hlavna kategória'].dropna().unique().tolist())
                self.populate_category_list()
                self.filter_group.setVisible(True)
                self.options_group.setVisible(True)
                self.generate_button.setVisible(True)
            else:
                QMessageBox.warning(self, "Chýbajúci stĺpec", "V CSV súbore nebol nájdený stĺpec 'Hlavna kategória'. Filtrovanie nie je možné.")
                self._reset_ui()

        except Exception as e:
            QMessageBox.critical(self, "Chyba načítania", f"Nepodarilo sa načítať CSV súbor.\nChyba: {e}")
            self._reset_ui()


    def populate_category_list(self):
        self.category_list.clear()
        for category in self.categories:
            item = QListWidgetItem(category)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.category_list.addItem(item)
            
    def on_scrape_topchladenie_changed(self, state):
        """Handle scraping checkbox state change"""
        if state == Qt.Checked:
            # If scraping is enabled, clear any loaded CSV file
            self.topchladenie_csv_drop_area.clear_file()
    
    def select_topchladenie_csv_file(self):
        """Open file dialog to select topchladenie CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Vyberte Topchladenie.sk CSV súbor", "", "CSV Files (*.csv)"
        )
        if file_path:
            self.load_topchladenie_csv_file(file_path)
    
    def load_topchladenie_csv_file(self, file_path):
        """Load topchladenie CSV file and update UI"""
        try:
            # Load CSV with semicolon separator and proper encoding
            df = pd.read_csv(file_path, sep=';', encoding='utf-8', dtype=str, keep_default_na=False)
            if df.empty:
                QMessageBox.warning(self, "Prázdny súbor", "Vybraný CSV súbor je prázdny.")
                return
            
            # Store the dataframe
            self.topchladenie_csv_drop_area.topchladenie_df = df
            
            # Update the drop area label
            filename = file_path.split('/')[-1].split('\\')[-1]
            self.topchladenie_csv_drop_area.label.setText(f"Načítaný súbor: {filename} ({len(df)} produktov)")
            self.topchladenie_csv_drop_area.label.setStyleSheet("QLabel { color: #2E7D32; font-size: 12px; font-weight: bold; }")
            
            # Uncheck scraping checkbox to avoid conflict
            self.scrape_topchladenie_checkbox.setChecked(False)
            
            QMessageBox.information(self, "Úspech", f"Topchladenie.sk CSV súbor bol úspešne načítaný ({len(df)} produktov).")
            
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nepodarilo sa načítať CSV súbor:\n{e}")
            print(f"Debug - CSV loading error: {e}")  # Debug output
            
    def toggle_filtered_categories(self):
        # Determine the state to apply based on the first visible item
        new_state = Qt.Unchecked
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if not item.isHidden():
                # If first visible item is unchecked, we'll check all visible items
                # Otherwise, we'll uncheck all visible items
                if item.checkState() == Qt.Unchecked:
                    new_state = Qt.Checked
                break
                
        # Apply the determined state to all visible items
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if not item.isHidden():
                item.setCheckState(new_state)

    def generate_and_export_csv(self):
        if self.main_df is None:
            QMessageBox.warning(self, "Chýbajúce dáta", "Najprv nahrajte hlavný CSV súbor.")
            return

        selected_categories = []
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_categories.append(item.text())

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Indeterminate progress

        # Get all checkbox states
        map_categories = self.map_categories_checkbox.isChecked()
        variant_checkbox = self.variant_checkbox.isChecked()
        scrape_topchladenie = self.scrape_topchladenie_checkbox.isChecked()
        topchladenie_csv_df = self.topchladenie_csv_drop_area.topchladenie_df
        enable_gastromarket = self.gastromarket_checkbox.isChecked()
        enable_forgastro = self.forgastro_checkbox.isChecked()
        ai_enhancement_checkbox = self.ai_enhancement_checkbox.isChecked()

        self.thread = QThread()
        self.worker = Worker(
            self.main_df, selected_categories, self.config, 
            map_categories=map_categories,
            variant_checkbox=variant_checkbox,
            scrape_topchladenie=scrape_topchladenie,
            topchladenie_csv_df=topchladenie_csv_df,
            enable_gastromarket=enable_gastromarket,
            enable_forgastro=enable_forgastro,
            ai_enhancement_checkbox=ai_enhancement_checkbox
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.result.connect(self.handle_result_with_statistics)
        self.worker.error.connect(self.show_error_message)
        self.worker.progress.connect(self.update_progress)
        
        self.thread.start()
        self.generate_button.setEnabled(False)
        self.thread.finished.connect(lambda: self.generate_button.setEnabled(True))
        self.thread.finished.connect(lambda: self.progress_bar.setVisible(False))


    def update_progress(self, message):
        self.progress_bar.setFormat(message)

    def show_error_message(self, error_info):
        title, message = error_info
        QMessageBox.critical(self, title, message)
    
    def handle_result_with_statistics(self, final_df, statistics):
        """Handle the final result with statistics from Worker"""
        self.last_statistics = statistics
        self.save_final_csv(final_df)

    def save_final_csv(self, final_df):
        save_path, _ = QFileDialog.getSaveFileName(self, "Uložiť výsledný CSV súbor", QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) + "/Merged.csv", "CSV files (*.csv)")
        if save_path:
            try:
                # First try cp1250 with character replacement
                try:
                    # Handle characters that can't be encoded in cp1250
                    # Convert problematic characters first, but preserve data
                    for col in final_df.columns:
                        if final_df[col].dtype == 'object':
                            # Ensure all values are strings and handle encoding issues
                            final_df[col] = final_df[col].astype(str)
                            final_df[col] = final_df[col].apply(
                                lambda x: ''.join(c if c.encode('cp1250', errors='replace') != b'?' else ' ' for c in x)
                            )
                    
                    final_df.to_csv(save_path, index=False, encoding='cp1250', sep=';')
                    
                    # Create detailed statistics message
                    stats_message = self.create_statistics_message(save_path)
                    QMessageBox.information(self, "Great success!", stats_message)
                except UnicodeEncodeError:
                    # Fall back to UTF-8 with BOM for Excel compatibility
                    # Ensure all values are clean strings before saving
                    for col in final_df.columns:
                        if final_df[col].dtype == 'object':
                            final_df[col] = final_df[col].astype(str)
                    final_df.to_csv(save_path, index=False, encoding='utf-8-sig', sep=';')
                    stats_message = self.create_statistics_message(save_path)
                    stats_message += "\n\nPoznámka: Použité kódovanie UTF-8 namiesto cp1250 kvôli nekompatibilným znakom."
                    QMessageBox.information(self, "Great success!", stats_message)
            except Exception as e:
                self.show_error_message(("Chyba pri ukladaní", f"Pri ukladaní súboru došlo k chybe:\n{e}"))
    
    def create_statistics_message(self, save_path):
        """Create detailed statistics message for the save dialog"""
        if not self.last_statistics:
            return f"Súbor bol úspešne uložený do: {save_path}"
        
        stats = self.last_statistics
        message = f"Súbor bol úspešne uložený do: {save_path}\n\n"
        message += "📊 Summár exportovaných produktov:\n"
        message += f"• Originálny CSV: {stats['original_csv']} produktov\n"
        message += f"• GastroMarket XML: {stats['gastromarket']} produktov\n"
        message += f"• ForGastro XML: {stats['forgastro']} produktov\n"
        message += f"• Topchladenie.sk: {stats['topchladenie']} produktov\n"
        
        # Add AI enhancement statistics if applicable
        if 'ai_should_process' in stats and stats['ai_should_process'] > 0:
            message += f"• AI spracované: {stats['ai_processed']}/{stats['ai_should_process']} produktov\n"
        
        message += f"\n🎯 Celkovo exportovaných: {stats['total']} produktov"
        
        return message

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = ProductManager()
    main_win.show()
    sys.exit(app.exec_())