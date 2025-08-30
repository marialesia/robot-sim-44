# main_interface/unified_interface.py
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import QTimer
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
        self.layout_controller = LayoutController(self.main_layout, self.task_manager)

        # Timer: Bottom layout for status and timer
        bottom_layout = QHBoxLayout()

        # Status label (bottom)
        self.status_label = QLabel("Select tasks to begin.")
        self.main_layout.addWidget(self.status_label)

        # Timer: Stretch pushes timer to the right
        bottom_layout.addStretch()

        # Timer Label (bottom right)
        self.timer_label = QLabel("Session Time: 00:00")
        bottom_layout.addWidget(self.timer_label) 

        # Timer: Add bottom layout to main layout
        self.main_layout.addLayout(bottom_layout)

        # Assign status label after creation
        self.layout_controller.set_status_label(self.status_label)

        # Timer: QTimer setup + elapsed seconds counter
        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self.update_timer)
        self.elapsed_seconds = 0

        # ===== Connect signals =====
        self.observer_control.tasks_changed.connect(self.layout_controller.update_workspace)
        self.observer_control.start_pressed.connect(self.layout_controller.start_tasks)
        self.observer_control.stop_pressed.connect(self.layout_controller.stop_tasks)

        # Timer: Hook into start/stop signals
        self.observer_control.start_pressed.connect(self.start_timer)
        self.observer_control.stop_pressed.connect(self.stop_timer)

    # Timer: Timer helper methods
    def start_timer(self):  # Starts or resumes session timer
        if not self.session_timer.isActive():
            self.session_timer.start(1000)  # tick every 1 second

    def stop_timer(self):   # Pause session timer without resetting
        self.session_timer.stop()
        

    def update_timer(self):
        self.elapsed_seconds += 1
        minutes = self.elapsed_seconds // 60
        seconds = self.elapsed_seconds % 60
        self.timer_label.setText(f"Session Time: {minutes:02}:{seconds:02}")