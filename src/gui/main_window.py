# src/gui/main_window.py
import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem, QDesktopWidget, 
    QLineEdit, QProgressBar, QCheckBox, QGroupBox
)
from PyQt5.QtCore import Qt, QThread, QStandardPaths

from .widgets import DropArea, TopchladenieCsvDropArea
from .worker import Worker
from ..utils.config_loader import load_config
from ..utils.data_loader import load_csv_data
from ..core.models import PipelineResult

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GASTROPRO Product Manager")
        self.setGeometry(100, 100, 600, 600)
        self.main_df = None
        self.categories = []
        self.config = load_config()
        self.last_statistics = None

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
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # --- UI Components ---
        self._create_upload_area()
        self._create_category_filter()
        self._create_progress_bar()
        self._create_options_group()
        self._create_export_button()

    def _create_upload_area(self):
        self.drop_area = DropArea(self.central_widget)
        self.layout.addWidget(self.drop_area)

    def _create_category_filter(self):
        self.filter_group = QGroupBox("Vyberte kategórie na export:")
        filter_layout = QVBoxLayout(self.filter_group)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Hľadať kategórie...")
        self.search_bar.textChanged.connect(self.filter_categories)
        
        buttons_layout = QHBoxLayout()
        self.toggle_filtered_button = QPushButton("Prepnúť filtrované")
        self.toggle_filtered_button.clicked.connect(self.toggle_filtered_categories)
        buttons_layout.addWidget(self.toggle_filtered_button)
        buttons_layout.addStretch(1)
        
        self.category_list = QListWidget()
        filter_layout.addWidget(self.search_bar)
        filter_layout.addLayout(buttons_layout)
        filter_layout.addWidget(self.category_list)
        self.layout.addWidget(self.filter_group)
        self.filter_group.setVisible(False)

    def _create_progress_bar(self):
        self.progress_bar = QProgressBar()
        self.layout.addWidget(self.progress_bar)
        self.progress_bar.setVisible(False)

    def _create_options_group(self):
        self.options_group = QGroupBox("Možnosti exportu")
        options_layout = QVBoxLayout(self.options_group)
        
        self.map_categories_checkbox = QCheckBox("Migrovať pôvodné CSV kategórie")
        self.variant_checkbox = QCheckBox("Analyzovať produkty na varianty")
        self.ai_enhancement_checkbox = QCheckBox("Použiť AI vylepšenie")
        self.gastromarket_checkbox = QCheckBox("Načítať z GastroMarket XML")
        self.forgastro_checkbox = QCheckBox("Načítať z ForGastro XML")
        self.scrape_topchladenie_checkbox = QCheckBox("Stiahnuť z Topchladenie.sk")
        self.topchladenie_csv_drop_area = TopchladenieCsvDropArea(self.central_widget)

        self.ai_enhancement_checkbox.setChecked(True)
        self.scrape_topchladenie_checkbox.stateChanged.connect(self.on_scrape_topchladenie_changed)

        row1 = QHBoxLayout()
        row1.addWidget(self.map_categories_checkbox)
        row1.addWidget(self.variant_checkbox)
        row1.addWidget(self.ai_enhancement_checkbox)
        row1.addStretch(1)

        row2 = QHBoxLayout()
        row2.addWidget(self.gastromarket_checkbox)
        row2.addWidget(self.forgastro_checkbox)
        row2.addStretch(1)

        options_layout.addLayout(row1)
        options_layout.addLayout(row2)
        options_layout.addWidget(self.scrape_topchladenie_checkbox)
        options_layout.addWidget(self.topchladenie_csv_drop_area)

        self.layout.addWidget(self.options_group)
        self.options_group.setVisible(False)

    def _create_export_button(self):
        self.generate_button = QPushButton("Generovať a Exportovať CSV")
        self.generate_button.clicked.connect(self.generate_and_export_csv)
        self.layout.addWidget(self.generate_button)
        self.generate_button.setVisible(False)

    def filter_categories(self, text):
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def toggle_filtered_categories(self):
        new_state = Qt.Unchecked
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if not item.isHidden():
                if item.checkState() == Qt.Unchecked:
                    new_state = Qt.Checked
                break
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if not item.isHidden():
                item.setCheckState(new_state)

    def select_csv_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Vyberte CSV súbor", QStandardPaths.writableLocation(QStandardPaths.DownloadLocation), "CSV files (*.csv)")
        if file_path:
            self.load_csv_file(file_path)

    def load_csv_file(self, file_path):
        try:
            self.main_df = load_csv_data(file_path)
            if self.main_df is None or self.main_df.empty or 'Hlavna kategória' not in self.main_df.columns:
                QMessageBox.warning(self, "Chyba súboru", "CSV súbor je prázdny alebo neobsahuje stĺpec 'Hlavna kategória'.")
                return

            self.drop_area.label.setText(f"Nahraný súbor: {file_path.split('/')[-1]}")
            self.categories = sorted(self.main_df['Hlavna kategória'].dropna().unique().tolist())
            self.populate_category_list()
            self.filter_group.setVisible(True)
            self.options_group.setVisible(True)
            self.generate_button.setVisible(True)
        except Exception as e:
            QMessageBox.critical(self, "Chyba načítania", f"Nepodarilo sa načítať CSV súbor.\nChyba: {e}")

    def populate_category_list(self):
        self.category_list.clear()
        for category in self.categories:
            item = QListWidgetItem(category)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.category_list.addItem(item)

    def on_scrape_topchladenie_changed(self, state):
        if state == Qt.Checked:
            self.topchladenie_csv_drop_area.clear_file()

    def select_topchladenie_csv_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Vyberte Topchladenie.sk CSV súbor", "", "CSV Files (*.csv)")
        if file_path:
            self.load_topchladenie_csv_file(file_path)

    def load_topchladenie_csv_file(self, file_path):
        try:
            df = pd.read_csv(file_path, sep=';', encoding='utf-8', dtype=str, keep_default_na=False)
            if df.empty:
                QMessageBox.warning(self, "Prázdny súbor", "Vybraný CSV súbor je prázdny.")
                return
            self.topchladenie_csv_drop_area.topchladenie_df = df
            filename = file_path.split('/')[-1]
            self.topchladenie_csv_drop_area.label.setText(f"Načítaný súbor: {filename} ({len(df)} produktov)")
            self.scrape_topchladenie_checkbox.setChecked(False)
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nepodarilo sa načítať CSV súbor:\n{e}")

    def generate_and_export_csv(self):
        if self.main_df is None:
            QMessageBox.warning(self, "Chýbajúce dáta", "Najprv nahrajte hlavný CSV súbor.")
            return

        selected_categories = [self.category_list.item(i).text() for i in range(self.category_list.count()) if self.category_list.item(i).checkState() == Qt.Checked]
        if not selected_categories:
            QMessageBox.warning(self, "Chýbajúci výber", "Vyberte aspoň jednu kategóriu.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.generate_button.setEnabled(False)

        options = {
            'map_categories': self.map_categories_checkbox.isChecked(),
            'variant_checkbox': self.variant_checkbox.isChecked(),
            'ai_enhancement_checkbox': self.ai_enhancement_checkbox.isChecked(),
            'enable_gastromarket': self.gastromarket_checkbox.isChecked(),
            'enable_forgastro': self.forgastro_checkbox.isChecked(),
            'scrape_topchladenie': self.scrape_topchladenie_checkbox.isChecked(),
            'topchladenie_csv_df': self.topchladenie_csv_drop_area.topchladenie_df
        }

        self.thread = QThread()
        self.worker = Worker(self.main_df, selected_categories, self.config, options)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.result.connect(self.handle_result)
        self.worker.error.connect(self.show_error_message)
        self.worker.progress.connect(self.update_progress)
        
        self.thread.start()
        self.thread.finished.connect(lambda: self.generate_button.setEnabled(True))
        self.thread.finished.connect(lambda: self.progress_bar.setVisible(False))

    def update_progress(self, message):
        self.progress_bar.setFormat(message)

    def show_error_message(self, error_info):
        title, message = error_info
        QMessageBox.critical(self, title, message)
    
    def handle_result(self, result: PipelineResult):
        self.last_statistics = result.statistics
        self.save_final_csv(result.dataframe)

    def save_final_csv(self, final_df):
        save_path, _ = QFileDialog.getSaveFileName(self, "Uložiť výsledný CSV súbor", QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) + "/Merged.csv", "CSV files (*.csv)")
        if save_path:
            try:
                final_df.to_csv(save_path, index=False, sep=';', encoding='cp1250', errors='replace')
                QMessageBox.information(self, "Export úspešný", f"Dáta boli úspešne exportované do {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Chyba pri ukladaní", f"Nepodarilo sa uložiť súbor.\nChyba: {e}")
