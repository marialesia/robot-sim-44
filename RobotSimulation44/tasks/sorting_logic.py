# tasks/sorting_logic.py
import random, time
from PyQt5.QtCore import QThread, pyqtSignal


class SortingWorker(QThread):
    # signals to GUI
    box_spawned = pyqtSignal(dict)      # box color + error placeholder
    box_sorted = pyqtSignal(str, bool)  # (color, correct?)
    metrics_ready = pyqtSignal(dict)    # summary at end
    metrics_live = pyqtSignal(dict)     # live updated metrics

    def __init__(self, pace, bin_count, error_rate=None, error_rate_percent=None):
        """
        error_rate_percent: 0..100 (e.g., 10 means 10%)
        error_rate:         0..1 probability (e.g., 0.1 means 10%)
                            If you pass a number > 1 (e.g., 10), it is treated as percent.
                            Strings like '10%' also work.
        """
        super().__init__()
        self.pace = pace               # "slow", "medium", "fast"
        self.bin_count = bin_count     # 2, 4, or 6 bins

        # normalize to a probability in [0,1]
        self.error_rate_prob = self._normalize_error_rate(error_rate, error_rate_percent)

        self.running = True

        if bin_count == 6:
            self.colors = ["red", "blue", "green", "purple", "orange", "teal"]
        elif bin_count == 4:
            self.colors = ["blue", "green", "purple", "orange"]
        elif bin_count == 2:
            self.colors = ["green", "purple"]
        else:
            # fallback (shouldn�t really happen)
            self.colors = ["red", "blue", "green", "purple", "orange", "teal"]


        self.pace_map = {
            "slow": (0.1, 0.3),
            "medium": (0.3, 0.7),
            "fast": (0.7, 1.0)
        }

        self.total = 0
        self.correct = 0
        self.errors = 0

        self.total_elapsed = 0.0  # accumulate across pauses

        # store spawned boxes
        self.spawned_boxes = []

    # ------------------------ public helpers ------------------------

    def set_error_rate_percent(self, percent: float):
        """Update error rate live using a percent (0..100)."""
        self.error_rate_prob = self._to_prob(percent)

    def set_error_rate(self, val):
        """Update error rate live; accepts 0..1 probability, N>1 as percent, or 'N%'."""
        self.error_rate_prob = self._to_prob(val)

    # ------------------------ thread loop ---------------------------

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

        # final metrics
        elapsed = time.time() - self.start_time
        self.total_elapsed += elapsed
        self.metrics_ready.emit({
            "sort_total": self.total,
            "sort_errors": self.errors,
            "sort_error_rate": (self.errors / self.total) * 100 if self.total else 0
        })

    def pause(self):
        self.running = False

    def stop(self):
        self.running = False

    # --- sort box when arm touches it ---
    def sort_box(self, box_color):
        is_error = random.random() < self.error_rate_prob
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

        elapsed = max(time.time() - getattr(self, 'start_time', time.time()), 1)

        # emit live metrics in full format
        self.metrics_live.emit({
            "sort_total": self.total,
            "sort_errors": self.errors,
            "sort_error_rate": (self.errors / self.total) * 100 if self.total else 0
        })

    # ------------------- internal normalization --------------------

    def _normalize_error_rate(self, error_rate, error_rate_percent):
        # Prefer explicit percent if provided
        if error_rate_percent is not None:
            return self._to_prob(error_rate_percent)

        # Fall back to error_rate (prob or percent-like)
        if error_rate is not None:
            return self._to_prob(error_rate)

        # default: 0%
        return 0.0

    def _to_prob(self, val):
        """
        Normalize different forms to a probability in [0,1]:
        - numbers <=1 treated as probability
        - numbers >1 treated as percent (divide by 100)
        - strings like '10%' parsed as percent
        """
        if val is None:
            return 0.0

        # string input (e.g., "10%")
        if isinstance(val, str):
            s = val.strip()
            if s.endswith('%'):
                try:
                    return self._clamp(float(s[:-1]) / 100.0, 0.0, 1.0)
                except ValueError:
                    return 0.0
            # plain number in a string
            try:
                f = float(s)
                return self._clamp(f / 100.0 if f > 1.0 else f, 0.0, 1.0)
            except ValueError:
                return 0.0

        # numeric input
        try:
            f = float(val)
        except Exception:
            return 0.0

        return self._clamp(f / 100.0 if f > 1.0 else f, 0.0, 1.0)

    @staticmethod
    def _clamp(x, lo, hi):
        return lo if x < lo else hi if x > hi else x
