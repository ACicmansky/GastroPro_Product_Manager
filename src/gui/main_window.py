"""
Main Window for new 138-column format GUI.
Simplified interface focused on XML feed processing and AI enhancement.
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QDesktopWidget,
    QProgressBar,
    QCheckBox,
    QGroupBox,
    QLabel,
    QFrame,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QListView,
    QShortcut,
)
from PyQt5.QtCore import Qt, QThread, QStandardPaths
from PyQt5.QtGui import QKeySequence

from .worker import PipelineWorker, AIResumeWorker
from .widgets import CategoryMappingDialog, PriceMappingDialog
from src.config.config_loader import load_config
from src.domain.categories.category_service import CategoryService
from src.data.loaders.xlsx_loader import load_xlsx
from src.domain.categories.category_filter import CategoryFilter
from src.domain.models import PipelineOptions
from src.data.database.run_db import RunDB
from src.ai.run_control import RunControl
from .theme import apply_theme, current_theme_mode, save_theme_mode, set_variant

PIPELINE_STAGES = [
    ("load", "Načítanie"),
    ("feeds", "Feedy"),
    ("scrape", "Scraping"),
    ("merge", "Zlúčenie"),
    ("categories", "Kategórie"),
    ("ai", "AI"),
    ("export", "Export"),
]

THEME_MODE_LABELS = {"auto": "🌓 Auto", "light": "☀️ Svetlá", "dark": "🌙 Tmavá"}


class MainWindow(QMainWindow):
    """Main window for new 138-column format processing."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GastroPro Product Manager")
        self.resize(1080, 720)
        self.setMinimumSize(940, 620)
        self.setAcceptDrops(True)
        self.main_data_file = None
        self.config = load_config()
        self.last_statistics = None
        self.result_df = None
        self.category_filter = CategoryFilter()
        self.category_service = CategoryService()
        self.all_categories = []
        self.main_data_df = None
        self.ai_control = RunControl()

        if not self.config:
            QMessageBox.critical(
                self,
                "Chyba konfigurácie",
                "Nepodarilo sa načítať konfiguračný súbor. Aplikácia sa ukončí.",
            )
            sys.exit(1)

        self.init_ui()
        self.center_window()
        self._check_resumable_ai_run()

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
        self.layout.setContentsMargins(16, 12, 16, 12)
        self.layout.setSpacing(10)

        # Header: title left, theme toggle right
        header = QHBoxLayout()
        title = QLabel("GastroPro Product Manager")
        title.setObjectName("appTitle")
        header.addWidget(title)
        header.addStretch()
        self.theme_button = QPushButton(THEME_MODE_LABELS[current_theme_mode()])
        self.theme_button.setObjectName("themeToggle")
        self.theme_button.setToolTip("Prepnúť tému (Auto / Svetlá / Tmavá)")
        self.theme_button.setCursor(Qt.PointingHandCursor)
        self.theme_button.clicked.connect(self._cycle_theme)
        header.addWidget(self.theme_button)
        self.layout.addLayout(header)

        # Two-pane content: sources & options left, categories + results right
        content = QHBoxLayout()
        content.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(10)
        self._create_main_data_section(left)
        self._create_xml_feeds_section(left)
        self._create_processing_options(left)
        self._create_ai_run_controls(left)
        left.addStretch()

        right = QVBoxLayout()
        right.setSpacing(10)
        self._create_category_filter_section(right)
        self.empty_state = QLabel(
            "📄\n\nNačítajte XLSX súbor (Ctrl+O)\nalebo ho presuňte sem\n\n"
            "Zobrazí sa filter kategórií a výsledky spracovania"
        )
        self.empty_state.setObjectName("emptyState")
        self.empty_state.setAlignment(Qt.AlignCenter)
        right.addWidget(self.empty_state, 1)
        self._create_statistics_display(right)

        content.addLayout(left, 2)
        content.addLayout(right, 3)
        self.layout.addLayout(content, 1)

        # Footer: stage tracker, progress, primary action
        self._create_stage_tracker(self.layout)
        self._create_progress_bar(self.layout)
        self._create_process_button(self.layout)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self.select_main_data_file)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.process_and_export)

    def _cycle_theme(self):
        order = ["auto", "light", "dark"]
        mode = order[(order.index(current_theme_mode()) + 1) % len(order)]
        save_theme_mode(mode)
        apply_theme(QApplication.instance())
        self.theme_button.setText(THEME_MODE_LABELS[mode])

    def _create_main_data_section(self, parent):
        """Create main data file selection section."""
        group = QGroupBox("Hlavné dáta (voliteľné)")
        layout = QVBoxLayout(group)

        self.main_data_label = QLabel("Žiadny súbor nie je načítaný")
        self.main_data_label.setProperty("variant", "hint")

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

        parent.addWidget(group)

    def _create_category_filter_section(self, parent):
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
        layout.addWidget(self.category_list, 1)

        # Info label
        self.category_info_label = QLabel("")
        self.category_info_label.setProperty("variant", "hint")
        layout.addWidget(self.category_info_label)

        parent.addWidget(self.category_filter_group, 1)

        # Hide by default (show when main data loaded)
        self.category_filter_group.setVisible(False)

    def _create_xml_feeds_section(self, parent):
        """Create XML feeds selection section."""
        group = QGroupBox("XML Feedy")
        layout = QVBoxLayout(group)

        self.gastromarket_checkbox = QCheckBox("Načítať z GastroMarket XML")
        self.gastromarket_stalgast_checkbox = QCheckBox(
            "Načítať z GastroMarket STALGAST XML"
        )
        self.forgastro_checkbox = QCheckBox("Načítať z ForGastro XML")

        self.gastromarket_checkbox.setChecked(False)
        self.gastromarket_stalgast_checkbox.setChecked(False)
        self.forgastro_checkbox.setChecked(False)

        layout.addWidget(self.gastromarket_checkbox)
        layout.addWidget(self.gastromarket_stalgast_checkbox)
        layout.addWidget(self.forgastro_checkbox)

        info_label = QLabel(
            "<small><i>XML feedy sa automaticky stiahnu a spracujú. "
            "URL adresy sú nakonfigurované v config.json.</i></small>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        parent.addWidget(group)

    def _create_processing_options(self, parent):
        """Create processing options section."""
        group = QGroupBox("Možnosti spracovania")
        layout = QVBoxLayout(group)

        is_ai_enhancement_enabled = False
        self.ai_enhancement_checkbox = QCheckBox("Použiť AI vylepšenie")
        self.ai_enhancement_checkbox.setChecked(is_ai_enhancement_enabled)
        self.ai_enhancement_checkbox.stateChanged.connect(self._update_force_reprocess)

        self.force_reprocess_checkbox = QCheckBox("Vynútiť AI vylepšenie")
        self.force_reprocess_checkbox.setChecked(False)
        self.force_reprocess_checkbox.setEnabled(is_ai_enhancement_enabled)

        self.web_scraping_checkbox = QCheckBox("Web scraping (TopChladenie.sk)")
        self.web_scraping_checkbox.setChecked(False)

        self.mebella_scraping_checkbox = QCheckBox("Web scraping (Mebella.pl)")
        self.mebella_scraping_checkbox.setChecked(False)

        self.update_categories_checkbox = QCheckBox("Aktualizovať kategórie z feedov")
        self.update_categories_checkbox.setChecked(False)
        self.update_categories_checkbox.setToolTip(
            "Ak je zaškrtnuté, kategórie produktov budú prepísané hodnotami z XML feedov/scrapingu."
        )

        self.preserve_edits_checkbox = QCheckBox(
            "Zachovať úpravy e-shopu (iba ceny a sklad z feedu)"
        )
        self.preserve_edits_checkbox.setChecked(False)
        self.preserve_edits_checkbox.setEnabled(
            False
        )  # enabled only when main data is loaded
        self.preserve_edits_checkbox.setToolTip(
            "Zachová opisy, obrázky, kategórie a ceny z e-shopu. "
            "Z feedu sa aktualizuje len standardPrice a sklad. "
            "Produkty, ktoré vypadli z feedu dodávateľa, budú odstránené."
        )

        layout.addWidget(self.ai_enhancement_checkbox)
        layout.addWidget(self.force_reprocess_checkbox)
        layout.addWidget(self.web_scraping_checkbox)
        layout.addWidget(self.mebella_scraping_checkbox)
        layout.addWidget(self.update_categories_checkbox)
        layout.addWidget(self.preserve_edits_checkbox)

        parent.addWidget(group)

    def _create_ai_run_controls(self, parent):
        """AI run tracking: resume banner + pause/cancel while an AI stage is active."""
        group = QGroupBox("AI spracovanie")
        layout = QVBoxLayout(group)

        self.ai_resume_banner = QLabel("")
        self.ai_resume_banner.setWordWrap(True)
        self.ai_resume_banner.setProperty("variant", "warning")
        self.ai_resume_banner.setVisible(False)

        self.ai_resume_button = QPushButton("Pokračovať v AI spracovaní")
        self.ai_resume_button.setProperty("primary", True)
        self.ai_resume_button.setVisible(False)
        self.ai_resume_button.clicked.connect(self._start_ai_resume)

        buttons_row = QHBoxLayout()
        self.ai_pause_button = QPushButton("Pozastaviť AI")
        self.ai_pause_button.setEnabled(False)
        self.ai_pause_button.clicked.connect(self._pause_ai)
        self.ai_cancel_button = QPushButton("Zrušiť AI")
        self.ai_cancel_button.setProperty("danger", True)
        self.ai_cancel_button.setEnabled(False)
        self.ai_cancel_button.clicked.connect(self._cancel_ai)
        buttons_row.addWidget(self.ai_pause_button)
        buttons_row.addWidget(self.ai_cancel_button)

        layout.addWidget(self.ai_resume_banner)
        layout.addWidget(self.ai_resume_button)
        layout.addLayout(buttons_row)
        parent.addWidget(group)
        self.ai_run_group = group

    def _check_resumable_ai_run(self):
        """DB-only check (no API key needed) — shows the resume banner if a run was interrupted."""
        db_path = self.config.get("db_path", "data/products.db") if self.config else "data/products.db"
        resumable = RunDB(db_path).get_resumable_run()
        if resumable and resumable["status"] in ("paused", "interrupted"):
            self.ai_resume_banner.setText(
                f"Prerušené AI spracovanie ({resumable['status']}): "
                f"{resumable['processed_products']}/{resumable['total_products']} produktov hotových."
                + (f" [{resumable['detail']}]" if resumable["detail"] else "")
            )
            self.ai_resume_banner.setVisible(True)
            self.ai_resume_button.setVisible(True)
        else:
            self.ai_resume_banner.setVisible(False)
            self.ai_resume_button.setVisible(False)

    def _pause_ai(self):
        self.ai_control.pause()
        self.ai_pause_button.setEnabled(False)
        self.update_progress("Pozastavovanie AI spracovania (dokončí sa po aktuálnej dávke)...")

    def _cancel_ai(self):
        confirm = QMessageBox.question(
            self, "Zrušiť AI spracovanie",
            "Naozaj chcete zrušiť prebiehajúcu AI dávku? Doteraz spracované produkty zostanú uložené.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.ai_control.cancel()
            self.ai_pause_button.setEnabled(False)
            self.ai_cancel_button.setEnabled(False)

    def _start_ai_resume(self):
        """Continue an interrupted AI run — DB in, DB out, no feeds/merge/file dialogs."""
        self.ai_resume_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Pokračujem v AI spracovaní...")
        self.status_label.setVisible(True)
        self._set_ui_enabled(False)
        self.ai_pause_button.setEnabled(True)
        self.ai_cancel_button.setEnabled(True)

        self.ai_control = RunControl()
        self.ai_thread = QThread()
        self.ai_worker = AIResumeWorker(self.config, ai_control=self.ai_control)
        self.ai_worker.moveToThread(self.ai_thread)

        self.ai_thread.started.connect(self.ai_worker.run)
        self.ai_worker.finished.connect(self.ai_thread.quit)
        self.ai_worker.finished.connect(self.ai_worker.deleteLater)
        self.ai_thread.finished.connect(self.ai_thread.deleteLater)
        self.ai_worker.result.connect(self.handle_result)
        self.ai_worker.error.connect(self.show_error_message)
        self.ai_worker.progress.connect(self.update_progress)

        self.ai_thread.finished.connect(lambda: self._set_ui_enabled(True))
        self.ai_thread.finished.connect(lambda: self.progress_bar.setVisible(False))
        self.ai_thread.finished.connect(lambda: self.status_label.setVisible(False))
        self.ai_thread.finished.connect(lambda: self.ai_pause_button.setEnabled(False))
        self.ai_thread.finished.connect(lambda: self.ai_cancel_button.setEnabled(False))
        self.ai_thread.finished.connect(self._check_resumable_ai_run)

        self.ai_thread.start()

    def _create_stage_tracker(self, parent):
        """Horizontal pipeline step indicator (driven by the worker's stage signal)."""
        self.stage_row = QWidget()
        row = QHBoxLayout(self.stage_row)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(8)
        self.stage_labels = {}
        for i, (key, name) in enumerate(PIPELINE_STAGES):
            if i:
                sep = QLabel("›")
                sep.setProperty("variant", "hint")
                row.addWidget(sep)
            label = QLabel(name)
            label.setProperty("stage", "pending")
            row.addWidget(label)
            self.stage_labels[key] = label
        row.addStretch()
        parent.addWidget(self.stage_row)
        self.stage_row.setVisible(False)

    def _set_stage(self, active_key):
        """Mark stages before active_key done, active_key active, the rest pending."""
        seen = False
        for key, name in PIPELINE_STAGES:
            if key == active_key:
                state, seen = "active", True
            elif not seen:
                state = "done"
            else:
                state = "pending"
            label = self.stage_labels[key]
            label.setText(f"✓ {name}" if state == "done" else name)
            label.setProperty("stage", state)
            label.style().unpolish(label)
            label.style().polish(label)

    def _finish_stages(self):
        self._set_stage(None)  # no active key -> everything done

    def _reset_stages(self):
        for key, name in PIPELINE_STAGES:
            label = self.stage_labels[key]
            label.setText(name)
            label.setProperty("stage", "pending")
            label.style().unpolish(label)
            label.style().polish(label)

    def _create_progress_bar(self, parent):
        """Create progress bar with a status line (indeterminate bars can't show text)."""
        self.progress_bar = QProgressBar()
        parent.addWidget(self.progress_bar)
        self.progress_bar.setVisible(False)

        self.status_label = QLabel("")
        self.status_label.setProperty("variant", "hint")
        parent.addWidget(self.status_label)
        self.status_label.setVisible(False)

    def _create_process_button(self, parent):
        """Create process button."""
        self.process_button = QPushButton("Spracovať a exportovať")
        self.process_button.setProperty("primary", True)
        self.process_button.setMinimumHeight(46)
        self.process_button.setCursor(Qt.PointingHandCursor)
        self.process_button.setToolTip("Spustiť spracovanie (Ctrl+R)")
        self.process_button.clicked.connect(self.process_and_export)
        parent.addWidget(self.process_button)

    def _create_statistics_display(self, parent):
        """Create results panel (KPI tiles + note)."""
        group = QGroupBox("Výsledky")
        layout = QVBoxLayout(group)

        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(8)
        layout.addLayout(self.kpi_grid)

        self.stats_note = QLabel("")
        self.stats_note.setProperty("variant", "hint")
        self.stats_note.setWordWrap(True)
        layout.addWidget(self.stats_note)

        parent.addWidget(group)
        group.setVisible(False)
        self.stats_group = group

    def _kpi_tile(self, value, caption):
        tile = QFrame()
        tile.setProperty("kpi", True)
        v = QVBoxLayout(tile)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(2)
        value_label = QLabel(str(value))
        value_label.setProperty("kpiValue", True)
        caption_label = QLabel(caption)
        caption_label.setProperty("kpiCaption", True)
        v.addWidget(value_label)
        v.addWidget(caption_label)
        return tile

    def _update_right_pane(self):
        """Empty-state placeholder shows only when there is nothing else to show."""
        self.empty_state.setVisible(
            not self.category_filter_group.isVisible() and not self.stats_group.isVisible()
        )

    def dragEnterEvent(self, event):
        """Accept XLSX files dragged anywhere onto the window."""
        if event.mimeData().hasUrls() and any(
            url.toLocalFile().lower().endswith(".xlsx") for url in event.mimeData().urls()
        ):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".xlsx"):
                self.load_main_data_file(path)
                break

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
            df = load_xlsx(file_path)

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
            set_variant(self.main_data_label, "success")
            self.clear_main_button.setEnabled(True)
            self.preserve_edits_checkbox.setEnabled(True)

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
        set_variant(self.main_data_label, "hint")
        self.clear_main_button.setEnabled(False)

        # Hide category filter section
        self.category_filter_group.setVisible(False)
        self._update_right_pane()
        self.all_categories = []
        self.category_list.clear()
        self.preserve_edits_checkbox.setEnabled(False)
        self.preserve_edits_checkbox.setChecked(False)

    def process_and_export(self):
        """Process data and export results."""
        # Validate: at least one data source must be selected
        if (
            self.main_data_file is None
            and not self.gastromarket_checkbox.isChecked()
            and not self.gastromarket_stalgast_checkbox.isChecked()
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

        # Ask for output path before starting
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Uložiť výsledný súbor",
            QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
            + f"/{datetime.now().strftime('%Y_%m_%d')}_GastroPro.xlsx",
            "XLSX files (*.xlsx)",
        )
        if not output_path:
            return

        # Prepare options
        options = PipelineOptions(
            main_file_path=self.main_data_file or "",
            output_path=output_path,
            selected_categories=(
                self.get_selected_categories() if self.main_data_file else []
            ),
            enabled_feeds=[
                name
                for name, checkbox in (
                    ("gastromarket", self.gastromarket_checkbox),
                    ("gastromarket_stalgast", self.gastromarket_stalgast_checkbox),
                    ("forgastro", self.forgastro_checkbox),
                )
                if checkbox.isChecked()
            ],
            enable_scraping=(
                self.web_scraping_checkbox.isChecked()
                or self.mebella_scraping_checkbox.isChecked()
            ),
            enable_ai_enhancement=self.ai_enhancement_checkbox.isChecked(),
            preserve_client_edits=self.preserve_edits_checkbox.isChecked(),
            force_ai_reprocess=self.force_reprocess_checkbox.isChecked(),
            scrape_mebella=self.mebella_scraping_checkbox.isChecked(),
            scrape_topchladenie=self.web_scraping_checkbox.isChecked(),
            topchladenie_csv_path=getattr(self, "topchladenie_csv_path", ""),
            enable_price_mapping=self.mebella_scraping_checkbox.isChecked(),
        )

        # Show progress and disable UI
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Spúšťam spracovanie...")
        self.status_label.setVisible(True)
        self._reset_stages()
        self.stage_row.setVisible(True)
        self._set_ui_enabled(False)
        self.stats_group.setVisible(False)
        self._update_right_pane()

        # Create worker thread
        self.ai_control = RunControl()
        if options.enable_ai_enhancement:
            self.ai_pause_button.setEnabled(True)
            self.ai_cancel_button.setEnabled(True)
        self.thread = QThread()
        self.worker = PipelineWorker(self.config, options, ai_control=self.ai_control)
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
        self.worker.stage.connect(self._set_stage)

        # Cleanup
        self.thread.finished.connect(lambda: self._set_ui_enabled(True))
        self.thread.finished.connect(lambda: self.progress_bar.setVisible(False))
        self.thread.finished.connect(lambda: self.status_label.setVisible(False))
        self.thread.finished.connect(lambda: self.ai_pause_button.setEnabled(False))
        self.thread.finished.connect(lambda: self.ai_cancel_button.setEnabled(False))
        self.thread.finished.connect(self._check_resumable_ai_run)

        # Start processing
        self.thread.start()

    def _set_ui_enabled(self, enabled: bool):
        """Enable or disable all UI inputs during processing."""
        self.process_button.setEnabled(enabled)
        self.ai_resume_button.setEnabled(enabled and self.ai_resume_button.isVisible())
        self.select_main_button.setEnabled(enabled)
        # Only enable clear if there is a main file loaded
        self.clear_main_button.setEnabled(enabled and self.main_data_file is not None)
        
        # XML Feeds
        self.gastromarket_checkbox.setEnabled(enabled)
        self.gastromarket_stalgast_checkbox.setEnabled(enabled)
        self.forgastro_checkbox.setEnabled(enabled)
        
        # Options
        self.ai_enhancement_checkbox.setEnabled(enabled)
        self.web_scraping_checkbox.setEnabled(enabled)
        self.mebella_scraping_checkbox.setEnabled(enabled)
        self.update_categories_checkbox.setEnabled(enabled)
        
        # We only enable these conditionally so rely on their specific state checks
        if enabled:
            # Re-check ai force enabled state
            self.force_reprocess_checkbox.setEnabled(self.ai_enhancement_checkbox.isChecked())
            # Re-check preserve edits enabled state
            self.preserve_edits_checkbox.setEnabled(self.main_data_file is not None)
        else:
            self.force_reprocess_checkbox.setEnabled(False)
            self.preserve_edits_checkbox.setEnabled(False)
            
        # Filter section
        self.category_search.setEnabled(enabled)
        self.toggle_categories_button.setEnabled(enabled)
        self.select_all_button.setEnabled(enabled)
        self.deselect_all_button.setEnabled(enabled)
        self.category_list.setEnabled(enabled)

    def update_progress(self, message: str):
        """Show the current pipeline message in the status line."""
        self.status_label.setText(message)

    def handle_statistics(self, stats: dict):
        """Render worker statistics as KPI tiles."""
        self.last_statistics = stats

        while self.kpi_grid.count():
            item = self.kpi_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tiles = [(stats.get("total_products", 0), "Produktov celkom")]
        merge = stats.get("merge")
        if merge:
            tiles += [
                (merge.get("created", 0), "Vytvorených"),
                (merge.get("updated", 0), "Aktualizovaných"),
                (merge.get("kept", 0), "Zachovaných"),
                (merge.get("removed", 0), "Odstránených"),
            ]
        ai = stats.get("ai")
        if ai:
            tiles.append((ai.get("processed", 0), "AI spracovaných"))
            if ai.get("failed"):
                tiles.append((ai["failed"], "AI zlyhaných"))
        duration = stats.get("duration")
        if duration is not None:
            minutes, seconds = divmod(int(duration), 60)
            tiles.append((f"{minutes}m {seconds}s" if minutes else f"{seconds}s", "Trvanie"))

        for i, (value, caption) in enumerate(tiles):
            self.kpi_grid.addWidget(self._kpi_tile(value, caption), i // 3, i % 3)

        self.stats_note.setText("")
        self.stats_group.setVisible(True)
        self._update_right_pane()

    def handle_result(self, pipeline_result):
        """Handle PipelineResult from worker."""
        if pipeline_result and pipeline_result.output_path:
            self._finish_stages()
            stats = self.last_statistics or {}
            message = (
                f"<b>Dáta boli úspešne exportované!</b><br><br>"
                f"<b>Súbor:</b> {pipeline_result.output_path}<br>"
                f"<b>Produktov:</b> {pipeline_result.product_count}<br>"
                f"<b>Čas spracovania:</b> {pipeline_result.duration_seconds:.1f}s"
            )
            warnings = getattr(pipeline_result, "warnings", [])
            if warnings:
                message += "<br><br><b>Upozornenia:</b><br>" + "<br>".join(warnings)
            msg_box = QMessageBox()
            msg_box.setIcon(
                QMessageBox.Warning if warnings else QMessageBox.Information
            )
            msg_box.setText(message)
            msg_box.setWindowTitle("Export úspešný")
            msg_box.setTextFormat(Qt.RichText)
            msg_box.exec_()

    def _extract_and_display_categories(self, df: pd.DataFrame):
        """Extract categories from DataFrame and display in list."""
        # Extract categories
        self.all_categories = self.category_filter.extract_categories(df)

        if not self.all_categories:
            # No categories found
            self.category_filter_group.setVisible(False)
            self._update_right_pane()
            return

        # Populate category list
        self._populate_category_list(self.all_categories)

        # Show category filter section
        self.category_filter_group.setVisible(True)
        self._update_right_pane()

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
        # Get suggestions from CategoryService (uses categories.json mappings)
        suggestions = self.category_service.suggest(original_category, top_n=5)

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

    def show_error_message(self, message: str):
        """Show error message."""
        QMessageBox.critical(self, "Chyba", message)

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

    def _update_force_reprocess(self, state):
        """Update force reprocess checkbox state."""
        self.force_reprocess_checkbox.setEnabled(state == Qt.Checked)
        if state != Qt.Checked:
            self.force_reprocess_checkbox.setChecked(False)
