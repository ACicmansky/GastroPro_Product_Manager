# src/gui/worker.py
from PyQt5.QtCore import QObject, pyqtSignal
from ..core.data_pipeline import DataPipeline

class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    progress = pyqtSignal(str)
    result = pyqtSignal(object)

    def __init__(self, main_df, selected_categories, config, options):
        super().__init__()
        self.main_df = main_df
        self.selected_categories = selected_categories
        self.config = config
        self.options = options

    def run(self):
        try:
            pipeline = DataPipeline(self.config, progress_callback=self.progress.emit)
            pipeline_result = pipeline.run(self.main_df, self.selected_categories, self.options)
            self.result.emit(pipeline_result)
        except Exception as e:
            self.error.emit(("Chyba spracovania", f"Počas spracovania dát došlo k chybe:\n{e}"))
        finally:
            self.finished.emit()
