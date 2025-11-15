"""
Main Window for new 147-column format GUI.
Simplified interface focused on XML feed processing and AI enhancement.
"""

import sys
import pandas as pd
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QFileDialog, QMessageBox, QDesktopWidget, QProgressBar, 
    QCheckBox, QGroupBox, QLabel, QTextEdit
)
from PyQt5.QtCore import Qt, QThread, QStandardPaths

from .worker_new_format import WorkerNewFormat
from ..utils.config_loader import load_config
from src.loaders.data_loader_factory import DataLoaderFactory


class MainWindowNewFormat(QMainWindow):
    """Main window for new 147-column format processing."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GASTROPRO Product Manager - New Format")
        self.setGeometry(100, 100, 700, 600)
        self.main_data_file = None
        self.config = load_config()
        self.last_statistics = None
        self.result_df = None

        if not self.config:
            QMessageBox.critical(
                self, 
                "Chyba konfigurácie", 
                "Nepodarilo sa načítať konfiguračný súbor. Aplikácia sa ukončí."
            )
            sys.exit(1)
        
        self.init_ui()
        self.center_window()
        self.load_stylesheet()

    def load_stylesheet(self):
        """Load stylesheet if available."""
        try:
            with open('styles/main.qss', 'r') as f:
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
        title = QLabel("<h2>GASTROPRO Product Manager</h2><p>Nový 147-stĺpcový formát</p>")
        title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title)

        # Main data section
        self._create_main_data_section()
        
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
        self.select_main_button = QPushButton("Vybrať XLSX/CSV súbor")
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

    def _create_xml_feeds_section(self):
        """Create XML feeds selection section."""
        group = QGroupBox("XML Feedy")
        layout = QVBoxLayout(group)
        
        self.gastromarket_checkbox = QCheckBox("Načítať z GastroMarket XML")
        self.forgastro_checkbox = QCheckBox("Načítať z ForGastro XML")
        
        # Check by default
        self.gastromarket_checkbox.setChecked(True)
        self.forgastro_checkbox.setChecked(True)
        
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
        self.ai_enhancement_checkbox.setChecked(False)
        
        layout.addWidget(self.ai_enhancement_checkbox)
        
        info_label = QLabel(
            "<small><i>Poznámka: Kategórie sa automaticky transformujú do nového formátu. "
            "Kódy produktov sa automaticky prevedú na veľké písmená.</i></small>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
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
            "Data files (*.xlsx *.csv);;XLSX files (*.xlsx);;CSV files (*.csv)"
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
                QMessageBox.warning(
                    self, 
                    "Prázdny súbor", 
                    "Vybraný súbor je prázdny."
                )
                return
            
            self.main_data_file = file_path
            filename = Path(file_path).name
            self.main_data_label.setText(
                f"<b>{filename}</b><br>"
                f"<small>{len(df)} produktov, {len(df.columns)} stĺpcov</small>"
            )
            self.main_data_label.setStyleSheet("color: green;")
            self.clear_main_button.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Chyba načítania", 
                f"Nepodarilo sa načítať súbor.\nChyba: {e}"
            )

    def clear_main_data(self):
        """Clear main data file selection."""
        self.main_data_file = None
        self.main_data_label.setText("Žiadny súbor nie je načítaný")
        self.main_data_label.setStyleSheet("color: gray;")
        self.clear_main_button.setEnabled(False)

    def process_and_export(self):
        """Process data and export results."""
        # Validate: at least one XML feed must be selected
        if not self.gastromarket_checkbox.isChecked() and not self.forgastro_checkbox.isChecked():
            QMessageBox.warning(
                self,
                "Chýbajúce dáta",
                "Vyberte aspoň jeden XML feed na spracovanie."
            )
            return
        
        # Prepare options
        options = {
            'enable_gastromarket': self.gastromarket_checkbox.isChecked(),
            'enable_forgastro': self.forgastro_checkbox.isChecked(),
            'enable_ai_enhancement': self.ai_enhancement_checkbox.isChecked(),
            'main_data_file': self.main_data_file
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
        stats_text.append(f"Spracovaných feedov: {stats.get('feeds_processed', 0)}")
        stats_text.append(f"Kategórií transformovaných: {stats.get('categories_mapped', 0)}")
        
        if 'ai_processed' in stats:
            stats_text.append(f"\nAI vylepšenie:")
            stats_text.append(f"  - Novo spracovaných: {stats.get('ai_processed', 0)}")
            stats_text.append(f"  - Celkom spracovaných: {stats.get('ai_total', 0)}")
        
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
            QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) + "/GastroPro_Export.xlsx", 
            "XLSX files (*.xlsx);;CSV files (*.csv)"
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
                    f"<b>Formát:</b> Nový 147-stĺpcový formát<br>"
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
                    f"Nepodarilo sa uložiť súbor.\nChyba: {e}"
                )

    def show_error_message(self, error_info):
        """Show error message."""
        title, message = error_info
        QMessageBox.critical(self, title, message)
