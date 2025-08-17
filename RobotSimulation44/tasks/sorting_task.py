# tasks/sorting_task.py
import random
import time
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QLabel
from .base_task import BaseTask, StorageContainerWidget

# ------------------------------ Box widget ------------------------------ 
class BoxWidget(QWidget):
    def __init__(self, parent=None, width=20, height=20, color=QColor("yellow")):
        super().__init__(parent)
        self.width_box = width
        self.height_box = height
        self.color = color
        self.x_pos = 0
        self.y_pos = 40
        self.moving = True
        self.finished = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.move_step)
        self.setFixedSize(self.width_box, self.height_box)

    def move_step(self):
        if self.moving:
            self.x_pos += 8
            if self.x_pos > self.parent().width() - self.width_box:
                self.x_pos = self.parent().width() - self.width_box
                self.moving = False
                self.finished = True
                self.timer.stop()
                self.setParent(None)
            else:
                self.move(self.x_pos, self.y_pos)

    def start(self):
        self.timer.start(20)

    def stop(self):
        self.timer.stop()

    def pause(self):
        self.moving = False

    def resume(self):
        if not self.finished:
            self.moving = True
            self.timer.start(20)

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter
        p = QPainter(self)
        p.setBrush(self.color)
        p.setPen(self.color) 
        p.drawRect(0, 0, self.width_box, self.height_box)

# ------------------------------ Worker class for console logic ------------------------------ 
class SortingWorker(QThread):
    spawn_box_signal = pyqtSignal(str)
    pause_signal = pyqtSignal()
    resume_signal = pyqtSignal()

    def __init__(self, pace, bin_count, error_rate, color_options, pace_map):
        super().__init__()
        self.pace = pace
        self.bin_count = bin_count
        self.error_rate = error_rate
        self.color_options = color_options
        self.pace_map = pace_map
        self._running = True
        self._paused = False
        self.total_items = 0
        self.correct_items = 0
        self.error_items = 0

    def run(self):
        print(f"\nStarting Sorting Task\n")
        self.start_time = time.time()
        for box_num in range(1, 101):
            if not self._running:
                break

            current_box = random.choice(self.color_options)
            print(f"[Box {box_num}] New box spawned: {current_box.upper()}")
            self.total_items += 1

            # Default final bin is the current box color
            final_bin = current_box

            # Handle error
            if self.error_rate > 0 and random.random() < self.error_rate:
                wrong_bin = random.choice([c for c in self.color_options if c != current_box])
                print(f"\nERROR: Sent to {wrong_bin.upper()} bin instead of {current_box.upper()}!")
                self.error_items += 1

                # Pause GUI
                self.pause_signal.emit()
                corrected_bin = input(
                    f"\nCorrect the {current_box.upper()} box. Where should it go? Options: {', '.join(self.color_options)}\n> "
                ).strip().lower()

                final_bin = corrected_bin  # Observer choice is final bin
                if corrected_bin == current_box:
                    print(f"\nCorrected! Box placed in {corrected_bin.upper()} bin.\n")
                else:
                    print(f"\nWrong correction. Box placed in {corrected_bin.upper()} bin anyway.\n")

                # Resume GUI
                self.resume_signal.emit()
            else:
                print(f"Box placed in {current_box.upper()} bin.")

            # Increment correct_items only if final bin matches the original box color
            if final_bin == current_box:
                self.correct_items += 1

            # Spawn the box back to the GUI
            self.spawn_box_signal.emit(current_box)

            # Delay according to pace
            delay_range = self.pace_map[self.pace]
            time.sleep(random.uniform(*delay_range))

        self._print_metrics()

    def _print_metrics(self):
        elapsed_time = time.time() - self.start_time
        accuracy = (self.correct_items / self.total_items) * 100 if self.total_items else 0
        items_per_minute = (self.total_items / elapsed_time) * 60 if elapsed_time else 0
        observed_error_rate = (self.error_items / self.total_items) * 100 if self.total_items else 0

        print("\nSESSION SORTING METRICS")
        print(f"Total items sorted:  {self.total_items}")
        print(f"Correctly sorted:    {self.correct_items}")
        print(f"Errors made by robot:{self.error_items}")
        print(f"Overall Accuracy:    {accuracy:.2f}%")
        print(f"Items per minute:    {items_per_minute:.2f}")
        print(f"Observed error rate: {observed_error_rate:.2f}%")

    def stop(self):
        self._running = False

