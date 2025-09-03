# main_interface/observer_control.py
from PyQt5.QtWidgets import QHBoxLayout, QCheckBox, QPushButton, QComboBox, QLabel
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QTime 
from event_logger import get_logger

class ObserverControl(QObject):
    # Signals to communicate with layout controller
    tasks_changed = pyqtSignal(list)
    start_pressed = pyqtSignal()
    pause_pressed = pyqtSignal()
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
        self.pause_button = QPushButton("Pause") 
        self.stop_button = QPushButton("Stop")
        self.start_button.clicked.connect(lambda: self.start_pressed.emit())
        self.pause_button.clicked.connect(lambda: self.pause_pressed.emit())
        self.stop_button.clicked.connect(lambda: self.stop_pressed.emit())
        self.control_bar.addWidget(self.start_button)
        self.control_bar.addWidget(self.pause_button)
        self.control_bar.addWidget(self.stop_button)

        # --- Logging for top bar user actions ---  # <<< NEW
        self.start_button.clicked.connect(
            lambda: get_logger().log_user("TopBar", "Start button", "click", "Start pressed")
        )
        self.pause_button.clicked.connect(
            lambda: get_logger().log_user("TopBar", "Pause button", "click", "Pause pressed")
        )
        self.stop_button.clicked.connect(
            lambda: get_logger().log_user("TopBar", "Stop button", "click", "Stop pressed")
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

        # TIMER
        self.timer_label = QLabel("00:00")
        self.control_bar.addWidget(self.timer_label)  

        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self.update_timer)
        self.start_time = None
        self.elapsed_time = 0  # seconds elapsed before last stop
        self.running = False

        # Connect timer to buttons
        self.start_button.clicked.connect(self.start_timer)
        self.stop_button.clicked.connect(self.stop_timer)


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

    def get_params_for_task(self, task_name):
        """Return a dict of parameters for a given task name."""
        task_name = task_name.lower()
        if task_name == "sorting":
            return {
                "pace": self.get_pace(),
                "bin_count": self.get_bin_count(),
                "error_rate": self.get_error_rate(),
            }
        elif task_name == "packaging":
            # return packaging-specific params
            return {}
        elif task_name == "inspection":
            # return inspection-specific params
            return {}
        else:
            return {}

    # TIMER METHODS
    def start_timer(self):
        # Reset timer
        self.elapsed_time = 0
        self.start_time = QTime.currentTime()
        self.session_timer.start(1000)  # update every second
        self.running = True
        self.timer_label.setText("00:00")  # reset display
        # Log start
        get_logger().log_user("ObserverControl", "Session Timer", "start", "Timer started")

    def stop_timer(self):
        if self.running:
            # Pause and keep elapsed time 
            self.elapsed_time += self.start_time.secsTo(QTime.currentTime())
            self.session_timer.stop()
            self.running = False
            # Log stop
            get_logger().log_user("ObserverControl", "Session Timer", "stop", "Timer paused")

    def update_timer(self):
        if self.start_time and self.running:
            total_seconds = self.elapsed_time + self.start_time.secsTo(QTime.currentTime())
            mins, secs = divmod(total_seconds, 60)
            self.timer_label.setText(f"{mins:02}:{secs:02}")