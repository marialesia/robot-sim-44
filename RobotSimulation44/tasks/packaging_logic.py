# tasks/packaging_logic.py
import time, random
from PyQt5.QtCore import QThread, pyqtSignal


class PackagingWorker(QThread):
    """
    Background 'brain' for the Packaging task.
    - Spawns boxes at a configurable pace.
    - Optionally flags some spawns as 'error' (mis-packed/defective) via error_rate.
    - Emits simple metrics on shutdown.
    """
    box_spawned = pyqtSignal(dict)   # {"color": <str>, "error": <bool>}
    metrics_ready = pyqtSignal(dict) # {"total": int, "errors": int, "accuracy": float, "items_per_min": float}

    def __init__(self, pace="slow", color="orange", error_rate=0.0):
        super().__init__()
        self.pace = pace
        self.color = color
        self.error_rate = float(error_rate)
        self.running = True

        # Items per second ranges
        self.pace_map = {
            "slow":   (0.3, 0.6),
            "medium": (0.7, 1.2),
            "fast":   (1.3, 2.0),
        }

        self.total = 0
        self.errors = 0

    def run(self):
        start = time.time()
        lo, hi = self.pace_map.get(self.pace, (0.5, 1.0))

        while self.running:
            is_error = (random.random() < self.error_rate)
            self.total += 1
            if is_error:
                self.errors += 1

            self.box_spawned.emit({"color": self.color, "error": is_error})

            # Variable cadence for a more natural feel
            rate = max(1e-6, random.uniform(lo, hi))   # items per second
            time.sleep(1.0 / rate)

        elapsed = max(1e-6, time.time() - start)
        spawn_rate_avg = self.total / elapsed
        accuracy = ((self.total - self.errors) / self.total * 100.0) if self.total else 0.0

        self.metrics_ready.emit({
            "total": self.total,
            "errors": self.errors,
            "accuracy": accuracy,
            "items_per_min": spawn_rate_avg * 60.0,
        })

    def stop(self):
        self.running = False