# ------------------------------ Sorting Task GUI ------------------------------ 
class SortingTask(BaseTask):
    COLOR_MAP = {"red": QColor("red"), "blue": QColor("blue"), "green": QColor("green")}

    def __init__(self):
        super().__init__(task_name="Sorting")

        # ---- Robot arm visuals ----
        self.arm.shoulder_angle = -95
        self.arm.elbow_angle = -5
        self.arm.c_arm = QColor("#3f88ff")
        self.arm.c_arm_dark = QColor("#2f6cc9")

        # ---- Containers: Blue (middle) uses the built-in self.container ----
        # Blue (middle)
        self.container.border = QColor("#2b4a91")
        self.container.fill_top = QColor("#dbe8ff")
        self.container.fill_bottom = QColor("#c7daff")
        self.container.rib = QColor(43, 74, 145, 120)

        # Red (left)
        self.container_left = StorageContainerWidget()
        self.container_left.border = QColor("#8c1f15")
        self.container_left.fill_top = QColor("#ffd6d1")
        self.container_left.fill_bottom = QColor("#ffb8b0")
        self.container_left.rib = QColor(140, 31, 21, 120)

        # Green (right)
        self.container_right = StorageContainerWidget()
        self.container_right.border = QColor("#1f7a3a")
        self.container_right.fill_top = QColor("#d9f7e6")
        self.container_right.fill_bottom = QColor("#bff0d3")
        self.container_right.rib = QColor(31, 122, 58, 120)

        # ---- Layout: Conveyor (row 0), Arm (row 1, spanning 3 cols),
        #              Three containers (row 3: red, blue, green) ----
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=3, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=3, align=Qt.AlignHCenter | Qt.AlignBottom),
            container=dict(row=3, col=1, align=Qt.AlignHCenter | Qt.AlignTop),  # Blue in the middle
            col_stretch=[1, 1, 1],
            row_stretch=[0, 0, 1],
            spacing=18
        )
        
        # Add Red (left) and Green (right) on the same row under the arm
        self.grid.addWidget(self.container_left,  3, 0, 1, 1, Qt.AlignLeft  | Qt.AlignTop)
        self.grid.addWidget(self.container_right, 3, 2, 1, 1, Qt.AlignRight | Qt.AlignTop)

        # Bin labels
        self.label_left = QLabel("Red: 0")
        self.label_middle = QLabel("Blue: 0")
        self.label_right = QLabel("Green: 0")
        self.counts = {"red":0,"blue":0,"green":0}
        self.grid.addWidget(self.label_left, 2,0, alignment=Qt.AlignHCenter)
        self.grid.addWidget(self.label_middle,2,1, alignment=Qt.AlignHCenter)
        self.grid.addWidget(self.label_right,2,2, alignment=Qt.AlignHCenter)

        #  Robot arm auto-rotation ------------------------------------- THIS WILL BE REMOVED - ITS JUST FOR NOW
        self.arm_timer = QTimer()
        self.arm_timer.timeout.connect(self.rotate_arm)
        self.arm_rotation_speed = 25
        self.arm_rotating_forward = True

        # Boxes list 
        self.boxes = []

        # Worker parameters
        self.pace = "medium"
        self.bin_count = 3
        self.error_rate = 0.1
        self.color_options = ["red","blue","green"]
        self.pace_map = {"slow":(8,10),"medium":(4,6),"fast":(1,3)}
        self.worker = None

        # Repaint
        self.arm.update()
        self.conveyor.update()
        self.container_left.update()
        self.container.update()
        self.container_right.update()

    # ------------------------------ Robot arm movement ------------------------------
    def rotate_arm(self):
        if self.arm_rotating_forward:
            if self.arm.shoulder_angle < 85:
                self.arm.shoulder_angle += self.arm_rotation_speed
            else:
                self.arm_rotating_forward = False
        else:
            if self.arm.shoulder_angle > -95:
                self.arm.shoulder_angle -= self.arm_rotation_speed
            else:
                self.arm_rotating_forward = True
        self.arm.update()

    # ------------------------------ Spawn box and update labels ------------------------------
    def spawn_box_gui(self, color_name):
        color = self.COLOR_MAP[color_name]
        box = BoxWidget(self.conveyor, width=20, height=20, color=color)
        box.show()
        box.start()
        self.boxes.append(box)
        # Update bin counts after final bin is decided
        self.counts[color_name] += 1
        self.update_labels()

    def update_labels(self):
        self.label_left.setText(f"Red: {self.counts['red']}")
        self.label_middle.setText(f"Blue: {self.counts['blue']}")
        self.label_right.setText(f"Green: {self.counts['green']}")

    # -------------------- Pause / resume / Start / Stop / Reset Counts --------------------
    def pause_task(self):
        self.arm_timer.stop()
        for box in self.boxes:
            box.pause()

    def resume_task(self):
        self.arm_timer.start(100)
        for box in self.boxes:
            box.resume()

    def start(self):
        self.arm_timer.start(100)
        if self.worker is None or not self.worker.isRunning():
            self.worker = SortingWorker(
                self.pace,
                self.bin_count,
                self.error_rate,
                self.color_options,
                self.pace_map
            )
            self.worker.spawn_box_signal.connect(self.spawn_box_gui)
            self.worker.pause_signal.connect(self.pause_task)
            self.worker.resume_signal.connect(self.resume_task)
            self.worker.start()

    def stop(self):
        # Stop arm rotation
        self.arm_timer.stop()

        # Stop the worker thread
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        # Remove all boxes from conveyor
        for box in self.boxes:
            box.stop()
            box.setParent(None)
        self.boxes.clear()

        # Reset counts
        self.reset_counts()

    def reset_counts(self):
        # Reset bin counts to 0 and update labels
        for key in self.counts:
            self.counts[key] = 0
        self.update_labels()
