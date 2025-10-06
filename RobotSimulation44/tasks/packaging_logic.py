# tasks/packaging_logic.py
import time, random
from PyQt5.QtCore import QThread, pyqtSignal

class PackagingWorker(QThread):
    """
    NOTE: Keeping bin_count and the active color palette for telemetry and any future logic
    that may need it; the UI controls exact colors via its active palette.
    """
    # Signals to GUI
    box_spawned = pyqtSignal(dict)      # {"color": <"red"|"blue"|...>}
    metrics_ready = pyqtSignal(dict)    # End-of-run summary
    metrics_live = pyqtSignal(dict)     # Live metrics
    container_should_fade = pyqtSignal(str, int, int, float)  # Mode, count, capacity, seconds

    def __init__(self, pace="slow", error_rate=0.0, bin_count=4):
        super().__init__()
        self.pace = pace or "slow"
        self.error_rate = float(error_rate or 0.0)
        self.bin_count = int(bin_count) if bin_count is not None else 4
        self.running = True

        # Set active palette based on bin count
        if self.bin_count >= 6:
            self.colors = ["red", "blue", "green", "purple", "orange", "teal"]
        elif self.bin_count == 4:
            self.colors = ["blue", "green", "purple", "orange"]
        elif self.bin_count == 2:
            self.colors = ["green", "purple"]
        else:
            self.colors = ["red", "blue", "green"][:max(1, self.bin_count)]

        # Pace mapping for delays
        self.pace_map = {
            "slow":   (0.1, 0.3),
            "medium": (0.3, 0.7),
            "fast":   (0.7, 1.0),
        }

        # Metrics
        self.total = 0
        self.errors = 0
        self.correct = 0
        self.start_time = time.time()

        # Container state
        self._cur_capacity = 0
        self._cur_count = 0
        self._cur_start_ts = None
        self._fired = False
        # Color policy
        # The UI tells us which color is active via begin_container(color=...)
        self._cur_color = "green"

    # Main thread loop
    def run(self):
        lo, hi = self.pace_map.get(self.pace, (0.3, 0.7))
        while self.running:
            # The UI drip spawns; we only exist for pacing metrics and signals
            # Emit a heartbeat with pace—this keeps telemetry flowing even if unused
            rate = max(1e-6, random.uniform(lo, hi))
            time.sleep(1.0 / rate)

        # Emit end-of-thread metrics
        elapsed = max(1e-6, time.time() - self.start_time)
        self.metrics_ready.emit({
            "pack_total": self.total,
            "pack_errors": self.errors,
            "pack_error_rate": (self.errors / self.total) * 100 if self.total else 0
        })

    # Stop thread
    def stop(self):
        self.running = False

    # Pick container capacity
    @staticmethod
    def pick_capacity(limit="4 - 6"):
        if limit == "6":
            return 6
        elif limit == "5 - 6":
            return random.choice((5, 6))
        else:  # "4 - 6"
            return random.choice((4, 5, 6))

    # Begin new container: UI tells us a fresh leftmost container is active (and its color)
    def begin_container(self, capacity: int, color: str = None):
        self._cur_capacity = int(capacity)
        self._cur_count = 0
        self._cur_start_ts = time.time()
        self._fired = False
        if color:
            self._cur_color = str(color)

    # Record a packed item
    def record_pack(self, is_error):
        """
        Called by UI each time an item is packed into the active container.
        We maintain metrics and *suggest* a fade when count reaches capacity.
        """
        self._cur_count += 1
        self.total += 1

        if is_error:
            self.errors += 1
        else:
            self.correct += 1

        # Emit live metrics
        self.metrics_live.emit({
            "pack_total": self.total,
            "pack_errors": self.errors,
            "pack_error_rate": (self.errors / self.total) * 100 if self.total else 0
        })

        # Suggest container fade when full
        if not self._fired and self._cur_capacity > 0 and self._cur_count >= self._cur_capacity:
            self._fired = True
            secs = max(0.0, time.time() - (self._cur_start_ts or time.time()))
            self.container_should_fade.emit("normal", self._cur_count, self._cur_capacity, secs)

    # Rearm fade if UI postponed it
    def rearm_fade(self):
        self._fired = False
