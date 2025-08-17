# tasks/sorting_task.py
#from .base_task import BaseTask

#class SortingTask(BaseTask):
#    def __init__(self):
#        super().__init__(task_name="Sorting")

# tasks/sorting_task.py
import random
import time
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import QThread, pyqtSignal
from .base_task import BaseTask

# Worker class to run the sorting logic in a separate thread
class SortingWorker(QThread):
    metrics_ready = pyqtSignal(dict)

    def __init__(self, pace, bin_count, error_rate, color_options, pace_map, num_boxes=10):
        super().__init__()
        self.pace = pace
        self.bin_count = bin_count
        self.error_rate = error_rate
        self.color_options = color_options
        self.pace_map = pace_map
        self.num_boxes = num_boxes #this is for debugging
        self._running = True

        # Metrics
        self.total_items = 0
        self.correct_items = 0
        self.error_items = 0

    def run(self):
        print(f"Starting Sorting Task ({self.num_boxes} boxes)...")
        self.start_time = time.time()

        for box_num in range(1, self.num_boxes + 1):
            if not self._running:
                break

            current_box = random.choice(self.color_options)
            print(f"[Box {box_num}] New box spawned: {current_box.upper()}")
            self.total_items += 1

            if random.random() < self.error_rate:
                wrong_bin = random.choice([c for c in self.color_options if c != current_box])
                print(f"ERROR: Sent to {wrong_bin.upper()} bin instead of {current_box.upper()}!")
                self.error_items += 1

                corrected_bin = input(
                    f"Where should this {current_box.upper()} box go? Options: {', '.join(self.color_options)}\n> "
                ).strip().lower()
                if corrected_bin == current_box:
                    print(f"Corrected! Box placed in {corrected_bin.upper()} bin.")
                    self.correct_items += 1
                else:
                    print(f"Wrong correction.")
            else:
                print(f"Box placed in {current_box.upper()} bin.")
                self.correct_items += 1

            delay_range = self.pace_map[self.pace]
            time.sleep(random.uniform(*delay_range))

        self._print_metrics()

    def _print_metrics(self):
        elapsed_time = time.time() - self.start_time
        accuracy = (self.correct_items / self.total_items) * 100 if self.total_items > 0 else 0
        items_per_minute = (self.total_items / elapsed_time) * 60 if elapsed_time > 0 else 0
        observed_error_rate = (self.error_items / self.total_items) * 100 if self.total_items > 0 else 0

        print("\nSORTING METRICS")
        print(f"Total items sorted: {self.total_items}")
        print(f"Correctly sorted:   {self.correct_items}")
        print(f"Errors made:        {self.error_items}")
        print(f"Accuracy:           {accuracy:.2f}%")
        print(f"Items per minute:   {items_per_minute:.2f}")
        print(f"Observed error rate:{observed_error_rate:.2f}%")

    def stop(self):
        self._running = False


class SortingTask(BaseTask, QWidget):
    def __init__(self):
        BaseTask.__init__(self, task_name="Sorting")
        QWidget.__init__(self)

        # Parameters
        self.pace = "medium"
        self.bin_count = 3
        self.error_rate = 0.1
        self.color_options = ["red", "blue", "green"] if self.bin_count == 3 else ["red", "blue"]
        self.pace_map = {
            "slow": (8, 10),
            "medium": (4, 6),
            "fast": (1, 3)
        }

        # Simple placeholder UI (can be expanded later)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Sorting Task (Console Simulation)"))

        self.worker = None

    def start(self):
        """Start the sorting logic in a separate thread."""
        if self.worker is None or not self.worker.isRunning():
            self.worker = SortingWorker(
                self.pace,
                self.bin_count,
                self.error_rate,
                self.color_options,
                self.pace_map,
                num_boxes=10 #this is for debugging
            )
            self.worker.start()

    def stop(self):
        """Stop the sorting logic."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
