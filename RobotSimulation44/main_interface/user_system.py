# user_system.py
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from .layout_controller import LayoutController

class UserSystem(QMainWindow):
    def __init__(self, bus, task_manager):
        super().__init__()
        self.setWindowTitle("User System")
        self.setGeometry(1100, 100, 900, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # LayoutController for tasks
        self.layout_controller = LayoutController(layout, task_manager)

        # Status label (reuse your existing logic)
        self.status_label = QLabel("Select tasks to begin.")
        layout.addWidget(self.status_label)
        self.layout_controller.set_status_label(self.status_label)

        # Start/Pause buttons
        self.start_btn = QPushButton("Start")
        self.pause_btn = QPushButton("Pause")
        layout.addWidget(self.start_btn)
        layout.addWidget(self.pause_btn)

        # Connect shared bus signals
        bus.tasks_changed.connect(self.layout_controller.update_workspace)
        bus.start_pressed.connect(self.layout_controller.start_tasks)
        bus.pause_pressed.connect(self.layout_controller.stop_tasks)

        # Buttons emit to shared bus
        self.start_btn.clicked.connect(bus.start_pressed)
        self.pause_btn.clicked.connect(bus.pause_pressed)
