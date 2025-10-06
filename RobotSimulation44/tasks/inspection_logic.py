# tasks/inspection_logic.py
import random, time
from PyQt5.QtCore import QThread, pyqtSignal

class InspectionWorker(QThread):
    # Signals to GUI
    box_spawned = pyqtSignal(dict)      # {"color": "green"|"red", "error": False}
    box_sorted  = pyqtSignal(str, bool) # (Color, correct?)
    metrics_ready = pyqtSignal(dict)    # Final summary
    metrics_live  = pyqtSignal(dict)    # Live metrics

    def __init__(self, pace="slow", error_rate=None, error_rate_percent=None):
        super().__init__()
        self.pace = pace               # "slow", "medium", "fast"
        self.error_rate_prob = self._normalize_error_rate(error_rate, error_rate_percent)
        self.running = True

        self.colors = ["green", "red"]  # Two bins for inspection

        # Pace mapping for delays
        self.pace_map = {
            "slow":   (0.1, 0.3),
            "medium": (0.3, 0.7),
            "fast":   (0.7, 1.0)
        }

        # Counters
        self.total = 0
        self.correct = 0
        self.errors = 0
        self.total_elapsed = 0.0
        self.start_time = None
        self.spawned_boxes = []

    # Update error rate using percent (0..100)
    def set_error_rate_percent(self, percent: float):
        self.error_rate_prob = self._to_prob(percent)

    # Update error rate live (0..1 probability, N>1 treated as percent, or "N%")
    def set_error_rate(self, val):
        self.error_rate_prob = self._to_prob(val)

    # Main loop for spawning boxes
    def run(self):
        self.start_time = time.time()
        while self.running:
            color = random.choice(self.colors)
            box_data = {"color": color, "error": False}
            self.spawned_boxes.append(box_data)
            self.box_spawned.emit(box_data)

            # Delay based on pace
            products_per_sec = random.uniform(*self.pace_map.get(self.pace, self.pace_map["slow"]))
            delay = 1.0 / products_per_sec
            time.sleep(delay)

        # Emit final metrics
        elapsed = time.time() - self.start_time
        self.total_elapsed += elapsed
        self.metrics_ready.emit({
            "insp_total": self.total,
            "insp_errors": self.errors,
            "insp_error_rate": (self.errors / self.total) * 100 if self.total else 0
        })

    # Stop thread when complete
    def complete(self):
        self.running = False

    # Stop thread when stopped
    def stop(self):
        self.running = False

    # Handle box sorted by robotic arm
    def sort_box(self, box_color: str):
        """
        For inspection, 'correct' means placing the item into the bin matching its color:
        - green -> green bin
        - red   -> red bin
        Error is injected per error_rate_prob.
        """
        # Determine if error occurs
        is_error = random.random() < self.error_rate_prob

        if is_error:
            self.errors += 1
            # Count missed defects for red (incorrect) boxes
            if box_color == "red":
                self.defects_missed = getattr(self, "defects_missed", 0) + 1
            self.box_sorted.emit(box_color, False)
        else:
            self.correct += 1
            self.box_sorted.emit(box_color, True)

        self.total += 1

        # Remove first spawned box matching color
        for b in self.spawned_boxes:
            if b["color"] == box_color:
                self.spawned_boxes.remove(b)
                break

        # Emit live metrics
        now = time.time()
        elapsed = max(now - getattr(self, 'start_time', now), 1e-6)
        self.metrics_live.emit({
            "insp_total": self.total,
            "insp_errors": self.errors,
            "insp_error_rate": (self.errors / self.total) * 100 if self.total else 0
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

        # Handle string input
        if isinstance(val, str):
            s = val.strip()
            if s.endswith('%'):
                try:
                    return self._clamp(float(s[:-1]) / 100.0, 0.0, 1.0)
                except ValueError:
                    return 0.0
            try:
                f = float(s)
                return self._clamp(f / 100.0 if f > 1.0 else f, 0.0, 1.0)
            except ValueError:
                return 0.0

        # Handle numeric input
        try:
            f = float(val)
        except Exception:
            return 0.0

        return self._clamp(f / 100.0 if f > 1.0 else f, 0.0, 1.0)

    # Clamp value to [lo, hi]
    @staticmethod
    def _clamp(x, lo, hi):
        return lo if x < lo else hi if x > hi else x
