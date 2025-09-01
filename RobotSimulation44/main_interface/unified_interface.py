# main_interface/unified_interface.py
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from .task_manager import TaskManager
from .observer_control import ObserverControl
from .layout_controller import LayoutController
from .metrics_manager import MetricsManager

class UserSystemWindow(QMainWindow):
    def __init__(self, task_manager):
        super().__init__()
        self.setWindowTitle("User System")
        self.setGeometry(100, 100, 900, 800)

        self.task_manager = task_manager

        # Central widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)

        # Status label
        self.status_label = QLabel("Select tasks to begin.")
        self.main_layout.addWidget(self.status_label)

        # Layout controller (workspace)
        self.layout_controller = LayoutController(self.main_layout, self.task_manager)
        self.layout_controller.set_status_label(self.status_label)

class ObserverSystemWindow(QMainWindow):
    def __init__(self, task_manager):
        super().__init__()
        self.setWindowTitle("Observer System")
        self.setGeometry(950, 100, 900, 800)

        self.task_manager = task_manager

        # Central widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)

        # Observer controls
        self.observer_control = ObserverControl(self.main_layout)

        # Metrics manager (bottom)
        self.metrics_manager = MetricsManager()
        self.main_layout.addWidget(self.metrics_manager)

        # Pass the metrics manager down to task manager so all tasks can use it
        if hasattr(self.task_manager, "set_metrics_manager"):
            self.task_manager.set_metrics_manager(self.metrics_manager)
