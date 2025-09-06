# tasks/inspection_logic.py
import random, time
from PyQt5.QtCore import QThread, pyqtSignal

class InspectionWorker(QThread):
    # signals to GUI
    box_spawned = pyqtSignal(dict)      # {"color": "green"|"red", "error": False (spawn-level placeholder)}
    box_sorted  = pyqtSignal(str, bool) # (color, correct?)
    metrics_ready = pyqtSignal(dict)    # summary at end
    metrics_live  = pyqtSignal(dict)    # live updated metrics

    def __init__(self, pace="slow", error_rate=None, error_rate_percent=None):
        """
        error_rate_percent: 0..100 (e.g., 10 means 10%)
        error_rate:         0..1 probability (e.g., 0.1 means 10%)
                            If you pass a number > 1 (e.g., 10), it is treated as percent.
                            Strings like '10%' also work.
        """
        super().__init__()
        self.pace = pace               # "slow", "medium", "fast"
        self.error_rate_prob = self._normalize_error_rate(error_rate, error_rate_percent)
        self.running = True

        self.colors = ["green", "red"]   # only two bins for inspection
        
        self.pace_map = {
            "slow":   (0.1, 0.3),
            "medium": (0.3, 0.7),
            "fast":   (0.7, 1.0)
        }

        self.total = 0
        self.correct = 0
        self.errors = 0
        self.total_elapsed = 0.0
        self.start_time = None
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
        self.start_time = time.time()
        while self.running:
            color = random.choice(self.colors)
            box_data = {"color": color, "error": False}
            self.spawned_boxes.append(box_data)
            self.box_spawned.emit(box_data)

            # delay based on pace
            products_per_sec = random.uniform(*self.pace_map.get(self.pace, self.pace_map["slow"]))
            delay = 1.0 / products_per_sec
            time.sleep(delay)

        # final metrics
        elapsed = time.time() - self.start_time
        self.total_elapsed += elapsed
        self.metrics_ready.emit({
            "insp_total": self.total,
            "insp_accuracy": (self.correct / self.total) * 100 if self.total else 0,
            "insp_efficiency": (self.correct / self.total) * 100 if self.total else 0,
            "insp_throughput": self.total / elapsed if elapsed > 0 else 0,
            "insp_defects_missed": getattr(self, "defects_missed", 0),
            "insp_error_rate": (self.errors / self.total) * 100 if self.total else 0,
            "insp_items_per_min": (self.total / elapsed) * 60 if elapsed > 0 else 0,
            "error_rate_config_percent": round(self.error_rate_prob * 100, 2)
        })

    def pause(self):
        self.running = False

    def stop(self):
        self.running = False

    # --- sort box when arm touches it ---
    def sort_box(self, box_color: str):
        """
        For inspection, 'correct' means placing the item into the bin matching its color:
        - green -> green bin
        - red   -> red bin
        Error is injected per error_rate_prob.
        """
        is_error = random.random() < self.error_rate_prob

        # Track errors
        if is_error:
            self.errors += 1

            # New: count only red boxes put in green as defects missed
            if box_color == "red":
                self.defects_missed = getattr(self, "defects_missed", 0) + 1

            self.box_sorted.emit(box_color, False)
        else:
            self.correct += 1
            self.box_sorted.emit(box_color, True)

        self.total += 1

        # remove one spawned box (first matching color)
        for b in self.spawned_boxes:
            if b["color"] == box_color:
                self.spawned_boxes.remove(b)
                break

        # emit live metrics exactly like SortingWorker
        now = time.time()
        elapsed = max(now - getattr(self, 'start_time', now), 1e-6)
        self.metrics_live.emit({
            "insp_total": self.total,
            "insp_accuracy": (self.correct / self.total) * 100 if self.total else 0,
            "insp_efficiency": (self.correct / self.total) * 100 if self.total else 0,
            "insp_throughput": self.total / elapsed,
            "insp_defects_missed": getattr(self, "defects_missed", 0),
            "insp_error_rate": (self.errors / self.total) * 100 if self.total else 0,
            "insp_items_per_min": (self.total / elapsed) * 60,
            "error_rate_config_percent": round(self.error_rate_prob * 100, 2)
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

        try:
            f = float(val)
        except Exception:
            return 0.0

        return self._clamp(f / 100.0 if f > 1.0 else f, 0.0, 1.0)

    @staticmethod
    def _clamp(x, lo, hi):
        return lo if x < lo else hi if x > hi else x
