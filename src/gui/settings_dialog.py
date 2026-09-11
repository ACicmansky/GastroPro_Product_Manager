"""Settings dialog: API key, AI tuning, feed URLs, category AI parameters."""

import json
import logging
import os
from typing import Dict, Optional

import pandas as pd
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ai.batch_orchestrator import BatchOrchestrator
from src.config.config_loader import read_api_key, save_api_key, save_config
from src.data.database.product_db import ProductDB

logger = logging.getLogger(__name__)

KNOWN_MODELS = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]

TARGET_PREFIX = "Tovary a kategórie > "


def _short_path(category: str) -> str:
    """Category path without the shared root prefix (pure noise on screen)."""
    return category[len(TARGET_PREFIX):] if category.startswith(TARGET_PREFIX) else category


class SettingsDialog(QDialog):
    """Per-user settings: Gemini key (.env), AI values + feed URLs (config.json),
    and per-category AI filter parameters (categories_with_parameters.json)."""

    run_ai_for_categories = pyqtSignal(list)  # category names to re-process

    def __init__(
        self,
        config: Dict,
        parent=None,
        config_path: str = "config.json",
        params_path: str = "categories_with_parameters.json",
        env_path: str = ".env",
    ):
        super().__init__(parent)
        self.setWindowTitle("Nastavenia")
        # resizable dialog with min/maximize buttons (Windows dialogs hide them by default)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowMinimizeButtonHint
        )
        self.setSizeGripEnabled(True)
        self.resize(980, 640)
        self.config = config
        self.config_path = config_path
        self.params_path = params_path
        self.env_path = env_path
        self._db_cache: Optional[pd.DataFrame] = None
        self.params = self._load_params()

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_api_tab(), "🔑 API kľúč")
        self.tabs.addTab(self._build_ai_tab(), "⚙️ AI nastavenia")
        self.tabs.addTab(self._build_params_tab(), "🧩 Parametre kategórií")
        layout.addWidget(self.tabs)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close_button = QPushButton("Zavrieť")
        close_button.clicked.connect(self.reject)
        buttons.addWidget(close_button)
        save_button = QPushButton("💾 Uložiť nastavenia")
        save_button.setProperty("primary", True)
        save_button.setDefault(True)
        save_button.clicked.connect(self.save_and_close)
        buttons.addWidget(save_button)
        layout.addLayout(buttons)

    # ------------------------------------------------------------------
    # Tab 1: API key
    # ------------------------------------------------------------------

    def _build_api_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        hint = QLabel(
            "Google Gemini API kľúč sa ukladá do súboru .env na tomto počítači "
            "(nie do zdieľanej konfigurácie). Kľúč získate na aistudio.google.com."
        )
        hint.setWordWrap(True)
        hint.setProperty("variant", "hint")
        layout.addWidget(hint)

        row = QHBoxLayout()
        self.api_key_input = QLineEdit(read_api_key(self.env_path))
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("AIza...")
        row.addWidget(self.api_key_input, 1)

        show_button = QPushButton("👁")
        show_button.setCheckable(True)
        show_button.setProperty("flat", "true")
        show_button.setToolTip("Zobraziť/skryť kľúč")
        show_button.toggled.connect(
            lambda checked: self.api_key_input.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        row.addWidget(show_button)
        layout.addLayout(row)

        test_button = QPushButton("🔌 Otestovať kľúč")
        test_button.clicked.connect(self._test_api_key)
        layout.addWidget(test_button, alignment=Qt.AlignLeft)

        self.api_test_result = QLabel("")
        self.api_test_result.setWordWrap(True)
        layout.addWidget(self.api_test_result)
        layout.addStretch()
        return tab

    def _test_api_key(self):
        key = self.api_key_input.text().strip()
        if not key:
            self._set_test_result("Zadajte kľúč.", ok=False)
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            from google import genai

            client = genai.Client(api_key=key)
            next(iter(client.models.list()), None)  # cheapest authenticated call
            self._set_test_result("✅ Kľúč je platný.", ok=True)
        except Exception as e:
            self._set_test_result(f"❌ Kľúč nefunguje: {e}", ok=False)
        finally:
            QApplication.restoreOverrideCursor()

    def _set_test_result(self, text: str, ok: bool):
        self.api_test_result.setText(text)
        self.api_test_result.setProperty("variant", "success" if ok else "warning")
        self.api_test_result.style().unpolish(self.api_test_result)
        self.api_test_result.style().polish(self.api_test_result)

    # ------------------------------------------------------------------
    # Tab 2: AI values + feed URLs (config.json)
    # ------------------------------------------------------------------

    def _build_ai_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = QFormLayout()
        ai = self.config.get("ai_enhancement", {})

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(KNOWN_MODELS)
        self.model_combo.setCurrentText(ai.get("model", KNOWN_MODELS[0]))
        form.addRow("Model:", self.model_combo)

        def spin(minimum, maximum, value, suffix=""):
            box = QSpinBox()
            box.setRange(minimum, maximum)
            box.setValue(value)
            if suffix:
                box.setSuffix(suffix)
            return box

        self.batch_size_spin = spin(1, 100, ai.get("batch_size", 45))
        form.addRow("Produktov v dávke:", self.batch_size_spin)
        self.retry_attempts_spin = spin(0, 10, ai.get("retry_attempts", 3))
        form.addRow("Počet opakovaní:", self.retry_attempts_spin)
        self.retry_delay_spin = spin(5, 600, ai.get("retry_delay", 60), " s")
        form.addRow("Pauza pred opakovaním:", self.retry_delay_spin)
        self.parallel_spin = spin(1, 50, ai.get("max_parallel_calls", 10))
        form.addRow("Paralelné volania:", self.parallel_spin)
        layout.addLayout(form)

        feeds_label = QLabel("Adresy XML feedov")
        feeds_label.setProperty("variant", "hint")
        layout.addWidget(feeds_label)
        feeds_form = QFormLayout()
        self.feed_url_inputs = {}
        for name, feed in self.config.get("xml_feeds", {}).items():
            edit = QLineEdit(feed.get("url", ""))
            self.feed_url_inputs[name] = edit
            feeds_form.addRow(f"{name}:", edit)
        layout.addLayout(feeds_form)
        layout.addStretch()
        return tab

    # ------------------------------------------------------------------
    # Tab 3: category AI parameters
    # ------------------------------------------------------------------

    def _build_params_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)

        left = QVBoxLayout()
        self.params_search = QLineEdit()
        self.params_search.setPlaceholderText("🔍 Hľadať kategóriu...")
        self.params_search.textChanged.connect(self._filter_params_list)
        left.addWidget(self.params_search)

        self.params_tree = QTreeWidget()
        self.params_tree.setHeaderHidden(True)
        self.params_tree.currentItemChanged.connect(self._on_tree_selection)
        self._populate_tree()
        left.addWidget(self.params_tree, 1)

        add_row = QHBoxLayout()
        self.new_category_input = QLineEdit()
        self.new_category_input.setPlaceholderText("Nová kategória (celý názov)...")
        add_row.addWidget(self.new_category_input, 1)
        add_button = QPushButton("➕")
        add_button.setToolTip("Pridať kategóriu do zoznamu parametrov")
        add_button.clicked.connect(self._add_category)
        add_row.addWidget(add_button)
        left.addLayout(add_row)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        self.params_cat_label = QLabel("Vyberte kategóriu vľavo.")
        self.params_cat_label.setWordWrap(True)
        right.addWidget(self.params_cat_label)

        self.params_edit = QPlainTextEdit()
        self.params_edit.setPlaceholderText(
            "Jeden parameter na riadok, napr.:\nŠírka (mm)\nPríkon (W)"
        )
        self.params_edit.setEnabled(False)
        right.addWidget(self.params_edit, 1)

        self.params_count_label = QLabel("")
        self.params_count_label.setProperty("variant", "hint")
        right.addWidget(self.params_count_label)

        actions = QHBoxLayout()
        self.save_params_button = QPushButton("💾 Uložiť parametre")
        self.save_params_button.setEnabled(False)
        self.save_params_button.clicked.connect(self._save_params)
        actions.addWidget(self.save_params_button)
        self.run_ai_button = QPushButton("🤖 Spustiť AI pre kategóriu")
        self.run_ai_button.setProperty("primary", True)
        self.run_ai_button.setEnabled(False)
        self.run_ai_button.clicked.connect(self._trigger_category_run)
        actions.addWidget(self.run_ai_button)
        right.addLayout(actions)
        layout.addLayout(right, 2)
        return tab

    def _load_params(self) -> Dict[str, list]:
        if not os.path.exists(self.params_path):
            return {}
        try:
            with open(self.params_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                item["kategoria"]: list(item["filtre"])
                for item in data
                if isinstance(item, dict) and "kategoria" in item and "filtre" in item
            }
        except Exception as e:
            logger.warning(f"Failed to load category parameters: {e}")
            return {}

    def _save_params_file(self):
        data = [{"kategoria": k, "filtre": v} for k, v in self.params.items()]
        with open(self.params_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _populate_tree(self):
        """Leaf names grouped under their parent path — full paths only on demand
        (tooltip + breadcrumb header), not as a wall of 100-char rows."""
        self.params_tree.clear()
        groups = {}
        for category in sorted(self.params):
            parts = _short_path(category).split(" > ")
            group_name = " > ".join(parts[:-1]) or "(bez skupiny)"
            group = groups.get(group_name)
            if group is None:
                group = QTreeWidgetItem([group_name])
                group.setFlags(group.flags() & ~Qt.ItemIsSelectable)
                groups[group_name] = group
                self.params_tree.addTopLevelItem(group)
            item = QTreeWidgetItem([parts[-1]])
            item.setData(0, Qt.UserRole, category)
            item.setToolTip(0, category)
            group.addChild(item)
        self.params_tree.expandAll()

    def select_category(self, category: str):
        for i in range(self.params_tree.topLevelItemCount()):
            group = self.params_tree.topLevelItem(i)
            for j in range(group.childCount()):
                child = group.child(j)
                if child.data(0, Qt.UserRole) == category:
                    self.params_tree.setCurrentItem(child)
                    return

    def _current_category(self) -> str:
        item = self.params_tree.currentItem()
        return (item.data(0, Qt.UserRole) or "") if item else ""

    def _on_tree_selection(self, current, _previous=None):
        category = current.data(0, Qt.UserRole) if current else None
        if category:
            self._show_params_for(category)

    def _filter_params_list(self, text: str):
        text = text.lower()
        for i in range(self.params_tree.topLevelItemCount()):
            group = self.params_tree.topLevelItem(i)
            visible = 0
            for j in range(group.childCount()):
                child = group.child(j)
                hit = text in child.data(0, Qt.UserRole).lower()
                child.setHidden(not hit)
                visible += hit
            group.setHidden(visible == 0)

    def _show_params_for(self, category: str):
        if not category:
            return
        parts = _short_path(category).split(" > ")
        breadcrumb = " › ".join(parts[:-1])
        self.params_cat_label.setText(
            f"<span style='font-size:8pt; opacity:0.7;'>{breadcrumb}</span><br>"
            f"<b>{parts[-1]}</b>"
        )
        self.params_cat_label.setToolTip(category)
        self.params_edit.setPlainText("\n".join(self.params.get(category, [])))
        self.params_edit.setEnabled(True)
        self.save_params_button.setEnabled(True)
        self.run_ai_button.setEnabled(True)
        count = self._product_count(category)
        self.params_count_label.setText(f"Produktov v databáze: {count}")

    def _add_category(self):
        name = self.new_category_input.text().strip()
        if not name:
            return
        if name not in self.params:
            self.params[name] = []
            self._populate_tree()
        self.select_category(name)
        self.new_category_input.clear()

    # ------------------------------------------------------------------
    # DB helpers (product counts + clearing removed params)
    # ------------------------------------------------------------------

    def _db(self) -> ProductDB:
        return ProductDB(self.config.get("db_path", "data/products.db"))

    def _db_df(self) -> pd.DataFrame:
        if self._db_cache is None:
            try:
                self._db_cache = self._db().get_all()
            except Exception as e:
                logger.warning(f"Could not read product DB: {e}")
                self._db_cache = pd.DataFrame()
        return self._db_cache

    def _category_mask(self, category: str) -> pd.Series:
        df = self._db_df()
        if df.empty:
            return pd.Series(dtype=bool)
        return df.apply(BatchOrchestrator._category_of, axis=1) == category

    def _product_count(self, category: str) -> int:
        mask = self._category_mask(category)
        return int(mask.sum()) if not mask.empty else 0

    def _clear_removed_params(self, category: str, removed: list) -> int:
        """Blank filteringProperty columns of removed params for this category's products."""
        df = self._db_df()
        mask = self._category_mask(category)
        cols = [
            f"filteringProperty:{p}" for p in removed
            if f"filteringProperty:{p}" in df.columns
        ]
        if df.empty or not cols or not mask.any():
            return 0
        df.loc[mask, cols] = ""
        self._db().upsert(df.loc[mask])
        return int(mask.sum())

    def _save_params(self):
        category = self._current_category()
        if not category:
            return
        new_params = [
            line.strip() for line in self.params_edit.toPlainText().splitlines()
            if line.strip()
        ]
        removed = [p for p in self.params.get(category, []) if p not in new_params]
        self.params[category] = new_params
        self._save_params_file()

        cleared = self._clear_removed_params(category, removed) if removed else 0
        message = "Parametre uložené."
        if removed:
            message += f" Odstránené hodnoty ({', '.join(removed)}) vymazané z {cleared} produktov."
        self.params_count_label.setText(message)

    def _trigger_category_run(self):
        category = self._current_category()
        if not category:
            return
        count = self._product_count(category)
        if count == 0:
            QMessageBox.information(
                self, "Žiadne produkty",
                "V databáze nie sú žiadne produkty tejto kategórie.",
            )
            return
        confirm = QMessageBox.question(
            self, "Spustiť AI spracovanie",
            f"Znova spracovať {count} produktov kategórie:\n\n{category}\n\n"
            "Použije sa API kvóta (platené volania). Pokračovať?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        self._save_params()  # run with what's on screen, not a stale file
        self.run_ai_for_categories.emit([category])
        self.accept()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save_and_close(self):
        key = self.api_key_input.text().strip()
        if key:
            save_api_key(key, self.env_path)

        ai = self.config.setdefault("ai_enhancement", {})
        ai["model"] = self.model_combo.currentText().strip()
        ai["batch_size"] = self.batch_size_spin.value()
        ai["retry_attempts"] = self.retry_attempts_spin.value()
        ai["retry_delay"] = self.retry_delay_spin.value()
        ai["max_parallel_calls"] = self.parallel_spin.value()
        for name, edit in self.feed_url_inputs.items():
            url = edit.text().strip()
            if url:
                self.config["xml_feeds"][name]["url"] = url
        save_config(self.config, self.config_path)
        self.accept()
