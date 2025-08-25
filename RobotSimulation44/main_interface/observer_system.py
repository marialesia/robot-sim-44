# observer_system.py
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton
from .observer_control import ObserverControl
from .metrics_display import MetricsDisplay

class ObserverSystem(QMainWindow):
    def __init__(self, bus):
        super().__init__()
        self.setWindowTitle("Observer System")
        self.setGeometry(100, 100, 900, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Observer controls (existing functionality)
        self.observer_control = ObserverControl(layout)

        # Metrics display (placeholder widget for now)
        self.metrics = MetricsDisplay()
        layout.addWidget(self.metrics)

        # Start/Pause buttons
        self.start_btn = QPushButton("Start")
        self.pause_btn = QPushButton("Pause")
        layout.addWidget(self.start_btn)
        layout.addWidget(self.pause_btn)

        # Connect signals to the shared bus
        self.observer_control.tasks_changed.connect(bus.tasks_changed)
        self.start_btn.clicked.connect(bus.start_pressed)
        self.pause_btn.clicked.connect(bus.pause_pressed)
