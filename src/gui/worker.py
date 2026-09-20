"""Thin pipeline worker — bridges pipeline use cases and driven ports to Qt signals."""

import logging
from typing import Dict, Optional

from PyQt5.QtCore import QEventLoop, QObject, pyqtSignal

from src.ai.run_control import RunControl
from src.domain.models import PipelineOptions
from src.pipeline.pipeline import Pipeline

logger = logging.getLogger(__name__)


class PipelineCancelled(Exception):
    """User aborted the run from an interactive dialog."""


class QtSignalEventSink:
    """Adapts Qt signals to EventSinkPort (driving adapter)."""

    def __init__(
        self,
        progress_sig=None,
        stage_sig=None,
        ai_progress_sig=None,
    ):
        self._progress = progress_sig
        self._stage = stage_sig
        self._ai_progress = ai_progress_sig

    def emit_progress(self, message: str) -> None:
        if self._progress:
            self._progress.emit(message)
        logger.info(message)

    def emit_stage(self, stage_key: str) -> None:
        if self._stage:
            self._stage.emit(stage_key)

    def emit_ai_progress(self, current: int, total: int, message: str) -> None:
        if self._ai_progress:
            self._ai_progress.emit(int(current), int(total), str(message))
        elif self._progress:
            self._progress.emit(message)


class QtDialogResolver:
    """Adapts worker Qt event loops to UserResolutionPort (driving adapter)."""

    def __init__(self, worker: "PipelineWorker"):
        self._worker = worker

    def resolve_category(self, original_category: str, product_name: str = "") -> str:
        return self._worker._on_unknown_category(original_category, product_name)

    def resolve_price(self, product_data: dict, prices_df) -> Optional[str]:
        return self._worker._on_unmapped_price(product_data, prices_df)


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
        self._cancelled = False
        self._price_result: Optional[str] = None
        self._price_loop: Optional[QEventLoop] = None

    def run(self):
        """Execute the pipeline via driving ports. Called from QThread."""
        try:
            event_sink = QtSignalEventSink(
                progress_sig=self.progress,
                stage_sig=self.stage,
                ai_progress_sig=self.ai_progress,
            )
            resolver = QtDialogResolver(self)

            pipeline_result = self.pipeline.run(
                self.options,
                event_sink=event_sink,
                user_resolution=resolver,
                ai_control=self.ai_control,
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
        except PipelineCancelled:
            logger.info("Pipeline cancelled by user from mapping dialog")
            self.error.emit("Spracovanie zrušené používateľom.")
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            db_path = self.config.get("db_path", "data/products.db") if self.config else "data/products.db"
            try:
                from src.data.database.run_db import RunDB

                run_db = RunDB(db_path)
                active = run_db.get_resumable_run()
                if active and active.get("status") == "running":
                    run_db.update_run(active["id"], status="interrupted", detail=str(e)[:150])
            except Exception:
                pass
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def _on_unknown_category(self, original_category: str, product_name: Optional[str] = None) -> str:
        """Block and ask GUI for category mapping."""
        self._category_result = None
        self._category_loop = QEventLoop()
        self.category_mapping_request.emit(original_category, product_name or "")
        self._category_loop.exec_()
        if self._cancelled:
            raise PipelineCancelled()
        return self._category_result or original_category

    def set_category_mapping_result(self, new_category: str):
        """Called by GUI when user provides category mapping."""
        self._category_result = new_category
        if self._category_loop:
            self._category_loop.quit()

    def cancel_pipeline(self):
        """Called by GUI when user aborts the whole run from the mapping dialog."""
        self._cancelled = True
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
    """AI-only run — no feeds/merge/file load, just DB in -> DB out."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    ai_progress = pyqtSignal(int, int, str)  # current, total, message
    result = pyqtSignal(object)  # PipelineResult

    def __init__(
        self,
        config: Dict,
        ai_control: Optional[RunControl] = None,
        categories: Optional[list] = None,
    ):
        super().__init__()
        self.pipeline = Pipeline(config)
        self.ai_control = ai_control or RunControl()
        self.categories = categories

    def run(self):
        """Called from QThread."""
        event_sink = QtSignalEventSink(
            progress_sig=self.progress,
            ai_progress_sig=self.ai_progress,
        )
        try:
            if self.categories:
                pipeline_result = self.pipeline.run_ai_for_categories(
                    self.categories,
                    event_sink=event_sink,
                    ai_control=self.ai_control,
                )
            else:
                pipeline_result = self.pipeline.run_ai_resume(
                    event_sink=event_sink,
                    ai_control=self.ai_control,
                )
            self.result.emit(pipeline_result)
        except Exception as e:
            logger.error(f"AI resume error: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class DBExportWorker(QObject):
    """Exports products from SQLite database directly to Excel file in a background thread."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    result = pyqtSignal(object)  # PipelineResult
    statistics = pyqtSignal(dict)

    def __init__(
        self,
        config: Dict,
        output_path: str,
        selected_categories: Optional[list] = None,
    ):
        super().__init__()
        self.pipeline = Pipeline(config)
        self.output_path = output_path
        self.selected_categories = selected_categories

    def run(self):
        """Called from QThread."""
        event_sink = QtSignalEventSink(progress_sig=self.progress)
        try:
            pipeline_result = self.pipeline.export_from_db(
                output_path=self.output_path,
                selected_categories=self.selected_categories,
                event_sink=event_sink,
            )
            self.statistics.emit(
                {
                    "total_products": pipeline_result.product_count,
                    "duration": pipeline_result.duration_seconds,
                }
            )
            self.result.emit(pipeline_result)
        except Exception as e:
            logger.error(f"DB export error: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            self.finished.emit()
