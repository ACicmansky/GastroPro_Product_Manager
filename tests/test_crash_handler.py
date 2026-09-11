"""Unit tests for global GUI crash handler."""

import sys
from unittest.mock import MagicMock, patch

from src.gui.crash_handler import handle_exception, install_crash_handler


def test_handle_exception_logs_critical():
    """Unhandled exceptions are logged as critical with full traceback."""
    with patch("src.gui.crash_handler.logger") as mock_logger:
        with patch("src.gui.crash_handler.QApplication.instance", return_value=None):
            try:
                raise ValueError("Test crash message")
            except ValueError as e:
                exc_type, exc_val, exc_tb = sys.exc_info()
                handle_exception(exc_type, exc_val, exc_tb)

            mock_logger.critical.assert_called_once()
            log_args = mock_logger.critical.call_args[0]
            assert "Unhandled exception" in log_args[0]
            assert "Test crash message" in log_args[1]


def test_handle_exception_ignores_keyboard_interrupt():
    """KeyboardInterrupt passes to sys.__excepthook__ without logging or dialog."""
    with patch("sys.__excepthook__") as mock_orig_hook, patch("src.gui.crash_handler.logger") as mock_logger:
        exc = KeyboardInterrupt()
        handle_exception(KeyboardInterrupt, exc, None)

        mock_orig_hook.assert_called_once_with(KeyboardInterrupt, exc, None)
        mock_logger.critical.assert_not_called()


def test_handle_exception_shows_dialog_when_app_present():
    """When QApplication is active, a critical QMessageBox is displayed."""
    mock_app = MagicMock()
    with patch("src.gui.crash_handler.QApplication.instance", return_value=mock_app):
        with patch("src.gui.crash_handler.QMessageBox") as mock_msg_box_cls, patch("src.gui.crash_handler.logger"):
            mock_box_instance = MagicMock()
            mock_msg_box_cls.return_value = mock_box_instance

            try:
                raise RuntimeError("GUI explosion")
            except RuntimeError as e:
                exc_type, exc_val, exc_tb = sys.exc_info()
                handle_exception(exc_type, exc_val, exc_tb)

            mock_msg_box_cls.assert_called_once()
            mock_box_instance.setWindowTitle.assert_called_once_with("Chyba aplikácie")
            mock_box_instance.exec_.assert_called_once()


def test_install_crash_handler():
    """install_crash_handler hooks sys.excepthook."""
    orig = sys.excepthook
    try:
        install_crash_handler()
        assert sys.excepthook == handle_exception
    finally:
        sys.excepthook = orig
