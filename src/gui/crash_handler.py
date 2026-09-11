"""Global uncaught exception handler for GastroPro PyQt5 GUI."""

import logging
import sys
import traceback
from types import TracebackType
from typing import Type

from PyQt5.QtWidgets import QApplication, QMessageBox

logger = logging.getLogger("gastropro")


def handle_exception(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType,
) -> None:
    """Global exception hook: logs unhandled exceptions and displays a user dialog."""
    # Allow KeyboardInterrupt to exit cleanly
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical("Unhandled exception:\n%s", tb_text)

    # Show Qt message box if GUI is running
    app = QApplication.instance()
    if app is not None:
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Chyba aplikácie")
            msg_box.setText(f"Vyskytla sa neočakávaná chyba:\n\n{exc_type.__name__}: {exc_value}")
            msg_box.setDetailedText(tb_text)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
        except Exception as dialog_err:
            logger.error("Failed to display crash dialog: %s", dialog_err)


def install_crash_handler() -> None:
    """Install global sys.excepthook handler."""
    sys.excepthook = handle_exception
