# main_interface/unified_interface.py
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from .task_manager import TaskManager
from main_interface.observer_control import ObserverControl
from main_interface.layout_controller import LayoutController
from main_interface.metrics_manager import MetricsManager
import os, subprocess, sys


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

        # --- Apply dark navy style (Qt-safe) ---
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1b2430;   /* darker navy */
            }
            QLabel {
                color: #f0f0f0;              /* light text */
                font-size: 15px;
                font-weight: bold;
            }
        """)

        # Status label
        self.status_label = QLabel("Select tasks to begin.")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.status_label)

        # Layout controller (workspace)
        self.layout_controller = LayoutController(self.main_layout, self.task_manager)
        self.layout_controller.set_status_label(self.status_label)

        # --- let TaskManager update panels when network 'start' or 'update_active' comes in
        if hasattr(self.task_manager, "set_workspace_updater"):
            self.task_manager.set_workspace_updater(self.layout_controller.update_workspace)


class ObserverSystemWindow(QMainWindow):
    def __init__(self, task_manager, server=None):
        super().__init__()
        self.setWindowTitle("Observer System")
        self.setGeometry(950, 100, 900, 800)

        self.task_manager = task_manager
        self.server = server   # <--- store server reference

        # Central widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setAlignment(Qt.AlignTop)

        # Observer controls
        self.observer_control = ObserverControl(self.main_layout)

        # Hook control signals to network send
        if self.server:
            # --- Checkbox updates (send active immediately) ---
            self.observer_control.tasks_changed.connect(
                lambda active: self.server.send({
                    "command": "update_active",
                    "active": active
                })
            )

            # --- Buttons ---
            self.observer_control.start_pressed.connect(
                lambda: self.server.send({
                    "command": "start",
                    "params": {
                        "sorting": self.observer_control.get_params_for_task("sorting"),
                        "packaging": self.observer_control.get_params_for_task("packaging"),
                        "inspection": self.observer_control.get_params_for_task("inspection"),
                        "active": self.observer_control.get_active_tasks()
                    }
                })
            )
            self.observer_control.stop_pressed.connect(lambda: self.server.send({"command": "stop"}))

        # Metrics manager
        self.metrics_manager = MetricsManager()
        self.main_layout.addWidget(self.metrics_manager)

        # --- Log folder button ---
        self.log_button = QPushButton("Open Log Folder")
        self.log_button.clicked.connect(self.open_log_folder)
        self.main_layout.addWidget(self.log_button)

        if hasattr(self.task_manager, "set_metrics_manager"):
            self.task_manager.set_metrics_manager(self.metrics_manager)

    def open_log_folder(self):
        """Opens the logs folder on the observers machine."""
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)

        if sys.platform.startswith("darwin"):   # macOS
            subprocess.Popen(["open", log_dir])
        elif os.name == "nt":                   # Windows
            os.startfile(log_dir)
        elif os.name == "posix":                # Linux
            subprocess.Popen(["xdg-open", log_dir])
