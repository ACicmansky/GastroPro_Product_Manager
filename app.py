# app.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QListWidget,
    QListWidgetItem, QDesktopWidget, QFrame, QLineEdit, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QStandardPaths

from utils import load_config, fetch_xml_feed, parse_xml_feed, merge_dataframes, load_csv_data

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

class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    progress = pyqtSignal(str)
    result = pyqtSignal(object)

    def __init__(self, main_df, selected_categories, config):
        super().__init__()
        self.main_df = main_df
        self.selected_categories = selected_categories
        self.config = config

    def run(self):
        try:
            self.progress.emit("Filtering main CSV...")
            filtered_df = self.main_df[self.main_df['Hlavna kategória'].isin(self.selected_categories)].copy()

            if filtered_df.empty:
                self.error.emit(("Prázdny výsledok", "Žiadne produkty nespĺňajú vybrané kritériá."))
                self.finished.emit()
                return

            self.progress.emit(f"Starting to fetch {len(self.config['xml_feeds'])} XML feeds...")
            feed_dataframes = []
            for feed_name, feed_info in self.config['xml_feeds'].items():
                self.progress.emit(f"Fetching feed: {feed_name}")
                try:
                    root = fetch_xml_feed(feed_info['url'])
                    if root is None:
                        continue
                    
                    self.progress.emit(f"Parsing feed: {feed_name}")
                    df = parse_xml_feed(root, feed_info['root_element'], feed_info['mapping'], feed_name)
                    
                    if df is not None and not df.empty:
                        feed_dataframes.append(df)
                except Exception as e:
                    self.error.emit(("Chyba pri spracovaní feedu", f"Chyba pri spracovaní feedu {feed_name}: {e}"))

            self.progress.emit("Merging dataframes...")
            final_df = merge_dataframes(filtered_df, feed_dataframes, self.config['final_csv_columns'])
            self.result.emit(final_df)
        except Exception as e:
            self.error.emit(("Chyba generovania", f"Pri generovaní došlo k chybe:\n{e}"))
        finally:
            self.finished.emit()

class ProductManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GASTROPRO Product Manager")
        self.setGeometry(100, 100, 600, 400)
        self.main_df = None
        self.categories = []
        self.config = load_config()

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
        
        # Replace checkbox with button for selecting all categories
        self.select_all_button = QPushButton("Prepnúť všetky")
        self.select_all_button.clicked.connect(self.select_all_categories)
        self.select_all_button.setToolTip("Prepnúť všetky kategórie")
        self.select_all_button.setMaximumWidth(130)
        
        # Button for filtered categories
        self.toggle_filtered_button = QPushButton("Prepnúť filtrované")
        self.toggle_filtered_button.clicked.connect(self.toggle_filtered_categories)
        self.toggle_filtered_button.setToolTip("Označiť/odznačiť všetky filtrované kategórie")
        self.toggle_filtered_button.setMaximumWidth(130)
        
        # Add buttons to horizontal layout
        buttons_layout.addWidget(self.select_all_button)
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

    def _reset_ui(self):
        self.main_df = None
        self.drop_area.label.setText("Presuňte CSV súbor sem alebo kliknite sem pre výber súboru")
        self.filter_group.setVisible(False)
        self.generate_button.setVisible(False)
        self.progress_bar.setVisible(False)

    def select_csv_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Vyberte CSV súbor", QStandardPaths.writableLocation(QStandardPaths.DownloadLocation), "CSV files (*.csv)")
        if file_path:
            self.load_csv_file(file_path)

    def load_csv_file(self, file_path):
        try:
            self.main_df = load_csv_data(file_path)
            
            if self.main_df is None or self.main_df.empty:
                self._reset_ui()
                return

            self.drop_area.label.setText(f"Nahraný súbor: {file_path.split('/')[-1]}")
            
            if 'Hlavna kategória' in self.main_df.columns:
                self.categories = sorted(self.main_df['Hlavna kategória'].dropna().unique().tolist())
                self.populate_category_list()
                self.filter_group.setVisible(True)
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

    def select_all_categories(self):
        # Toggle between selecting all and deselecting all
        all_checked = True
        
        # Check if all items are already checked
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.checkState() != Qt.Checked:
                all_checked = False
                break
        
        # Set all items to the opposite state
        new_state = Qt.Unchecked if all_checked else Qt.Checked
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setCheckState(new_state)
            
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

        if not selected_categories:
            QMessageBox.warning(self, "Bez výberu", "Vyberte aspoň jednu kategóriu na export.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Indeterminate progress

        self.thread = QThread()
        self.worker = Worker(self.main_df, selected_categories, self.config)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.result.connect(self.save_final_csv)
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

    def save_final_csv(self, final_df):
        save_path, _ = QFileDialog.getSaveFileName(self, "Uložiť výsledný CSV súbor", "Merged.csv", "CSV files (*.csv)")
        if save_path:
            try:
                # First try cp1250 with character replacement
                try:
                    # Handle characters that can't be encoded in cp1250
                    # Convert problematic characters first
                    for col in final_df.columns:
                        if final_df[col].dtype == 'object':
                            final_df[col] = final_df[col].astype(str).apply(
                                lambda x: ''.join(c if c.encode('cp1250', errors='replace') != b'?' else ' ' for c in x)
                            )
                    
                    final_df.to_csv(save_path, index=False, encoding='cp1250', sep=';')
                    QMessageBox.information(self, "Great success!", f"Súbor bol úspešne uložený do: {save_path}")
                except UnicodeEncodeError:
                    # Fall back to UTF-8 with BOM for Excel compatibility
                    final_df.to_csv(save_path, index=False, encoding='utf-8-sig', sep=';')
                    QMessageBox.information(self, "Great success!", 
                        f"Súbor bol uložený do: {save_path}\n\nPoznámka: Použité kódovanie UTF-8 namiesto cp1250 kvôli nekompatibilným znakom.")
            except Exception as e:
                self.show_error_message(("Chyba pri ukladaní", f"Pri ukladaní súboru došlo k chybe:\n{e}"))

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Ukončiť', "Naozaj chcete aplikáciu ukončiť?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = ProductManager()
    main_win.show()
    sys.exit(app.exec_())