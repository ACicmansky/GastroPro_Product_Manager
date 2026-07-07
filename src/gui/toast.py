"""Non-blocking toast notifications, stacked bottom-right inside a parent window."""

from PyQt5.QtCore import QEvent, QObject, QPropertyAnimation, Qt, QTimer
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

# 0 = sticky until clicked
DURATIONS = {"info": 4500, "success": 6000, "warning": 9000, "error": 0}
ICONS = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "⛔"}


class Toast(QFrame):
    """One notification card. Click anywhere to dismiss; optional action button."""

    def __init__(self, host, message, variant, action=None, duration=None):
        super().__init__(host.parent_widget)
        self.host = host
        self._closing = False
        self.setProperty("toast", variant)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)
        row.addWidget(QLabel(ICONS.get(variant, "")))
        label = QLabel(message)
        label.setWordWrap(True)
        row.addWidget(label, 1)
        if action:
            text, callback = action
            button = QPushButton(text)
            button.setProperty("toastAction", True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(callback)
            button.clicked.connect(self.dismiss)
            row.addWidget(button)

        self.setFixedWidth(360)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(180)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

        ms = DURATIONS.get(variant, 4500) if duration is None else duration
        if ms:
            QTimer.singleShot(ms, self.dismiss)
        self.show()

    def mousePressEvent(self, event):
        self.dismiss()

    def dismiss(self):
        if self._closing:
            return
        self._closing = True
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(220)
        self._anim.setStartValue(self._effect.opacity())
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(lambda: self.host._remove(self))
        self._anim.start()


class ToastHost(QObject):
    """Owns and stacks toasts bottom-right of a window; restacks on resize."""

    MARGIN = 16
    SPACING = 8

    def __init__(self, parent_widget):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self._toasts = []
        parent_widget.installEventFilter(self)

    def show(self, message, variant="info", action=None, duration=None):
        toast = Toast(self, message, variant, action, duration)
        self._toasts.append(toast)
        self._restack()
        return toast

    def _remove(self, toast):
        if toast in self._toasts:
            self._toasts.remove(toast)
        toast.deleteLater()
        self._restack()

    def _restack(self):
        y = self.parent_widget.height() - self.MARGIN
        for toast in reversed(self._toasts):  # newest closest to the corner
            toast.adjustSize()
            y -= toast.height()
            toast.move(self.parent_widget.width() - toast.width() - self.MARGIN, y)
            toast.raise_()
            y -= self.SPACING

    def eventFilter(self, obj, event):
        if obj is self.parent_widget and event.type() == QEvent.Resize:
            self._restack()
        return False
