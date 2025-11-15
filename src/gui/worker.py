# src/gui/worker.py
from PyQt5.QtCore import QObject, pyqtSignal, QEventLoop
from ..core.data_pipeline import DataPipeline


class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    progress = pyqtSignal(str)
    result = pyqtSignal(object)
    request_category_mapping = pyqtSignal(
        str
    )  # Signal to request category mapping from UI

    def __init__(self, main_df, selected_categories, config, options):
        super().__init__()
        self.main_df = main_df
        self.selected_categories = selected_categories
        self.config = config
        self.options = options
        self.category_mapping_result = None
        self.category_mapping_loop = None
        self.current_original_category = None  # Track current category being mapped
        self.current_product_name = None  # Track product name for context

    def run(self):
        try:
            self.pipeline = DataPipeline(
                self.config,
                progress_callback=self.progress.emit,
                category_mapping_callback=self.request_category_mapping_sync,
            )
            pipeline_result = self.pipeline.run(
                self.main_df, self.selected_categories, self.options
            )
            self.result.emit(pipeline_result)
        except Exception as e:
            self.error.emit(
                ("Chyba spracovania", f"Počas spracovania dát došlo k chybe:\n{e}")
            )
        finally:
            self.finished.emit()

    def request_category_mapping_sync(self, original_category, product_name=None):
        """Request category mapping from UI thread and wait for response."""
        self.category_mapping_result = None
        self.current_original_category = original_category
        self.current_product_name = product_name
        self.category_mapping_loop = QEventLoop()

        # Emit signal to UI thread
        self.request_category_mapping.emit(original_category)

        # Wait for response
        self.category_mapping_loop.exec_()

        return self.category_mapping_result

    def set_category_mapping_result(self, new_category):
        """Called by UI thread to provide the result."""
        self.category_mapping_result = new_category
        if self.category_mapping_loop:
            self.category_mapping_loop.quit()
