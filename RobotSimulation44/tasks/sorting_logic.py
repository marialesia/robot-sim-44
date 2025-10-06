# tasks/sorting_logic.py
import random, time
from PyQt5.QtCore import QThread, pyqtSignal


class SortingWorker(QThread):
    # signals to GUI
    box_spawned = pyqtSignal(dict)      # Box color + error placeholder
    box_sorted = pyqtSignal(str, bool)  # (color, correct?)
    metrics_ready = pyqtSignal(dict)    # Final summary
    metrics_live = pyqtSignal(dict)     # Live updated metrics

    def __init__(self, pace, bin_count, error_rate=None, error_rate_percent=None):
        super().__init__()
        self.pace = pace               # "slow", "medium", "fast"
        self.bin_count = bin_count     # 2, 4, or 6 bins

        # Normalize to a probability in [0,1]
        self.error_rate_prob = self._normalize_error_rate(error_rate, error_rate_percent)

        self.running = True

        # Determine colors for bins
        if bin_count == 6:
            self.colors = ["red", "blue", "green", "purple", "orange", "teal"]
        elif bin_count == 4:
            self.colors = ["blue", "green", "purple", "orange"]
        elif bin_count == 2:
            self.colors = ["green", "purple"]
        else:
            # Fallback
            self.colors = ["red", "blue", "green", "purple", "orange", "teal"]

        # Pace mapping for random delays
        self.pace_map = {
            "slow": (0.1, 0.3),
            "medium": (0.3, 0.7),
            "fast": (0.7, 1.0)
        }

        # Counters
        self.total = 0
        self.correct = 0
        self.errors = 0
        self.total_elapsed = 0.0  # Accumulate elapsed time

        # Store spawned boxes
        self.spawned_boxes = []

    # Update error rate using percent (0..100)
    def set_error_rate_percent(self, percent: float):
        self.error_rate_prob = self._to_prob(percent)

    # Update error rate live (0..1 prob, N>1 treated as percent, or "N%")
    def set_error_rate(self, val):
        self.error_rate_prob = self._to_prob(val)

    # Main thread loop for spawning boxes
    def run(self):
        self.start_time = time.time()   # store start time
        while self.running:
            # spawn a random box
            color = random.choice(self.colors)
            box_data = {"color": color, "error": False}
            self.spawned_boxes.append(box_data)
            self.box_spawned.emit(box_data)

            # delay based on pace
            products_per_sec = random.uniform(*self.pace_map[self.pace])
            delay = 1.0 / products_per_sec
            time.sleep(delay)

        # Emit final metrics
        elapsed = time.time() - self.start_time
        self.total_elapsed += elapsed
        self.metrics_ready.emit({
            "sort_total": self.total,
            "sort_errors": self.errors,
            "sort_error_rate": (self.errors / self.total) * 100 if self.total else 0
        })

    # Stop thread when complete
    def complete(self):
        self.running = False

    # Stop thread when stopped
    def stop(self):
        self.running = False

    # Handle box sorted by robotic arm
    def sort_box(self, box_color):
        # Determine if error occurs
        is_error = random.random() < self.error_rate_prob
        if is_error:
            self.errors += 1
            self.box_sorted.emit(box_color, False)
        else:
            self.correct += 1
            self.box_sorted.emit(box_color, True)
        self.total += 1

        # Remove box from spawned list
        for b in self.spawned_boxes:
            if b["color"] == box_color:
                self.spawned_boxes.remove(b)
                break

        elapsed = max(time.time() - getattr(self, 'start_time', time.time()), 1)

        # Emit live metrics
        self.metrics_live.emit({
            "sort_total": self.total,
            "sort_errors": self.errors,
            "sort_error_rate": (self.errors / self.total) * 100 if self.total else 0
        })

    # Determine probability from error_rate or error_rate_percent
    def _normalize_error_rate(self, error_rate, error_rate_percent):
        if error_rate_percent is not None:
            return self._to_prob(error_rate_percent)
        if error_rate is not None:
            return self._to_prob(error_rate)
        return 0.0

    # Convert various forms to 0..1 probability
    def _to_prob(self, val):
        """
        Normalize different forms to a probability in [0,1]:
        - numbers <=1 treated as probability
        - numbers >1 treated as percent (divide by 100)
        - strings like '10%' parsed as percent
        """
        if val is None:
            return 0.0

        # String input (e.g., "10%")
        if isinstance(val, str):
            s = val.strip()
            if s.endswith('%'):
                try:
                    return self._clamp(float(s[:-1]) / 100.0, 0.0, 1.0)
                except ValueError:
                    return 0.0
            # Plain number in a string
            try:
                f = float(s)
                return self._clamp(f / 100.0 if f > 1.0 else f, 0.0, 1.0)
            except ValueError:
                return 0.0

        # Numeric input
        try:
            f = float(val)
        except Exception:
            return 0.0

        return self._clamp(f / 100.0 if f > 1.0 else f, 0.0, 1.0)

    # Clamp value to [lo, hi]
    @staticmethod
    def _clamp(x, lo, hi):
        return lo if x < lo else hi if x > hi else x
