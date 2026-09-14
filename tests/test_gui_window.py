"""Offscreen smoke + logic tests for the MainWindow (stage tracker, KPI tiles)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtWidgets import QApplication

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def app():
    # fixture cache keeps the QApplication referenced; a local would be GC'd
    # between tests and take the whole widget tree with it
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def window(app):
    from src.gui.theme import apply_theme
    from src.gui.main_window import MainWindow

    apply_theme(app)
    return MainWindow()


def test_stage_tracker_transitions(window):
    window._reset_stages()
    window._set_stage("merge")
    states = {key: label.property("stage") for key, label in window.stage_labels.items()}
    assert states["load"] == states["feeds"] == states["scrape"] == "done"
    assert states["merge"] == "active"
    assert states["categories"] == states["ai"] == states["export"] == "pending"

    window._finish_stages()
    assert all(label.property("stage") == "done" for label in window.stage_labels.values())


def test_kpi_tiles_render_worker_schema(window):
    """Tiles must consume the exact dict PipelineWorker emits."""
    window.handle_statistics(
        {
            "total_products": 9657,
            "merge": {"created": 10, "updated": 20, "removed": 3, "kept": 4},
            "ai": {"processed": 5, "failed": 0},
            "duration": 61.2,
        }
    )
    # products + 4 merge + ai processed + duration (failed==0 hidden)
    assert window.kpi_grid.count() == 7
    assert window.stats_group.isVisible() or not window.isVisible()  # visible once shown

    window.handle_statistics({"total_products": 1, "duration": 5})
    assert window.kpi_grid.count() == 2  # old tiles cleared, no stale rows


def test_toast_stack_and_dismiss(window):
    toast = window.toasts.show("Hotovo", "success")
    assert window.toasts._toasts == [toast]
    assert toast.property("toast") == "success"
    window.toasts._remove(toast)
    assert window.toasts._toasts == []


def test_ai_progress_switches_bar_to_determinate(window):
    window._on_ai_progress(450, 9657, "Beh 3: davka 1/20...")
    assert window.progress_bar.maximum() == 9657
    assert window.progress_bar.value() == 450
    assert "davka" in window.status_label.text()
    # any non-AI stage flips the bar back to indeterminate
    window._set_stage("export")
    assert window.progress_bar.maximum() == 0


def test_mapping_dialog_prefill_and_cancel(app):
    from PyQt5.QtWidgets import QDialog
    from src.gui.widgets import CategoryMappingDialog

    dialog = CategoryMappingDialog("Chladenie/Vitríny", suggestions=[("Chladenie/Chladničky", 88.0)])
    # input prefilled with the unmapped value, selected so typing replaces it
    assert dialog.category_input.text() == "Chladenie/Vitríny"
    assert dialog.category_input.selectedText() == "Chladenie/Vitríny"

    dialog.on_cancel_pipeline()
    assert dialog.cancel_pipeline is True
    assert dialog.result() == QDialog.Rejected


def test_mapping_dialog_force_file_and_apply_to_all(app):
    from src.gui.widgets import CategoryMappingDialog

    dialog = CategoryMappingDialog(
        "Kategória Zo Súboru",
        suggestions=[],
        product_name="Skriňa chladiaca",
        is_from_file=True,
        has_input_file=True,
    )

    assert not dialog.apply_to_all_from_file_cb.isHidden()
    assert not dialog.should_apply_to_all_from_file()

    # Check the "Apply to all from file" checkbox
    dialog.apply_to_all_from_file_cb.setChecked(True)

    # Click the "Force file name" button
    dialog.on_force_file()

    assert dialog.get_new_category() == "Kategória Zo Súboru"
    assert dialog.should_apply_to_all_from_file() is True


def test_main_window_force_file_categories_toggles(window):
    # Initially without file loaded, should be disabled and unchecked
    window.clear_main_data()
    assert not window.force_file_categories_checkbox.isEnabled()
    assert not window.force_file_categories_checkbox.isChecked()

    # Simulate loading data
    window.main_data_file = "fake.xlsx"
    window._set_ui_enabled(True)
    assert window.force_file_categories_checkbox.isEnabled()

    # Clear main data should disable and uncheck it
    window.clear_main_data()
    assert not window.force_file_categories_checkbox.isEnabled()
    assert not window.force_file_categories_checkbox.isChecked()


def test_settings_dialog_saves_config_key_and_params(app, tmp_path, monkeypatch):
    import json

    import pandas as pd

    from src.data.database.product_db import ProductDB
    from src.gui.settings_dialog import SettingsDialog

    category = "Tovary a kategórie > Chladenie"
    db_path = str(tmp_path / "products.db")
    ProductDB(db_path).upsert(
        pd.DataFrame(
            [
                {
                    "code": "P1",
                    "defaultCategory": category,
                    "filteringProperty:Príkon (W)": "2000",
                    "filteringProperty:Šírka (mm)": "800",
                    "aiProcessed": "1",
                }
            ]
        )
    )

    config = {
        "ai_enhancement": {"model": "gemini-2.5-flash-lite", "batch_size": 15},
        "xml_feeds": {"forgastro": {"url": "http://old"}},
        "db_path": db_path,
    }
    config_path = str(tmp_path / "config.json")
    params_path = str(tmp_path / "params.json")
    env_path = str(tmp_path / ".env")
    with open(params_path, "w", encoding="utf-8") as f:
        json.dump([{"kategoria": category, "filtre": ["Šírka (mm)", "Príkon (W)"]}], f)

    # monkeypatch records + restores GOOGLE_API_KEY (save_api_key sets os.environ)
    monkeypatch.setenv("GOOGLE_API_KEY", "sentinel")

    dialog = SettingsDialog(config, config_path=config_path, params_path=params_path, env_path=env_path)

    # params tab: removing a param persists the file AND clears the DB values
    dialog.select_category(category)
    assert dialog.params_tree.currentItem().text(0) == "Chladenie"  # leaf shown, not full path
    assert "Produktov v databáze: 1" in dialog.params_count_label.text()
    dialog.params_edit.setPlainText("Šírka (mm)")
    dialog._save_params()
    with open(params_path, encoding="utf-8") as f:
        assert json.load(f) == [{"kategoria": category, "filtre": ["Šírka (mm)"]}]
    df = ProductDB(db_path).get_all()
    assert df.at[0, "filteringProperty:Príkon (W)"] == ""
    assert df.at[0, "filteringProperty:Šírka (mm)"] == "800"  # kept param untouched

    # save: key -> .env, values -> config.json
    dialog.api_key_input.setText("test-key")
    dialog.batch_size_spin.setValue(33)
    dialog.feed_url_inputs["forgastro"].setText("http://new")
    dialog.save_and_close()
    with open(env_path, encoding="utf-8") as f:
        assert "GOOGLE_API_KEY=test-key" in f.read()
    with open(config_path, encoding="utf-8") as f:
        saved_config = json.load(f)
    assert saved_config["ai_enhancement"]["batch_size"] == 33
    assert saved_config["xml_feeds"]["forgastro"]["url"] == "http://new"


def test_activity_log_collects_messages(window):
    before = window.activity_log.toPlainText()
    window.update_progress("Merging product data...")
    text = window.activity_log.toPlainText()
    assert "Merging product data..." in text
    assert len(text) > len(before)
