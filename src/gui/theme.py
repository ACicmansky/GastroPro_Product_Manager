"""Application theme: Fusion base + token-substituted QSS, follows Windows light/dark."""

from pathlib import Path
from string import Template

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QColor, QFont, QPalette

_STYLES_DIR = Path(__file__).resolve().parents[2] / "styles"

LIGHT = {
    "bg": "#f3f4f6",
    "surface": "#ffffff",
    "surfaceAlt": "#f9fafb",
    "border": "#e5e7eb",
    "text": "#111827",
    "muted": "#6b7280",
    "accent": "#2563eb",
    "accentHover": "#1d4ed8",
    "accentPressed": "#1e40af",
    "accentSubtle": "#e8effd",
    "success": "#15803d",
    "warning": "#b45309",
    "danger": "#dc2626",
}

DARK = {
    "bg": "#111318",
    "surface": "#1a1d23",
    "surfaceAlt": "#22262e",
    "border": "#2e333d",
    "text": "#e5e7eb",
    "muted": "#9ca3af",
    "accent": "#3b82f6",
    "accentHover": "#5a97f5",
    "accentPressed": "#2563eb",
    "accentSubtle": "#1d2a45",
    "success": "#4ade80",
    "warning": "#fbbf24",
    "danger": "#f87171",
}


def _settings() -> QSettings:
    return QSettings("GastroPro", "ProductManager")


def current_theme_mode() -> str:
    """Persisted preference: 'auto' (follow Windows), 'light' or 'dark'."""
    mode = _settings().value("theme", "auto")
    return mode if mode in ("auto", "light", "dark") else "auto"


def save_theme_mode(mode: str) -> None:
    _settings().setValue("theme", mode)


def windows_dark_mode() -> bool:
    """True if Windows apps theme is dark. Safe on any platform."""
    try:
        import winreg

        key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False


def _palette(tokens: dict) -> QPalette:
    """Minimal QPalette so native-drawn bits (menus, message boxes) match the QSS."""
    p = QPalette()
    roles = {
        QPalette.Window: tokens["bg"],
        QPalette.WindowText: tokens["text"],
        QPalette.Base: tokens["surface"],
        QPalette.AlternateBase: tokens["surfaceAlt"],
        QPalette.Text: tokens["text"],
        QPalette.Button: tokens["surface"],
        QPalette.ButtonText: tokens["text"],
        QPalette.Highlight: tokens["accent"],
        QPalette.HighlightedText: "#ffffff",
        QPalette.ToolTipBase: tokens["surface"],
        QPalette.ToolTipText: tokens["text"],
        QPalette.PlaceholderText: tokens["muted"],
    }
    for role, color in roles.items():
        p.setColor(role, QColor(color))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(tokens["muted"]))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(tokens["muted"]))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor(tokens["muted"]))
    return p


def apply_theme(app) -> None:
    """Fusion style + palette + stylesheet on the whole application (dialogs inherit).

    Respects the persisted theme preference; 'auto' follows the Windows app theme.
    Safe to call again at runtime to re-theme live.
    """
    mode = current_theme_mode()
    dark = windows_dark_mode() if mode == "auto" else mode == "dark"
    tokens = dict(DARK if dark else LIGHT)
    tokens["check"] = (_STYLES_DIR / "check.svg").as_posix()

    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setPalette(_palette(tokens))

    qss_path = _STYLES_DIR / "main.qss"
    if qss_path.exists():
        app.setStyleSheet(Template(qss_path.read_text(encoding="utf-8")).substitute(tokens))


def set_variant(widget, variant: str) -> None:
    """Switch a QSS [variant=...] state at runtime (e.g. hint/success/warning label)."""
    widget.setProperty("variant", variant)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
