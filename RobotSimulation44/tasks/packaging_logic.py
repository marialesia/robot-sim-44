# tasks/packaging_logic.py
import time, random
from PyQt5.QtCore import QThread, pyqtSignal


class PackagingWorker(QThread):
    """
    Background brain for the Packaging task.

    New behavior:
    - Spawns boxes matching the active container color most of the time.
    - With probability error_rate, spawns the wrong color (one of the other two).
    - Fade suggestion is still driven by reaching capacity, but the UI may defer
      fading if an error is present; the UI can call rearm_fade() to allow a later fade.
    """
    box_spawned = pyqtSignal(dict)      # {"color": <"red"|"blue"|"green">}
    metrics_ready = pyqtSignal(dict)    # end-of-run summary
    metrics_live = pyqtSignal(dict)     # live metrics
    container_should_fade = pyqtSignal(str, int, int, float)  # mode, count, capacity, secs

    def __init__(self, pace="slow", error_rate=0.0):
        super().__init__()
        self.pace = pace or "slow"
        self.error_rate = float(error_rate or 0.0)
        self.running = True

        self.pace_map = {
            "slow":   (0.1, 0.3),
            "medium": (0.3, 0.7),
            "fast":   (0.7, 1.0),
        }

        # metrics
        self.total = 0
        self.errors = 0
        self.correct = 0
        self.start_time = time.time()

        # per-container state
        self._cur_capacity = 0
        self._cur_count = 0
        self._cur_start_ts = None
        self._fired = False

        # color policy
        self._cur_color = "red"
        self._palette = ("red", "blue", "green")

    def run(self):
        lo, hi = self.pace_map.get(self.pace, (0.3, 0.7))
        while self.running:
            # choose color: usually the active color; sometimes wrong
            if random.random() < self.error_rate:
                others = [c for c in self._palette if c != self._cur_color]
                color = random.choice(others)
                is_error = True
            else:
                color = self._cur_color
                is_error = False

            self.box_spawned.emit({"color": color})

            # pacing
            rate = max(1e-6, random.uniform(lo, hi))  # items/sec
            time.sleep(1.0 / rate)

        # end-of-thread summary
        elapsed = max(1e-6, time.time() - self.start_time)
        self.metrics_ready.emit({
            "pack_total": self.total,
            "pack_errors": self.errors,
            "pack_error_rate": (self.errors / self.total) * 100 if self.total else 0
        })

    def stop(self):
        self.running = False

    @staticmethod
    def pick_capacity():
        return random.choice((4, 5, 6))

    def begin_container(self, capacity: int, color: str = None):
        """UI tells us a fresh leftmost container is active (and its color)."""
        self._cur_capacity = int(capacity)
        self._cur_count = 0
        self._cur_start_ts = time.time()
        self._fired = False
        if color:
            self._cur_color = str(color)

    def record_pack(self):
        """
        Called by UI each time an item is packed into the active container.
        We maintain metrics and *suggest* a fade when count reaches capacity.
        """
        self._cur_count += 1
        self.total += 1

        # We don't know the box color here; let the UI decide correctness.
        # Keep live throughput style metrics only.
        elapsed = max(time.time() - self.start_time, 1.0)
        self.metrics_live.emit({
            "pack_total": self.total,
            "pack_errors": self.errors,
            "pack_error_rate": (self.errors / self.total) * 100 if self.total else 0
        })

        # Suggest fade once per container when we reach capacity
        if not self._fired and self._cur_capacity > 0 and self._cur_count >= self._cur_capacity:
            self._fired = True
            secs = max(0.0, time.time() - (self._cur_start_ts or time.time()))
            # "mode" kept for compatibility (unused by UI logic now)
            self.container_should_fade.emit("normal", self._cur_count, self._cur_capacity, secs)

    def rearm_fade(self):
        """UI can call this if it postponed the fade (e.g., due to an error)."""
        self._fired = False
