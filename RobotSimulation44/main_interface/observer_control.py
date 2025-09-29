from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QCheckBox, QPushButton,
    QComboBox, QLabel, QGroupBox, QFileDialog, QLineEdit, QSlider
)
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QTimer, QTime 
from event_logger import get_logger
import json

class ObserverControl(QObject):
    # Signals to communicate with layout controller
    tasks_changed = pyqtSignal(list)
    start_pressed = pyqtSignal()
    complete_pressed = pyqtSignal()
    stop_pressed = pyqtSignal()

    def __init__(self, parent_layout, audio_manager=None):
        super().__init__()

        self.audio_manager = audio_manager

        # Create top control bar layout
        self.control_bar = QVBoxLayout()

        # --- Row 0: Scenario name input ---
        scenario_row = QHBoxLayout()
        scenario_row.addWidget(QLabel("Scenario Name:"))
        self.scenario_name_input = QLineEdit()
        self.scenario_name_input.setPlaceholderText("Enter scenario name...")
        scenario_row.addWidget(self.scenario_name_input)
        self.control_bar.addLayout(scenario_row)

        # --- Row 1: Buttons (right aligned) ---
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.start_button = QPushButton("Start")
        self.complete_button = QPushButton("Complete")
        self.stop_button = QPushButton("Stop")
        # --- New Save / Load buttons ---
        self.save_button = QPushButton("Save Params")
        self.load_button = QPushButton("Load Params")
        # --- New user input for time limit ---
        self.time_limit_input = QLineEdit()
        self.time_limit_input.setPlaceholderText("Time Limit")
        self.time_limit_input.setFixedWidth(70)
        button_row.addWidget(self.start_button)
        # button_row.addWidget(self.complete_button)
        button_row.addWidget(self.stop_button)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.load_button)
        button_row.addWidget(self.time_limit_input)
        self.control_bar.addLayout(button_row)

        # TIMER
        self.timer_label = QLabel("00:00")
        button_row.addWidget(self.timer_label)  

        # --- Connection Status ---
        self.connection_label = QLabel("Not connected")
        self.connection_label.setStyleSheet("color: red; font-weight: bold;")
        self.control_bar.addWidget(self.connection_label)

        def set_connection_status(self, connected: bool):
            if connected:
                self.connection_label.setText("Connection successful")
                self.connection_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.connection_label.setText("Disconnected")
                self.connection_label.setStyleSheet("color: red; font-weight: bold;")

        # Time Input handler
        self.time_limit_input.editingFinished.connect(self.format_time_input)
        self.flash_count = 0
        self.flash_timer = None

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

        # --- Helper function to create slider + editable input for error rate ---
        def create_slider_with_input():
            container = QHBoxLayout()
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(0)
            slider.setTickInterval(5)
            slider.setTickPosition(QSlider.TicksBelow)
            input_field = QLineEdit("0")
            input_field.setFixedWidth(50)
            container.addWidget(slider)
            container.addWidget(input_field)

            # Connect slider -> input_field
            slider.valueChanged.connect(lambda val: input_field.setText(str(val)))
            # Connect input_field -> slider
            def text_changed():
                try:
                    val = int(input_field.text())
                    if 0 <= val <= 100:
                        slider.setValue(val)
                except ValueError:
                    pass
            input_field.editingFinished.connect(text_changed)
            return slider, input_field, container

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
        self.sort_error_slider, self.sort_error_input, slider_layout = create_slider_with_input()
        sorting_layout.addLayout(slider_layout)

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

        packaging_layout.addWidget(QLabel("Limit:"))
        self.pack_limit_dropdown = QComboBox()
        self.pack_limit_dropdown.addItems(["6", "5 - 6", "4 - 6"])
        packaging_layout.addWidget(self.pack_limit_dropdown)

        packaging_layout.addWidget(QLabel("Error Rate:"))
        self.pack_error_slider, self.pack_error_input, slider_layout = create_slider_with_input()
        packaging_layout.addLayout(slider_layout)

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

        inspection_layout.addWidget(QLabel("Error Rate:"))
        self.insp_error_slider, self.insp_error_input, slider_layout = create_slider_with_input()
        inspection_layout.addLayout(slider_layout)

        inspection_group.setLayout(inspection_layout)
        tasks_row.addWidget(inspection_group)

        self.control_bar.addLayout(tasks_row)
        parent_layout.addLayout(self.control_bar)

        # --- Sound Controls group ---
        sound_group = QGroupBox("Sound Controls")
        sound_layout = QHBoxLayout()

        self.conveyor_checkbox = QCheckBox("Conveyor")
        self.conveyor_checkbox.setChecked(True)
        sound_layout.addWidget(self.conveyor_checkbox)

        self.robotic_arm_checkbox = QCheckBox("Robotic Arm")
        self.robotic_arm_checkbox.setChecked(True)
        sound_layout.addWidget(self.robotic_arm_checkbox)

        self.correct_checkbox = QCheckBox("Correct Chime")
        self.correct_checkbox.setChecked(True)
        sound_layout.addWidget(self.correct_checkbox)

        self.incorrect_checkbox = QCheckBox("Incorrect Chime")
        self.incorrect_checkbox.setChecked(True)
        sound_layout.addWidget(self.incorrect_checkbox)

        self.alarm_checkbox = QCheckBox("Alarm")
        self.alarm_checkbox.setChecked(True)
        sound_layout.addWidget(self.alarm_checkbox)

        sound_group.setLayout(sound_layout)
        self.control_bar.addWidget(sound_group)

        # === Connections for checkboxes and task updates ===
        self.sorting_checkbox.stateChanged.connect(self.update_tasks)
        self.packaging_checkbox.stateChanged.connect(self.update_tasks)
        self.inspection_checkbox.stateChanged.connect(self.update_tasks)

        # === Connections for start/stop buttons ===
        self.start_button.clicked.connect(lambda: self.start_pressed.emit())
        self.complete_button.clicked.connect(lambda: self.complete_pressed.emit())
        self.stop_button.clicked.connect(lambda: self.stop_pressed.emit())

        # === Connections for save/load buttons ===
        self.save_button.clicked.connect(self.save_parameters)
        self.load_button.clicked.connect(self.load_parameters)

    # --- Connection status updater ---
    def set_connection_status(self, text, success=True):
        """Update connection status text & colour."""
        if success:
            self.connection_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.connection_label.setStyleSheet("color: red; font-weight: bold;")
        self.connection_label.setText(text)

    # --- Task getter functions ---
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
        return self.sort_error_slider.value() / 100.0

    def get_pack_pace(self):
        return self.pack_pace_dropdown.currentText()

    def get_pack_limit(self):
        return self.pack_limit_dropdown.currentText()

    def get_pack_error_rate(self):
        return self.pack_error_slider.value() / 100.0

    def get_insp_pace(self):
        return self.insp_pace_dropdown.currentText()

    def get_insp_error_rate(self):
        return self.insp_error_slider.value() / 100.0
    
    def get_active_tasks(self):
        """Return list of task names that are enabled via checkboxes."""
        active = []
        if self.sorting_checkbox.isChecked():
            active.append("sorting")
        if self.packaging_checkbox.isChecked():
            active.append("packaging")
        if self.inspection_checkbox.isChecked():
            active.append("inspection")
        return active

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
            return {
                "pace": self.get_pack_pace(),
                "error_rate": self.get_pack_error_rate(),
                "limit": self.get_pack_limit(),
            }
        elif task_name == "inspection":
            return {
                "pace": self.get_insp_pace(),
                "error_rate": self.get_insp_error_rate(),
            }
        else:
            return {}

    def get_sounds_enabled(self):
        """Return a dict of which sounds are enabled."""
        return {
            "conveyor": self.conveyor_checkbox.isChecked(),
            "robotic_arm": self.robotic_arm_checkbox.isChecked(),
            "correct_chime": self.correct_checkbox.isChecked(),
            "incorrect_chime": self.incorrect_checkbox.isChecked(),
            "alarm": self.alarm_checkbox.isChecked()
        }

    # --- TIMER METHODS ---
    def start_timer(self):
        if self.flash_timer:
            self.flash_timer.stop()
            self.flash_timer = None
            self.timer_label.setStyleSheet("")
        self.elapsed_time = 0
        self.start_time = QTime.currentTime()
        self.session_timer.start(1000)
        self.running = True
        self.timer_label.setText("00:00")
        self.time_limit_input.setDisabled(True)

    def stop_timer(self):
        if self.running:
            self.elapsed_time += self.start_time.secsTo(QTime.currentTime())
            self.session_timer.stop()
            self.running = False
            self.time_limit_input.setDisabled(False)

    def update_timer(self):
        if self.start_time and self.running:
            total_seconds = self.elapsed_time + self.start_time.secsTo(QTime.currentTime())
            mins, secs = divmod(total_seconds, 60)
            self.timer_label.setText(f"{mins:02}:{secs:02}")
            try:
                m, s = map(int, self.time_limit_input.text().split(":"))
                time_limit_seconds = m * 60 + s
                if total_seconds >= time_limit_seconds:
                    self.stop_timer()
                    self.complete_pressed.emit()
                    self.timer_label.setStyleSheet("color: red")
                    self.flash_count = 0
                    self.flash_timer = QTimer()
                    self.flash_timer.timeout.connect(self._flash_timer_label)
                    self.flash_timer.start(500)
            except ValueError:
                pass

    def get_timestamp(self):
        return self.timer_label.text()

    # --- SAVE / LOAD FUNCTIONS ---
    def save_parameters(self):
        scenario_name = self.scenario_name_input.text().strip() or "Unnamed_Scenario"
        params = {
            "scenario_name": scenario_name,
            "time_limit": self.time_limit_input.text().strip() or "00:00",
            "sorting": {
                "enabled": self.sorting_checkbox.isChecked(),
                "pace": self.sort_pace_dropdown.currentText(),
                "bin_count": self.sort_bin_dropdown.currentText(),
                "error_rate": self.sort_error_slider.value(),
            },
            "packaging": {
                "enabled": self.packaging_checkbox.isChecked(),
                "pace": self.pack_pace_dropdown.currentText(),
                "error_rate": self.pack_error_slider.value(),
            },
            "inspection": {
                "enabled": self.inspection_checkbox.isChecked(),
                "pace": self.insp_pace_dropdown.currentText(),
                "error_rate": self.insp_error_slider.value(),
            },
            "sounds": self.get_sounds_enabled()
        }
        default_filename = f"{scenario_name}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            None, "Save Parameters", default_filename, "JSON Files (*.json)"
        )
        if file_path:
            with open(file_path, "w") as f:
                json.dump(params, f, indent=4)
            print(f"Parameters saved to {file_path} with scenario name '{scenario_name}'")

    def load_parameters(self):
        file_path, _ = QFileDialog.getOpenFileName(None, "Load Parameters", "", "JSON Files (*.json)")
        if not file_path:
            return
        with open(file_path, "r") as f:
            params = json.load(f)
        self.scenario_name_input.setText(params.get("scenario_name", ""))
        self.time_limit_input.setText(params.get("time_limit", "00:00"))
        if "sorting" in params:
            s = params["sorting"]
            self.sorting_checkbox.setChecked(s.get("enabled", False))
            self.sort_pace_dropdown.setCurrentText(s.get("pace", "medium"))
            self.sort_bin_dropdown.setCurrentText(s.get("bin_count", "2"))
            self.sort_error_slider.setValue(s.get("error_rate", 0))
        if "packaging" in params:
            p = params["packaging"]
            self.packaging_checkbox.setChecked(p.get("enabled", False))
            self.pack_pace_dropdown.setCurrentText(p.get("pace", "medium"))
            self.pack_error_slider.setValue(p.get("error_rate", 0))
        if "inspection" in params:
            i = params["inspection"]
            self.inspection_checkbox.setChecked(i.get("enabled", False))
            self.insp_pace_dropdown.setCurrentText(i.get("pace", "medium"))
            self.insp_error_slider.setValue(i.get("error_rate", 0))
        sounds = params.get("sounds", {})
        self.conveyor_checkbox.setChecked(sounds.get("conveyor", True))
        self.robotic_arm_checkbox.setChecked(sounds.get("robotic_arm", True))
        self.correct_checkbox.setChecked(sounds.get("correct_chime", True))
        self.incorrect_checkbox.setChecked(sounds.get("incorrect_chime", True))
        self.alarm_checkbox.setChecked(sounds.get("alarm", True))
        self.update_tasks()
        print(f"Parameters loaded from {file_path}")

    def format_time_input(self):
        text = self.time_limit_input.text().strip()
        if not text:
            self.time_limit_input.clear()
            return
        try:
            if ":" in text:
                parts = list(map(int, text.split(":")))
                while len(parts) < 2:
                    parts.insert(0, 0)
                m, s = parts
            else:
                m, s = int(text), 0
            m = max(0, min(m, 99))
            s = max(0, min(s, 59))
            self.time_limit_input.setText(f"{m:02}:{s:02}")
        except ValueError:
            self.time_limit_input.setText("00:00")

    def _flash_timer_label(self):
        if self.flash_count >= 100:
            if self.flash_timer:
                self.flash_timer.stop()
            self.timer_label.setStyleSheet("")
            return
        if self.flash_count % 2 == 0:
            self.timer_label.setStyleSheet("color: red;")
        else:
            self.timer_label.setStyleSheet("")
        self.flash_count += 1
