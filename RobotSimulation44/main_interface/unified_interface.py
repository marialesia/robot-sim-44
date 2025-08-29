# main_interface/unified_interface.py
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from .task_manager import TaskManager
from .observer_control import ObserverControl
from .layout_controller import LayoutController

class UnifiedInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robotic Simulation 44")
        self.setGeometry(100, 100, 1800, 800)

        # Task manager
        self.task_manager = TaskManager()

        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)

        # ===== Observer Control (top) =====
        self.observer_control = ObserverControl(self.main_layout)

        # Workspace area (middle)
        self.layout_controller = LayoutController(self.main_layout, self.task_manager, observer_control=self.observer_control)

        # Status label (bottom)
        self.status_label = QLabel("Select tasks to begin.")
        self.main_layout.addWidget(self.status_label)

        # Assign status label after creation
        self.layout_controller.set_status_label(self.status_label)

        # ===== Connect signals =====
        self.observer_control.tasks_changed.connect(self.layout_controller.update_workspace)
        self.observer_control.start_pressed.connect(self.layout_controller.start_tasks)
        self.observer_control.stop_pressed.connect(self.layout_controller.stop_tasks)


