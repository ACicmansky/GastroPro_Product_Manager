# src/gui/widgets.py
from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt

class DropArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.label = QLabel("Presuňte CSV súbor sem alebo kliknite sem pre výber súboru")
        self.label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith('.csv'):
                self.parent().load_csv_file(file_path)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # The parent of DropArea is the central widget, its parent is the MainWindow
            self.parent().parent().select_csv_file()
        super().mousePressEvent(event)

class TopchladenieCsvDropArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.label = QLabel("Presuňte Topchladenie.sk CSV súbor sem alebo kliknite sem pre výber súboru")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("QLabel { color: #666; font-size: 12px; }")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMaximumHeight(60)
        self.topchladenie_df = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith('.csv'):
                self.parent().load_topchladenie_csv_file(file_path)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent().parent().parent().select_topchladenie_csv_file()
        super().mousePressEvent(event)
    
    def clear_file(self):
        self.topchladenie_df = None
        self.label.setText("Presuňte Topchladenie.sk CSV súbor sem alebo kliknite sem pre výber súboru")
        self.label.setStyleSheet("QLabel { color: #666; font-size: 12px; }")
