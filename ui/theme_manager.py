"""
Theme manager for handling application styling
"""
from PyQt5.QtCore import QObject, pyqtSignal

class ThemeManager(QObject):
    """
    Manages application theme and styling
    """
    themeChanged = pyqtSignal(bool)  # Signal emitted when theme changes (bool: isDarkMode)
    
    def __init__(self):
        super().__init__()
        self.dark_mode = False
        self.stylesheet_path = 'styles/main.qss'
    
    def toggle_dark_mode(self):
        """Toggle between light and dark modes"""
        self.dark_mode = not self.dark_mode
        self.themeChanged.emit(self.dark_mode)
        return self.dark_mode
    
    def is_dark_mode(self):
        """Check if dark mode is active"""
        return self.dark_mode
    
    def load_stylesheet(self):
        """Load and return the current stylesheet"""
        try:
            with open(self.stylesheet_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Stylesheet not found at {self.stylesheet_path}")
            return ""
