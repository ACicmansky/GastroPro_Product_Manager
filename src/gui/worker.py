"""Thin pipeline worker — bridges pipeline callbacks to Qt signals."""

import logging
from typing import Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal, QEventLoop

from src.pipeline.pipeline import Pipeline
from src.domain.models import PipelineOptions, PipelineResult

logger = logging.getLogger(__name__)


class PipelineWorker(QObject):
    """Executes pipeline in a background thread, emitting Qt signals for UI updates."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    result = pyqtSignal(object)  # PipelineResult
    statistics = pyqtSignal(dict)
    category_mapping_request = pyqtSignal(str, str)  # original_category, product_name
    price_mapping_request = pyqtSignal(list)  # unmapped codes

    def __init__(self, config: Dict, options: PipelineOptions):
        super().__init__()
        self.config = config
        self.options = options
        self.pipeline = Pipeline(config)

        # For blocking on GUI interactions
        self._category_result: Optional[str] = None
        self._category_loop: Optional[QEventLoop] = None
        self._price_result: Optional[str] = None
        self._price_loop: Optional[QEventLoop] = None

    def run(self):
        """Execute the pipeline. Called from QThread."""
        try:
            pipeline_result = self.pipeline.run(
                self.options,
                on_progress=self._on_progress,
                on_unknown_category=self._on_unknown_category,
                on_unmapped_price=self._on_unmapped_price,
            )

            # Emit statistics
            stats = {}
            if pipeline_result.merge_stats:
                stats["merge"] = {
                    "created": pipeline_result.merge_stats.created,
                    "updated": pipeline_result.merge_stats.updated,
                    "removed": pipeline_result.merge_stats.removed,
                    "kept": pipeline_result.merge_stats.kept,
                }
            if pipeline_result.enrichment_stats:
                stats["ai"] = {
                    "processed": pipeline_result.enrichment_stats.processed,
                    "failed": pipeline_result.enrichment_stats.failed,
                }
            stats["total_products"] = pipeline_result.product_count
            stats["duration"] = pipeline_result.duration_seconds
            self.statistics.emit(stats)

            self.result.emit(pipeline_result)
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def _on_progress(self, message: str):
        self.progress.emit(message)

    def _on_unknown_category(self, original_category: str, product_name: Optional[str] = None) -> str:
        """Block and ask GUI for category mapping."""
        self._category_result = None
        self._category_loop = QEventLoop()
        self.category_mapping_request.emit(original_category, product_name or "")
        self._category_loop.exec_()
        return self._category_result or original_category

    def set_category_mapping_result(self, new_category: str):
        """Called by GUI when user provides category mapping."""
        self._category_result = new_category
        if self._category_loop:
            self._category_loop.quit()

    def _on_unmapped_price(self, unmapped_codes: list):
        """Notify GUI about unmapped prices."""
        self.price_mapping_request.emit(unmapped_codes)

    def set_price_mapping_result(self, price: str):
        """Called by GUI when user provides price mapping."""
        self._price_result = price
        if self._price_loop:
            self._price_loop.quit()
