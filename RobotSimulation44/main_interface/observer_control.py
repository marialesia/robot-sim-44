# main_interface/observer_control.py
from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QCheckBox, QPushButton,
    QComboBox, QLabel, QGroupBox
)
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QTimer, QTime 
from event_logger import get_logger

class ObserverControl(QObject):
    # Signals to communicate with layout controller
    tasks_changed = pyqtSignal(list)
    start_pressed = pyqtSignal()
    pause_pressed = pyqtSignal()
    stop_pressed = pyqtSignal()

    def __init__(self, parent_layout):
        super().__init__()

        # Create top control bar layout
        self.control_bar = QVBoxLayout()

        # --- Row 1: Buttons (right aligned) ---
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.pause_button)
        button_row.addWidget(self.stop_button)
        self.control_bar.addLayout(button_row)

        # TIMER
        self.timer_label = QLabel("00:00")
        button_row.addWidget(self.timer_label)  

        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self.update_timer)
        self.start_time = None
        self.elapsed_time = 0  # seconds elapsed before last stop
        self.running = False

        # Connect timer to buttons
        self.start_button.clicked.connect(self.start_timer)
        self.stop_button.clicked.connect(self.stop_timer)

        # --- Row 2: Task groups side by side ---
        tasks_row = QHBoxLayout()
        tasks_row.setAlignment(Qt.AlignTop)

        # Sorting group
        sorting_group = QGroupBox("Sorting")
        sorting_layout = QVBoxLayout()
        sorting_layout.setSpacing(5)

        self.sorting_checkbox = QCheckBox("Enable Sorting")
        sorting_layout.addWidget(self.sorting_checkbox)

        sorting_layout.addWidget(QLabel("Pace:"))
        self.sort_pace_dropdown = QComboBox()
        self.sort_pace_dropdown.addItems(["slow", "medium", "fast"])
        sorting_layout.addWidget(self.sort_pace_dropdown)

        sorting_layout.addWidget(QLabel("Bins:"))
        self.sort_bin_dropdown = QComboBox()
        self.sort_bin_dropdown.addItems(["2", "4", "6"])
        sorting_layout.addWidget(self.sort_bin_dropdown)

        sorting_layout.addWidget(QLabel("Error Rate:"))
        self.sort_error_dropdown = QComboBox()
        self.sort_error_dropdown.addItems(["0%", "5%", "10%", "20%"])
        sorting_layout.addWidget(self.sort_error_dropdown)

        sorting_group.setLayout(sorting_layout)
        tasks_row.addWidget(sorting_group)

        # Packaging group
        packaging_group = QGroupBox("Packaging")
        packaging_layout = QVBoxLayout()
        packaging_layout.setSpacing(5)

        self.packaging_checkbox = QCheckBox("Enable Packaging")
        packaging_layout.addWidget(self.packaging_checkbox)

        packaging_layout.addWidget(QLabel("Pace:"))
        self.pack_pace_dropdown = QComboBox()
        self.pack_pace_dropdown.addItems(["slow", "medium", "fast"])
        packaging_layout.addWidget(self.pack_pace_dropdown)

        # packaging_layout.addWidget(QLabel("Bins:"))
        # self.pack_bin_dropdown = QComboBox()
        # self.pack_bin_dropdown.addItems(["2", "4", "6"])
        # packaging_layout.addWidget(self.pack_bin_dropdown)

        packaging_layout.addWidget(QLabel("Error Rate:"))
        self.pack_error_dropdown = QComboBox()
        self.pack_error_dropdown.addItems(["0%", "5%", "10%", "20%"])
        packaging_layout.addWidget(self.pack_error_dropdown)

        packaging_group.setLayout(packaging_layout)
        tasks_row.addWidget(packaging_group)

        # Inspection group
        inspection_group = QGroupBox("Inspection")
        inspection_layout = QVBoxLayout()
        inspection_layout.setSpacing(5)

        self.inspection_checkbox = QCheckBox("Enable Inspection")
        inspection_layout.addWidget(self.inspection_checkbox)

        inspection_layout.addWidget(QLabel("Pace:"))
        self.insp_pace_dropdown = QComboBox()
        self.insp_pace_dropdown.addItems(["slow", "medium", "fast"])
        inspection_layout.addWidget(self.insp_pace_dropdown)

        # inspection_layout.addWidget(QLabel("Bins:"))
        # self.insp_bin_dropdown = QComboBox()
        # self.insp_bin_dropdown.addItems(["2", "4", "6"])
        # inspection_layout.addWidget(self.insp_bin_dropdown)

        inspection_layout.addWidget(QLabel("Error Rate:"))
        self.insp_error_dropdown = QComboBox()
        self.insp_error_dropdown.addItems(["0%", "5%", "10%", "20%"])
        inspection_layout.addWidget(self.insp_error_dropdown)

        inspection_group.setLayout(inspection_layout)
        tasks_row.addWidget(inspection_group)

        self.control_bar.addLayout(tasks_row)
        parent_layout.addLayout(self.control_bar)

        # === Connections ===
        self.sorting_checkbox.stateChanged.connect(self.update_tasks)
        self.packaging_checkbox.stateChanged.connect(self.update_tasks)
        self.inspection_checkbox.stateChanged.connect(self.update_tasks)

        self.start_button.clicked.connect(lambda: self.start_pressed.emit())
        self.pause_button.clicked.connect(lambda: self.pause_pressed.emit())
        self.stop_button.clicked.connect(lambda: self.stop_pressed.emit())

        # --- Logging for top bar user actions ---
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

    def update_tasks(self):
        active_tasks = []
        if self.sorting_checkbox.isChecked():
            active_tasks.append("sorting")
        if self.packaging_checkbox.isChecked():
            active_tasks.append("packaging")
        if self.inspection_checkbox.isChecked():
            active_tasks.append("inspection")
        self.tasks_changed.emit(active_tasks)

    def get_sort_pace(self):
        return self.sort_pace_dropdown.currentText()

    def get_sort_bin_count(self):
        return int(self.sort_bin_dropdown.currentText())

    def get_sort_error_rate(self):
        # strip '%' and convert to decimal fraction
        value = self.sort_error_dropdown.currentText()
        if value.endswith("%"):
            return int(value[:-1]) / 100.0
        return 0.0

    def get_pack_pace(self):
        return self.pack_pace_dropdown.currentText()

    def get_pack_error_rate(self):
        # strip '%' and convert to decimal fraction
        value = self.pack_error_dropdown.currentText()
        if value.endswith("%"):
            return int(value[:-1]) / 100.0
        return 0.0

    def get_insp_pace(self):
        return self.insp_pace_dropdown.currentText()

    def get_insp_error_rate(self):
        # strip '%' and convert to decimal fraction
        value = self.insp_error_dropdown.currentText()
        if value.endswith("%"):
            return int(value[:-1]) / 100.0
        return 0.0

    def get_params_for_task(self, task_name):
        """Return a dict of parameters for a given task name."""
        task_name = task_name.lower()
        if task_name == "sorting":
            return {
                "pace": self.get_sort_pace(),
                "bin_count": self.get_sort_bin_count(),
                "error_rate": self.get_sort_error_rate(),
            }
        elif task_name == "packaging":
            # return packaging-specific params
            return {
                "pace": self.get_pack_pace(),
                "error_rate": self.get_pack_error_rate(),
            }
        elif task_name == "inspection":
            # return inspection-specific params
            return {
                "pace": self.get_insp_pace(),
                "error_rate": self.get_insp_error_rate(),
            }
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