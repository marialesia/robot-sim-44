# main_interface/observer_control.py
from PyQt5.QtWidgets import QHBoxLayout, QCheckBox, QPushButton, QComboBox, QLabel
from PyQt5.QtCore import QObject, pyqtSignal
from event_logger import get_logger

class ObserverControl(QObject):
    # Signals to communicate with layout controller
    tasks_changed = pyqtSignal(list)
    start_pressed = pyqtSignal()
    stop_pressed = pyqtSignal()

    def __init__(self, parent_layout):
        super().__init__()  # important to initialize QObject

        # Create top control bar layout
        self.control_bar = QHBoxLayout()

        # Task checkboxes
        self.sorting_checkbox = QCheckBox("Sorting")
        self.packaging_checkbox = QCheckBox("Packaging")
        self.inspection_checkbox = QCheckBox("Inspection")

        # Connect signals
        self.sorting_checkbox.stateChanged.connect(self.update_tasks)
        self.packaging_checkbox.stateChanged.connect(self.update_tasks)
        self.inspection_checkbox.stateChanged.connect(self.update_tasks)

        self.control_bar.addWidget(self.sorting_checkbox)
        self.control_bar.addWidget(self.packaging_checkbox)
        self.control_bar.addWidget(self.inspection_checkbox)

        # ===== New controls for Sorting Parameters =====
        param_layout = QHBoxLayout()

        # Pace dropdown
        self.pace_dropdown = QComboBox()
        self.pace_dropdown.addItems(["slow", "medium", "fast"])
        param_layout.addWidget(QLabel("Pace:"))
        param_layout.addWidget(self.pace_dropdown)

        # Bin Count dropdown
        self.bin_dropdown = QComboBox()
        self.bin_dropdown.addItems(["2", "4", "6"])
        param_layout.addWidget(QLabel("Bins:"))
        param_layout.addWidget(self.bin_dropdown)

        # Error Rate dropdown
        self.error_dropdown = QComboBox()
        self.error_dropdown.addItems(["0%", "5%", "10%", "20%"])
        param_layout.addWidget(QLabel("Error Rate:"))
        param_layout.addWidget(self.error_dropdown)

        self.control_bar.addLayout(param_layout)

        # Start / Pause buttons
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Pause")  # behaves like pause
        self.start_button.clicked.connect(lambda: self.start_pressed.emit())
        self.stop_button.clicked.connect(lambda: self.stop_pressed.emit())
        self.control_bar.addWidget(self.start_button)
        self.control_bar.addWidget(self.stop_button)

        # --- Logging for top bar user actions ---  # <<< NEW
        self.start_button.clicked.connect(
            lambda: get_logger().log_user("TopBar", "Start button", "click", "Start pressed")
        )
        self.stop_button.clicked.connect(
            lambda: get_logger().log_user("TopBar", "Pause button", "click", "Pause pressed")
        )
        self.sorting_checkbox.stateChanged.connect(
            lambda s: get_logger().log_user("TopBar", "Sorting checkbox", "toggle",
                                            "checked" if s else "unchecked")
        )
        self.packaging_checkbox.stateChanged.connect(
            lambda s: get_logger().log_user("TopBar", "Packaging checkbox", "toggle",
                                            "checked" if s else "unchecked")
        )
        self.inspection_checkbox.stateChanged.connect(
            lambda s: get_logger().log_user("TopBar", "Inspection checkbox", "toggle",
                                            "checked" if s else "unchecked")
        )

        parent_layout.addLayout(self.control_bar)

    def update_tasks(self):
        active_tasks = []
        if self.sorting_checkbox.isChecked():
            active_tasks.append("sorting")
        if self.packaging_checkbox.isChecked():
            active_tasks.append("packaging")
        if self.inspection_checkbox.isChecked():
            active_tasks.append("inspection")
        self.tasks_changed.emit(active_tasks)

    def get_pace(self):
        return self.pace_dropdown.currentText()

    def get_bin_count(self):
        return int(self.bin_dropdown.currentText())

    def get_error_rate(self):
        # strip '%' and convert to decimal fraction
        value = self.error_dropdown.currentText()
        if value.endswith("%"):
            return int(value[:-1]) / 100.0
        return 0.0
