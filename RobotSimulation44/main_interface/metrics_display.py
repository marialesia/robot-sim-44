# metrics_display.py
from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout

class MetricsDisplay(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        # Just a placeholder for now
        layout.addWidget(QLabel("Metrics Placeholder (future stats here)"))
