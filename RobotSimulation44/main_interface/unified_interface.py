# main_interface/unified_interface.py
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
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
        self.main_layout.setAlignment(Qt.AlignTop)  # <- top-align everything

        # Observer controls (top)
        self.observer_control = ObserverControl(self.main_layout)

        # Metrics manager (immediately below)
        self.metrics_manager = MetricsManager()
        self.main_layout.addWidget(self.metrics_manager)

        # Pass the metrics manager down to task manager
        if hasattr(self.task_manager, "set_metrics_manager"):
            self.task_manager.set_metrics_manager(self.metrics_manager)