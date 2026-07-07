"""Thin pipeline worker — bridges pipeline callbacks to Qt signals."""

import logging
from typing import Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal, QEventLoop

from src.pipeline.pipeline import Pipeline
from src.domain.models import PipelineOptions, PipelineResult
from src.ai.run_control import RunControl

logger = logging.getLogger(__name__)


class PipelineWorker(QObject):
    """Executes pipeline in a background thread, emitting Qt signals for UI updates."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    stage = pyqtSignal(str)  # pipeline stage key (load/feeds/scrape/merge/categories/ai/export)
    ai_progress = pyqtSignal(int, int, str)  # current, total, message
    result = pyqtSignal(object)  # PipelineResult
    statistics = pyqtSignal(dict)
    category_mapping_request = pyqtSignal(str, str)  # original_category, product_name
    price_mapping_request = pyqtSignal(dict, object)  # product_data, prices_df

    def __init__(self, config: Dict, options: PipelineOptions, ai_control: Optional[RunControl] = None):
        super().__init__()
        self.config = config
        self.options = options
        self.pipeline = Pipeline(config)
        self.ai_control = ai_control or RunControl()

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
                ai_control=self.ai_control,
                on_stage=self.stage.emit,
                on_ai_progress=lambda current, total, message: self.ai_progress.emit(
                    int(current), int(total), str(message)
                ),
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

    def _on_unmapped_price(self, product_data: dict, prices_df) -> Optional[str]:
        """Block and ask GUI for a price for one product."""
        self._price_result = None
        self._price_loop = QEventLoop()
        self.price_mapping_request.emit(product_data, prices_df)
        self._price_loop.exec_()
        return self._price_result

    def set_price_mapping_result(self, price: Optional[str]):
        """Called by GUI when user provides price mapping."""
        self._price_result = price
        if self._price_loop:
            self._price_loop.quit()


class AIResumeWorker(QObject):
    """Continues an interrupted AI run — no feeds/merge/file load, just DB in -> DB out."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    ai_progress = pyqtSignal(int, int, str)  # current, total, message
    result = pyqtSignal(object)  # PipelineResult

    def __init__(self, config: Dict, ai_control: Optional[RunControl] = None):
        super().__init__()
        self.pipeline = Pipeline(config)
        self.ai_control = ai_control or RunControl()

    def run(self):
        """Called from QThread."""
        try:
            pipeline_result = self.pipeline.run_ai_resume(
                on_progress=lambda msg: self.progress.emit(msg),
                ai_control=self.ai_control,
                on_ai_progress=lambda current, total, message: self.ai_progress.emit(
                    int(current), int(total), str(message)
                ),
            )
            self.result.emit(pipeline_result)
        except Exception as e:
            logger.error(f"AI resume error: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            self.finished.emit()
