"""
Main Window for new 138-column format GUI.
Simplified interface focused on XML feed processing and AI enhancement.
"""

import sys
import pandas as pd
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QDesktopWidget,
    QProgressBar,
    QCheckBox,
    QGroupBox,
    QLabel,
    QTextEdit,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QListView,
)
from PyQt5.QtCore import Qt, QThread, QStandardPaths

from .worker_new_format import WorkerNewFormat
from .widgets import CategoryMappingDialog, PriceMappingDialog
from ..utils.config_loader import load_config
from ..utils.category_mapper import get_category_suggestions
from src.loaders.data_loader_factory import DataLoaderFactory
from src.filters.category_filter import CategoryFilter


class MainWindowNewFormat(QMainWindow):
    """Main window for new 138-column format processing."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GASTROPRO Product Manager - New Format")
        self.setGeometry(100, 100, 700, 600)
        self.main_data_file = None
        self.config = load_config()
        self.last_statistics = None
        self.result_df = None
        self.category_filter = CategoryFilter()
        self.all_categories = []
        self.main_data_df = None

        if not self.config:
            QMessageBox.critical(
                self,
                "Chyba konfigurácie",
                "Nepodarilo sa načítať konfiguračný súbor. Aplikácia sa ukončí.",
            )
            sys.exit(1)

        self.init_ui()
        self.center_window()
        self.load_stylesheet()

    def load_stylesheet(self):
        """Load stylesheet if available."""
        try:
            with open("styles/main.qss", "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass  # Use default styling

    def center_window(self):
        """Center window on screen."""
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def init_ui(self):
        """Initialize UI components."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Title
        title = QLabel(
            "<h2>GASTROPRO Product Manager</h2><p>Nový 138-stĺpcový formát</p>"
        )
        title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title)

        # Main data section
        self._create_main_data_section()

        # Category filter section (hidden by default)
        self._create_category_filter_section()

        # XML feeds section
        self._create_xml_feeds_section()

        # Processing options
        self._create_processing_options()

        # Progress bar
        self._create_progress_bar()

        # Process button
        self._create_process_button()

        # Statistics display
        self._create_statistics_display()

    def _create_main_data_section(self):
        """Create main data file selection section."""
        group = QGroupBox("Hlavné dáta (voliteľné)")
        layout = QVBoxLayout(group)

        self.main_data_label = QLabel("Žiadny súbor nie je načítaný")
        self.main_data_label.setStyleSheet("color: gray;")

        button_layout = QHBoxLayout()
        self.select_main_button = QPushButton("Vybrať XLSX súbor")
        self.select_main_button.clicked.connect(self.select_main_data_file)
        self.clear_main_button = QPushButton("Vymazať")
        self.clear_main_button.clicked.connect(self.clear_main_data)
        self.clear_main_button.setEnabled(False)

        button_layout.addWidget(self.select_main_button)
        button_layout.addWidget(self.clear_main_button)
        button_layout.addStretch()

        layout.addWidget(self.main_data_label)
        layout.addLayout(button_layout)

        self.layout.addWidget(group)

    def _create_category_filter_section(self):
        """Create category filtering section."""
        self.category_filter_group = QGroupBox("Filter kategórií")
        layout = QVBoxLayout(self.category_filter_group)

        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Hľadať:")
        self.category_search = QLineEdit()
        self.category_search.setPlaceholderText(
            "Zadajte text pre filtrovanie kategórií..."
        )
        self.category_search.textChanged.connect(self._filter_category_list)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.category_search)
        layout.addLayout(search_layout)

        # Toggle button
        toggle_layout = QHBoxLayout()
        self.toggle_categories_button = QPushButton("Prepnúť filtrované")
        self.toggle_categories_button.clicked.connect(self._toggle_filtered_categories)
        self.select_all_button = QPushButton("Vybrať všetky")
        self.select_all_button.clicked.connect(self._select_all_categories)
        self.deselect_all_button = QPushButton("Zrušiť výber")
        self.deselect_all_button.clicked.connect(self._deselect_all_categories)
        toggle_layout.addWidget(self.toggle_categories_button)
        toggle_layout.addWidget(self.select_all_button)
        toggle_layout.addWidget(self.deselect_all_button)
        layout.addLayout(toggle_layout)

        # Category list with checkboxes
        self.category_list = QListWidget()
        self.category_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.category_list.setResizeMode(QListView.Adjust)
        layout.addWidget(self.category_list)

        # Info label
        self.category_info_label = QLabel("")
        self.category_info_label.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addWidget(self.category_info_label)

        self.layout.addWidget(self.category_filter_group)

        # Hide by default (show when main data loaded)
        self.category_filter_group.setVisible(False)

    def _create_xml_feeds_section(self):
        """Create XML feeds selection section."""
        group = QGroupBox("XML Feedy")
        layout = QVBoxLayout(group)

        self.gastromarket_checkbox = QCheckBox("Načítať z GastroMarket XML")
        self.forgastro_checkbox = QCheckBox("Načítať z ForGastro XML")

        self.gastromarket_checkbox.setChecked(False)
        self.forgastro_checkbox.setChecked(False)

        layout.addWidget(self.gastromarket_checkbox)
        layout.addWidget(self.forgastro_checkbox)

        info_label = QLabel(
            "<small><i>XML feedy sa automaticky stiahnu a spracujú. "
            "URL adresy sú nakonfigurované v config.json.</i></small>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.layout.addWidget(group)

    def _create_processing_options(self):
        """Create processing options section."""
        group = QGroupBox("Možnosti spracovania")
        layout = QVBoxLayout(group)

        self.ai_enhancement_checkbox = QCheckBox("Použiť AI vylepšenie")
        self.ai_enhancement_checkbox.setChecked(True)

        self.web_scraping_checkbox = QCheckBox("Web scraping (TopChladenie.sk)")
        self.web_scraping_checkbox.setChecked(False)

        self.mebella_scraping_checkbox = QCheckBox("Web scraping (Mebella.pl)")
        self.mebella_scraping_checkbox.setChecked(False)

        self.update_categories_checkbox = QCheckBox("Aktualizovať kategórie z feedov")
        self.update_categories_checkbox.setChecked(False)
        self.update_categories_checkbox.setToolTip(
            "Ak je zaškrtnuté, kategórie produktov budú prepísané hodnotami z XML feedov/scrapingu."
        )

        layout.addWidget(self.ai_enhancement_checkbox)
        layout.addWidget(self.web_scraping_checkbox)
        layout.addWidget(self.mebella_scraping_checkbox)
        layout.addWidget(self.update_categories_checkbox)

        self.layout.addWidget(group)

    def _create_progress_bar(self):
        """Create progress bar."""
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("%p% - %v")
        self.layout.addWidget(self.progress_bar)
        self.progress_bar.setVisible(False)

    def _create_process_button(self):
        """Create process button."""
        self.process_button = QPushButton("Spracovať a Exportovať")
        self.process_button.setMinimumHeight(50)
        self.process_button.clicked.connect(self.process_and_export)
        self.layout.addWidget(self.process_button)

    def _create_statistics_display(self):
        """Create statistics display area."""
        group = QGroupBox("Štatistiky")
        layout = QVBoxLayout(group)

        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        self.stats_display.setMaximumHeight(150)
        self.stats_display.setPlainText("Štatistiky sa zobrazia po spracovaní...")

        layout.addWidget(self.stats_display)

        self.layout.addWidget(group)
        group.setVisible(False)
        self.stats_group = group

    def select_main_data_file(self):
        """Select main data file (XLSX or CSV)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Vyberte hlavný dátový súbor",
            QStandardPaths.writableLocation(QStandardPaths.DownloadLocation),
            "Data files (*.xlsx);;XLSX files (*.xlsx)",
        )

        if file_path:
            self.load_main_data_file(file_path)

    def load_main_data_file(self, file_path: str):
        """
        Load main data file.

        Args:
            file_path: Path to data file
        """
        try:
            # Load using factory
            df = DataLoaderFactory.load(file_path)

            if df is None or df.empty:
                QMessageBox.warning(self, "Prázdny súbor", "Vybraný súbor je prázdny.")
                return

            self.main_data_file = file_path
            self.main_data_df = df
            filename = Path(file_path).name
            self.main_data_label.setText(
                f"<b>{filename}</b><br>"
                f"<small>{len(df)} produktov, {len(df.columns)} stĺpcov</small>"
            )
            self.main_data_label.setStyleSheet("color: green;")
            self.clear_main_button.setEnabled(True)

            # Extract and display categories
            self._extract_and_display_categories(df)

        except Exception as e:
            QMessageBox.critical(
                self, "Chyba načítania", f"Nepodarilo sa načítať súbor.\nChyba: {e}"
            )

    def clear_main_data(self):
        """Clear main data file selection."""
        self.main_data_file = None
        self.main_data_df = None
        self.main_data_label.setText("Žiadny súbor nie je načítaný")
        self.main_data_label.setStyleSheet("color: gray;")
        self.clear_main_button.setEnabled(False)

        # Hide category filter section
        self.category_filter_group.setVisible(False)
        self.all_categories = []
        self.category_list.clear()

    def process_and_export(self):
        """Process data and export results."""
        # Validate: at least one data source must be selected
        if (
            self.main_data_file is None
            and not self.gastromarket_checkbox.isChecked()
            and not self.forgastro_checkbox.isChecked()
            and not self.web_scraping_checkbox.isChecked()
            and not self.mebella_scraping_checkbox.isChecked()
        ):
            QMessageBox.warning(
                self,
                "Chýbajúce dáta",
                "Vyberte aspoň jeden zdroj dát na spracovanie (XML feed alebo web scraping).",
            )
            return

        # Prepare options
        options = {
            "enable_gastromarket": self.gastromarket_checkbox.isChecked(),
            "enable_forgastro": self.forgastro_checkbox.isChecked(),
            "enable_web_scraping": self.web_scraping_checkbox.isChecked(),
            "enable_mebella_scraping": self.mebella_scraping_checkbox.isChecked(),
            "enable_ai_enhancement": self.ai_enhancement_checkbox.isChecked(),
            "update_categories_from_feeds": self.update_categories_checkbox.isChecked(),
            "main_data_file": self.main_data_file,
            "selected_categories": (
                self.get_selected_categories() if self.main_data_file else None
            ),
        }

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.process_button.setEnabled(False)
        self.stats_group.setVisible(False)

        # Create worker thread
        self.thread = QThread()
        self.worker = WorkerNewFormat(self.config, options)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.result.connect(self.handle_result)
        self.worker.statistics.connect(self.handle_statistics)
        self.worker.category_mapping_request.connect(
            self.handle_category_mapping_request
        )
        self.worker.price_mapping_request.connect(self.handle_price_mapping_request)
        self.worker.error.connect(self.show_error_message)
        self.worker.progress.connect(self.update_progress)

        # Cleanup
        self.thread.finished.connect(lambda: self.process_button.setEnabled(True))
        self.thread.finished.connect(lambda: self.progress_bar.setVisible(False))

        # Start processing
        self.thread.start()

    def update_progress(self, message: str):
        """Update progress bar with message."""
        self.progress_bar.setFormat(message)

    def handle_statistics(self, stats: dict):
        """Handle statistics from worker."""
        self.last_statistics = stats

        # Display statistics
        stats_text = []
        stats_text.append("=== ŠTATISTIKY SPRACOVANIA ===\n")
        stats_text.append(f"Celkový počet produktov: {stats.get('total_products', 0)}")

        # Show detailed merge statistics if available
        if "total_created" in stats or "total_updated" in stats:
            stats_text.append(f"\n--- Zmeny produktov ---")
            stats_text.append(f"Vytvorených: {stats.get('total_created', 0)}")
            stats_text.append(f"Aktualizovaných: {stats.get('total_updated', 0)}")
            stats_text.append(f"Zachovaných: {stats.get('total_kept', 0)}")
            stats_text.append(f"Odstránených: {stats.get('removed', 0)}")

            # Show breakdown by source
            if "created" in stats and stats["created"]:
                stats_text.append(f"\n--- Vytvorené podľa zdroja ---")
                for source, count in stats["created"].items():
                    if count > 0:
                        stats_text.append(f"  {source}: {count}")

            if "updated" in stats and stats["updated"]:
                stats_text.append(f"\n--- Aktualizované podľa zdroja ---")
                for source, count in stats["updated"].items():
                    if count > 0:
                        stats_text.append(f"  {source}: {count}")

        stats_text.append(f"\n--- Ostatné ---")
        stats_text.append(f"Spracovaných feedov: {stats.get('feeds_processed', 0)}")
        stats_text.append(
            f"Kategórií transformovaných: {stats.get('categories_mapped', 0)}"
        )

        if stats.get("filtered_categories"):
            stats_text.append(
                f"Filtrovaných kategórií: {stats.get('filtered_categories', 0)}"
            )

        if "ai_processed" in stats:
            stats_text.append(f"\n--- AI vylepšenie ---")
            stats_text.append(f"Novo spracovaných: {stats.get('ai_processed', 0)}")
            stats_text.append(f"Celkom spracovaných: {stats.get('ai_total', 0)}")

        self.stats_display.setPlainText("\n".join(stats_text))
        self.stats_group.setVisible(True)

    def handle_result(self, result_df: pd.DataFrame):
        """Handle result DataFrame from worker."""
        self.result_df = result_df
        self.save_output_file()

    def save_output_file(self):
        """Save output file."""
        if self.result_df is None:
            return

        # Ask for save location
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Uložiť výsledný súbor",
            QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
            + "/GastroPro_Export.xlsx",
            "XLSX files (*.xlsx);;CSV files (*.csv)",
        )

        if save_path:
            try:
                # Save using factory
                DataLoaderFactory.save(self.result_df, save_path)

                # Show success message
                stats = self.last_statistics or {}
                message = (
                    f"<b>Dáta boli úspešne exportované!</b><br><br>"
                    f"<b>Súbor:</b> {save_path}<br>"
                    f"<b>Produktov:</b> {len(self.result_df)}<br>"
                    f"<b>Stĺpcov:</b> {len(self.result_df.columns)}<br><br>"
                    f"<b>Formát:</b> Nový 138-stĺpcový formát<br>"
                    f"<b>Typ súboru:</b> {'XLSX' if save_path.endswith('.xlsx') else 'CSV'}"
                )

                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setText(message)
                msg_box.setWindowTitle("Export úspešný")
                msg_box.setTextFormat(Qt.RichText)
                msg_box.exec_()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Chyba pri ukladaní",
                    f"Nepodarilo sa uložiť súbor.\nChyba: {e}",
                )

    def _extract_and_display_categories(self, df: pd.DataFrame):
        """Extract categories from DataFrame and display in list."""
        # Extract categories
        self.all_categories = self.category_filter.extract_categories(df)

        if not self.all_categories:
            # No categories found
            self.category_filter_group.setVisible(False)
            return

        # Populate category list
        self._populate_category_list(self.all_categories)

        # Show category filter section
        self.category_filter_group.setVisible(True)

        # Update info label
        self._update_category_info()

    def _populate_category_list(self, categories: list):
        """Populate category list with checkboxes."""
        self.category_list.clear()

        for category in categories:
            item = QListWidgetItem(category)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)  # Check all by default
            self.category_list.addItem(item)

    def _filter_category_list(self):
        """Filter category list based on search text."""
        search_text = self.category_search.text()

        if not search_text:
            # Show all categories
            filtered_categories = self.all_categories
        else:
            # Filter categories
            filtered_categories = self.category_filter.search_categories(
                self.all_categories, search_text
            )

        # Repopulate list with filtered categories
        self._populate_category_list(filtered_categories)

        # Update info
        self._update_category_info()

    def _toggle_filtered_categories(self):
        """Toggle check state of all visible categories."""
        # Check if any visible items are checked
        any_checked = False
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                any_checked = True
                break

        # Toggle: if any checked, uncheck all; otherwise check all
        new_state = Qt.Unchecked if any_checked else Qt.Checked

        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setCheckState(new_state)

        self._update_category_info()

    def _select_all_categories(self):
        """Select all visible categories."""
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setCheckState(Qt.Checked)

        self._update_category_info()

    def _deselect_all_categories(self):
        """Deselect all visible categories."""
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setCheckState(Qt.Unchecked)

        self._update_category_info()

    def _update_category_info(self):
        """Update category info label."""
        selected_count = self._get_selected_categories_count()
        total_count = len(self.all_categories)
        visible_count = self.category_list.count()

        if visible_count < total_count:
            self.category_info_label.setText(
                f"Zobrazené: {visible_count} z {total_count} kategórií | "
                f"Vybrané: {selected_count}"
            )
        else:
            self.category_info_label.setText(
                f"Celkom: {total_count} kategórií | Vybrané: {selected_count}"
            )

    def _get_selected_categories_count(self) -> int:
        """Get count of selected categories."""
        count = 0
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                count += 1
        return count

    def get_selected_categories(self) -> list:
        """Get list of selected category names."""
        selected = []
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

    def handle_category_mapping_request(self, original_category, product_name):
        """
        Handle interactive category mapping request from worker thread.

        Args:
            original_category: The unmapped category
            product_name: Product name for context
        """
        # Collect existing categories for suggestions
        existing_categories = set()

        # 1. Get categories from worker's category manager
        if (
            hasattr(self, "worker")
            and hasattr(self.worker, "pipeline")
            and hasattr(self.worker.pipeline, "category_mapper")
            and hasattr(self.worker.pipeline.category_mapper, "category_manager")
        ):
            category_manager = self.worker.pipeline.category_mapper.category_manager
            unique_cats = category_manager.get_unique_categories()
            existing_categories.update(unique_cats)

        # 2. Get categories from loaded main data (filter out already-formatted ones)
        if (
            self.main_data_df is not None
            and "defaultCategory" in self.main_data_df.columns
        ):
            main_categories = self.main_data_df["defaultCategory"].dropna().unique()
            # Only add categories WITHOUT the prefix (raw categories for mapping)
            # Categories with prefix are already in final format and shouldn't be used as suggestions
            for cat in main_categories:
                if not str(cat).startswith("Tovary a kategórie >"):
                    existing_categories.add(cat)

        # 3. Get categories from all_categories list (filter out already-formatted ones)
        if self.all_categories:
            for cat in self.all_categories:
                if not str(cat).startswith("Tovary a kategórie >"):
                    existing_categories.add(cat)

        # Get suggestions using similarity matching
        suggestions = []
        if existing_categories:
            suggestions = get_category_suggestions(
                original_category, list(existing_categories), top_n=5
            )

        # Show dialog with suggestions
        dialog = CategoryMappingDialog(
            original_category, suggestions, product_name, self
        )
        if dialog.exec_():
            new_category = dialog.get_new_category()

            # Update progress bar with mapping info
            if new_category and new_category != original_category:
                self.progress_bar.setFormat(
                    f"Mapovanie kategórie: {original_category[:40]}... -> {new_category[:40]}..."
                )

            # Send result back to worker
            self.worker.set_category_mapping_result(new_category)
        else:
            # User cancelled - return original category
            self.worker.set_category_mapping_result(original_category)

    def show_error_message(self, error_info):
        """Show error message."""
        title, message = error_info
        QMessageBox.critical(self, title, message)

    def handle_price_mapping_request(self, product_data, prices_df):
        """
        Handle interactive price mapping request.

        Args:
            product_data: Dictionary with product info
            prices_df: DataFrame with prices
        """
        dialog = PriceMappingDialog(product_data, prices_df, self)
        if dialog.exec_():
            price = dialog.get_selected_price()
            self.worker.set_price_mapping_result(price)
        else:
            self.worker.set_price_mapping_result(None)

    def _extract_and_display_categories(self, df: pd.DataFrame):
        """Extract categories from DataFrame and display in list."""
        # Extract categories
        self.all_categories = self.category_filter.extract_categories(df)

        if not self.all_categories:
            # No categories found
            self.category_filter_group.setVisible(False)
            return

        # Populate category list
        self._populate_category_list(self.all_categories)

        # Show category filter section
        self.category_filter_group.setVisible(True)

        # Update info label
        self._update_category_info()

    def _populate_category_list(self, categories: list):
        """Populate category list with checkboxes."""
        self.category_list.clear()

        for category in categories:
            item = QListWidgetItem(category)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)  # Check all by default
            self.category_list.addItem(item)

    def _filter_category_list(self):
        """Filter category list based on search text."""
        search_text = self.category_search.text()

        if not search_text:
            # Show all categories
            filtered_categories = self.all_categories
        else:
            # Filter categories
            filtered_categories = self.category_filter.search_categories(
                self.all_categories, search_text
            )

        # Repopulate list with filtered categories
        self._populate_category_list(filtered_categories)

        # Update info
        self._update_category_info()

    def _toggle_filtered_categories(self):
        """Toggle check state of all visible categories."""
        # Check if any visible items are checked
        any_checked = False
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                any_checked = True
                break

        # Toggle: if any checked, uncheck all; otherwise check all
        new_state = Qt.Unchecked if any_checked else Qt.Checked

        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setCheckState(new_state)

        self._update_category_info()

    def _select_all_categories(self):
        """Select all visible categories."""
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setCheckState(Qt.Checked)

        self._update_category_info()

    def _deselect_all_categories(self):
        """Deselect all visible categories."""
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setCheckState(Qt.Unchecked)

        self._update_category_info()

    def _update_category_info(self):
        """Update category info label."""
        selected_count = self._get_selected_categories_count()
        total_count = len(self.all_categories)
        visible_count = self.category_list.count()

        if visible_count < total_count:
            self.category_info_label.setText(
                f"Zobrazené: {visible_count} z {total_count} kategórií | "
                f"Vybrané: {selected_count}"
            )
        else:
            self.category_info_label.setText(
                f"Celkom: {total_count} kategórií | Vybrané: {selected_count}"
            )

    def _get_selected_categories_count(self) -> int:
        """Get count of selected categories."""
        count = 0
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                count += 1
        return count

    def get_selected_categories(self) -> list:
        """Get list of selected category names."""
        selected = []
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

    def handle_category_mapping_request(self, original_category, product_name):
        """
        Handle interactive category mapping request from worker thread.

        Args:
            original_category: The unmapped category
            product_name: Product name for context
        """
        # Collect existing categories for suggestions
        existing_categories = set()

        # 1. Get categories from worker's category manager
        if (
            hasattr(self, "worker")
            and hasattr(self.worker, "pipeline")
            and hasattr(self.worker.pipeline, "category_mapper")
            and hasattr(self.worker.pipeline.category_mapper, "category_manager")
        ):
            category_manager = self.worker.pipeline.category_mapper.category_manager
            unique_cats = category_manager.get_unique_categories()
            existing_categories.update(unique_cats)

        # 2. Get categories from loaded main data (filter out already-formatted ones)
        if (
            self.main_data_df is not None
            and "defaultCategory" in self.main_data_df.columns
        ):
            main_categories = self.main_data_df["defaultCategory"].dropna().unique()
            # Only add categories WITHOUT the prefix (raw categories for mapping)
            # Categories with prefix are already in final format and shouldn't be used as suggestions
            for cat in main_categories:
                if not str(cat).startswith("Tovary a kategórie >"):
                    existing_categories.add(cat)

        # 3. Get categories from all_categories list (filter out already-formatted ones)
        if self.all_categories:
            for cat in self.all_categories:
                if not str(cat).startswith("Tovary a kategórie >"):
                    existing_categories.add(cat)

        # Get suggestions using similarity matching
        suggestions = []
        if existing_categories:
            suggestions = get_category_suggestions(
                original_category, list(existing_categories), top_n=5
            )

        # Show dialog with suggestions
        dialog = CategoryMappingDialog(
            original_category, suggestions, product_name, self
        )
        if dialog.exec_():
            new_category = dialog.get_new_category()

            # Update progress bar with mapping info
            if new_category and new_category != original_category:
                self.progress_bar.setFormat(
                    f"Mapovanie kategórie: {original_category[:40]}... -> {new_category[:40]}..."
                )

            # Send result back to worker
            self.worker.set_category_mapping_result(new_category)
        else:
            # User cancelled - return original category
            self.worker.set_category_mapping_result(original_category)

    def show_error_message(self, error_info):
        """Show error message."""
        title, message = error_info
        QMessageBox.critical(self, title, message)

    def handle_price_mapping_request(self, product_data, prices_df):
        """
        Handle interactive price mapping request.

        Args:
            product_data: Dictionary with product info
            prices_df: DataFrame with prices
        """
        dialog = PriceMappingDialog(product_data, prices_df, self)
        if dialog.exec_():
            price = dialog.get_selected_price()
            self.worker.set_price_mapping_result(price)
        else:
            self.worker.set_price_mapping_result(None)
