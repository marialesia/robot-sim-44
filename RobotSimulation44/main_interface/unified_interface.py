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

        # Status label (bottom)
        self.status_label = QLabel("Select tasks to begin.")
        self.main_layout.addWidget(self.status_label)

        # Assign status label after creation
        self.layout_controller.set_status_label(self.status_label)

        # ===== Connect signals =====
        self.observer_control.tasks_changed.connect(self.layout_controller.update_workspace)
        self.observer_control.start_pressed.connect(self.layout_controller.start_tasks)
        self.observer_control.stop_pressed.connect(self.layout_controller.stop_tasks)


