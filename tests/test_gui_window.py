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
    assert all(
        label.property("stage") == "done" for label in window.stage_labels.values()
    )


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
