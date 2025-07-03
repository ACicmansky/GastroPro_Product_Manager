"""
GASTROPRO Product Manager
Main application module that integrates all components
"""
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QDesktopWidget,
    QProgressBar, QSplitter
)
from PyQt5.QtCore import Qt, QThread, QStandardPaths, QTimer

# Import our components
from ui.drop_area import DropArea
from ui.filter_panel import FilterPanel
from ui.table_view_manager import TableViewManager
from ui.theme_manager import ThemeManager
from services.data_loader import DataManager
from services.worker import Worker
from utils import load_config


class ProductManager(QMainWindow):
    """
    Main application window for GASTROPRO Product Manager
    Integrates all components and manages the application flow
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GASTROPRO Product Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Load configuration
        self.config = load_config()
        if not self.config:
            QMessageBox.critical(self, "Chyba konfigurácie", 
                               "Nepodarilo sa načítať konfiguračný súbor. Aplikácia sa ukončí.")
            sys.exit(1)
        
        # Initialize managers and services
        self.theme_manager = ThemeManager()
        self.data_manager = DataManager()
        
        # Set up UI
        self.init_ui()
        self.center_window()
        self.apply_theme()
        
        # Connect signals
        self.connect_signals()
        
        # Thread for background processing
        self.thread = None
        self.worker = None
    
    def center_window(self):
        """Center the window on screen"""
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
    
    def apply_theme(self):
        """Apply the current theme"""
        stylesheet = self.theme_manager.load_stylesheet()
        self.setStyleSheet(stylesheet)
        
        # Update widget styles based on current theme
        is_dark = self.theme_manager.is_dark_mode()
        self.central_widget.setObjectName(f"central_widget{'_dark' if is_dark else ''}")
        self.filter_panel.setObjectName(f"glass{'_dark' if is_dark else ''}")
        self.dark_mode_button.setText("Light Mode" if is_dark else "Dark Mode")
        
    def init_ui(self):
        """Initialize the user interface"""
        # Main layout
        self.central_widget = QWidget()
        self.central_widget.setObjectName("central_widget")
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # --- Top controls ---
        top_controls = QHBoxLayout()
        
        # Dark Mode Toggle
        self.dark_mode_button = QPushButton("Dark Mode")
        self.dark_mode_button.clicked.connect(self.toggle_dark_mode)
        self.dark_mode_button.setMaximumWidth(100)
        top_controls.addWidget(self.dark_mode_button)
        
        # CSV Upload
        upload_button = QPushButton("Nahrať CSV")
        upload_button.clicked.connect(self.select_csv_file)
        upload_button.setMinimumWidth(120)
        top_controls.addWidget(upload_button)
        
        # Export Button
        self.generate_button = QPushButton("Generovať a Exportovať CSV")
        self.generate_button.clicked.connect(self.generate_and_export_csv)
        self.generate_button.setVisible(False)
        self.generate_button.setMinimumWidth(180)
        top_controls.addWidget(self.generate_button)
        
        top_controls.addStretch(1)
        self.layout.addLayout(top_controls)
        
        # --- Drop Area ---
        self.drop_area = DropArea(self)
        self.layout.addWidget(self.drop_area)
        
        # --- Main Content - Split into filter panel and tables ---
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # --- Left Side: Filter Panel ---
        self.filter_panel = FilterPanel()
        self.filter_panel.setVisible(False)
        
        # --- Right Side: Table Manager ---
        self.table_manager = TableViewManager()
        
        # Add both panels to the main splitter
        self.main_splitter.addWidget(self.filter_panel)
        self.main_splitter.addWidget(self.table_manager)
        
        # Set initial sizes (30% for filter panel, 70% for tables)
        self.main_splitter.setSizes([300, 700])
        
        # Add main splitter to layout
        self.layout.addWidget(self.main_splitter)
        
        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)
    
    def connect_signals(self):
        """Connect signals between components"""
        # Theme manager signals
        self.theme_manager.themeChanged.connect(lambda _: self.apply_theme())
        
        # Data manager signals
        self.data_manager.dataLoaded.connect(self.table_manager.set_input_data)
        self.data_manager.categoriesLoaded.connect(self.filter_panel.populate_categories)
        self.data_manager.categoriesLoaded.connect(self.on_categories_loaded)
        self.data_manager.seoPreservedCountUpdated.connect(self.on_seo_preserved_count_updated)
        
        # Filter panel signals
        self.filter_panel.categorySelectionChanged.connect(self.on_filter_criteria_changed)
        self.filter_panel.seoPreservationChanged.connect(self.on_filter_criteria_changed)
        
        # Table manager signals
        self.table_manager.dataChanged.connect(self.on_filter_criteria_changed)
    
    def toggle_dark_mode(self):
        """Toggle between dark and light mode"""
        self.theme_manager.toggle_dark_mode()
    
    def select_csv_file(self):
        """Open file dialog to select a CSV file"""
        downloads_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        file_path, _ = QFileDialog.getOpenFileName(self, "Vyberte CSV súbor", downloads_path, "CSV files (*.csv)")
        if file_path:
            self.load_csv_file(file_path)
    
    def load_csv_file(self, file_path):
        """Load data from a CSV file"""
        self.reset_ui()
        
        # Try to load the file
        success, message = self.data_manager.load_csv_file(file_path)
        
        if success:
            # Update UI
            self.drop_area.label.setText(f"Nahraný súbor: {file_path.split('/')[-1]}")
            self.drop_area.setMaximumHeight(50)  # Reduce size after loading
        else:
            # Show error message
            QMessageBox.critical(self, "Chyba načítania", message)
            self.reset_ui()
    
    def on_categories_loaded(self, categories):
        """Handle successful loading of categories"""
        if categories:
            self.filter_panel.setVisible(True)
            self.generate_button.setVisible(True)
    
    def on_filter_criteria_changed(self):
        """Handle changes in filter criteria"""
        # Get selected categories and SEO preservation setting
        selected_categories = self.filter_panel.get_selected_categories()
        preserve_seo = self.filter_panel.is_seo_preservation_enabled()
        
        # Apply filter to input table
        filter_mask = self.data_manager.filter_data(selected_categories, preserve_seo)
        self.table_manager.filter_input_rows(filter_mask)
    
    def on_seo_preserved_count_updated(self, count, preserved_products):
        """Handle update of SEO preserved products count"""
        self.filter_panel.update_seo_count(count)
        if count > 0 and preserved_products is not None:
            self.filter_panel.populate_seo_details(preserved_products)
    
    def generate_and_export_csv(self):
        """Generate and export the filtered data as CSV"""
        # Check if we have data in the output table
        output_df = self.table_manager.get_output_data()
        
        if output_df.empty:
            QMessageBox.warning(self, "Prázdny výstup", 
                              "Tabuľka výstupu je prázdna. Pridajte produkty do výstupu pomocou tlačidla 'Pridať vybrané riadky do výstupu'.")
            return

        # Get save location
        output_file, _ = QFileDialog.getSaveFileName(self, "Uložiť CSV", "", "CSV súbory (*.csv)")
        if not output_file:
            return
            
        # Get selected categories for XML feed processing
        selected_categories = self.filter_panel.get_selected_categories()
        preserve_seo = self.filter_panel.is_seo_preservation_enabled()

        # Set up worker in background thread
        self.thread = QThread()
        self.worker = Worker(output_df, selected_categories, self.config, preserve_seo)
        
        # Move worker to thread
        self.worker.moveToThread(self.thread)
        
        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(lambda: self.progress_bar.setVisible(False))
        
        self.worker.progress.connect(self.update_progress)
        self.worker.error.connect(self.show_error_message)
        self.worker.result.connect(lambda df: self.save_final_csv(df, output_file))
        
        # Start processing
        self.progress_bar.setVisible(True)
        self.thread.start()
    
    def update_progress(self, message):
        """Update the progress bar message"""
        self.progress_bar.setFormat(message)
        self.progress_bar.setAlignment(Qt.AlignCenter)
    
    def show_error_message(self, error_info):
        """Show error message from worker thread"""
        title, message = error_info
        QMessageBox.critical(self, title, message)
    
    def save_final_csv(self, final_df, output_file):
        """Save the final processed dataframe as CSV"""
        try:
            # Ensure the file ends with .csv
            if not output_file.lower().endswith('.csv'):
                output_file += '.csv'
                
            # Save with semicolon separator and proper encoding for Central European characters
            final_df.to_csv(output_file, sep=';', encoding='utf-8-sig', index=False)
            
            QMessageBox.information(self, "Export úspešný", 
                                 f"CSV súbor bol úspešne vygenerovaný a uložený do:\n{output_file}\n\nPočet produktov: {len(final_df)}")
        except Exception as e:
            QMessageBox.critical(self, "Chyba pri ukladaní", f"Nepodarilo sa uložiť CSV súbor:\n{e}")
    
    def reset_ui(self):
        """Reset UI components to their initial state"""
        self.drop_area.label.setText("Presuňte CSV súbor sem alebo kliknite na tlačidlo nižšie")
        self.drop_area.setMaximumHeight(200)
        self.filter_panel.setVisible(False)
        self.generate_button.setVisible(False)
        self.progress_bar.setVisible(False)
        self.table_manager.reset()
        self.data_manager.reset()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop any running threads
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = ProductManager()
    main_win.show()
    sys.exit(app.exec_())
