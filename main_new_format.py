"""
Main entry point for GastroPro Product Manager - New 147-Column Format.
This is the GUI application for manual testing of the new format pipeline.
"""

import sys
from PyQt5.QtWidgets import QApplication
from src.gui.main_window_new_format import MainWindowNewFormat


def main():
    """Run the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("GASTROPRO Product Manager - New Format")
    
    window = MainWindowNewFormat()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
