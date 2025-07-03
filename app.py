# app.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QListWidget,
    QCheckBox, QListWidgetItem, QDesktopWidget, QFrame, QLineEdit, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

from utils import load_config, fetch_xml_feed, parse_xml_feed, merge_dataframes, load_csv_data

class DropArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.label = QLabel("Presuňte CSV súbor sem alebo kliknite na tlačidlo nižšie")
        self.label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith('.csv'):
                self.parent().load_csv_file(file_path)

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
        self.dark_mode = False

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

        # --- Dark Mode Toggle ---
        self.dark_mode_button = QPushButton("Dark Mode")
        self.dark_mode_button.clicked.connect(self.toggle_dark_mode)
        self.layout.addWidget(self.dark_mode_button)

        # --- CSV Upload ---
        self.drop_area = DropArea(self)
        self.layout.addWidget(self.drop_area)
        upload_button = QPushButton("Vybrať CSV")
        upload_button.clicked.connect(self.select_csv_file)
        self.layout.addWidget(upload_button)

        # --- Category Filter ---
        self.filter_group = QWidget()
        self.filter_group.setObjectName("glass")
        filter_layout = QVBoxLayout(self.filter_group)
        filter_label = QLabel("Vyberte kategórie na export:")
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Hľadať kategórie...")
        self.search_bar.textChanged.connect(self.filter_categories)
        self.select_all_checkbox = QCheckBox("Vybrať všetky kategórie")
        self.select_all_checkbox.stateChanged.connect(self.toggle_all_categories)
        self.category_list = QListWidget()
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.search_bar)
        filter_layout.addWidget(self.select_all_checkbox)
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

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.central_widget.setObjectName("central_widget dark")
            self.filter_group.setObjectName("glass dark")
            self.dark_mode_button.setText("Light Mode")
        else:
            self.central_widget.setObjectName("central_widget")
            self.filter_group.setObjectName("glass")
            self.dark_mode_button.setText("Dark Mode")
        self.load_stylesheet()

    def filter_categories(self, text):
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def _reset_ui(self):
        self.main_df = None
        self.drop_area.label.setText("Presuňte CSV súbor sem alebo kliknite na tlačidlo nižšie")
        self.filter_group.setVisible(False)
        self.generate_button.setVisible(False)
        self.progress_bar.setVisible(False)

    def select_csv_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Vyberte CSV súbor", "", "CSV files (*.csv)")
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
            item.setCheckState(Qt.Checked)
            self.category_list.addItem(item)
        self.select_all_checkbox.setChecked(True)

    def toggle_all_categories(self, state):
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            item.setCheckState(Qt.Checked if state == Qt.Checked else Qt.Unchecked)

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
                final_df.to_csv(save_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "Great success!", f"Súbor bol úspešne uložený do: {save_path}")
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