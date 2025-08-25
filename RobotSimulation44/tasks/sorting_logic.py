# tasks/sorting_logic.py
import random, time
from PyQt5.QtCore import QThread, pyqtSignal


class SortingWorker(QThread):
    # signals to GUI
    box_spawned = pyqtSignal(dict)      # box color + error placeholder
    box_sorted = pyqtSignal(str, bool)  # (color, correct?)
    metrics_ready = pyqtSignal(dict)    # summary at end

    def __init__(self, pace, bin_count, error_rate):
        super().__init__()
        self.pace = pace               # "slow", "medium", "fast"
        self.bin_count = bin_count     # 2, 4, or 6 bins
        self.error_rate = error_rate
        self.running = True

        all_colors = ["red", "blue", "green", "purple", "orange", "teal"]
        self.colors = all_colors[:bin_count]

        self.pace_map = {
            "slow": (0.1, 0.3),
            "medium": (0.3, 0.7),
            "fast": (0.7, 1)
        }

        self.total = 0
        self.correct = 0
        self.errors = 0

        # store spawned boxes
        self.spawned_boxes = []

    def run(self):
        start_time = time.time()
        while self.running:
            # spawn a random box
            color = random.choice(self.colors)
            box_data = {"color": color, "error": False}  # error not determined yet
            self.spawned_boxes.append(box_data)
            self.box_spawned.emit(box_data)

            # delay based on pace
            products_per_sec = random.uniform(*self.pace_map[self.pace])
            delay = 1.0 / products_per_sec
            time.sleep(delay)

        elapsed = time.time() - start_time
        self.metrics_ready.emit({
            "total": self.total,
            "correct": self.correct,
            "errors": self.errors,
            "accuracy": (self.correct / self.total) * 100 if self.total else 0,
            "items_per_min": (self.total / elapsed) * 60 if elapsed > 0 else 0,
            "spawn_rate_avg": (self.total / elapsed) if elapsed > 0 else 0
        })

    def stop(self):
        self.running = False

    # --- New method: sort box when arm touches it ---
    def sort_box(self, box_color):
        is_error = random.random() < self.error_rate
        if is_error:
            self.errors += 1
            self.box_sorted.emit(box_color, False)
        else:
            self.correct += 1
            self.box_sorted.emit(box_color, True)
        self.total += 1

        # remove from spawned list
        for b in self.spawned_boxes:
            if b["color"] == box_color:
                self.spawned_boxes.remove(b)
                break