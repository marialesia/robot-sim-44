# tasks/packaging_logic.py
import time, random
from PyQt5.QtCore import QThread, pyqtSignal


class PackagingWorker(QThread):
    """
    Background 'brain' for the Packaging task.
    - Spawns boxes at a configurable pace.
    - Optionally flags some spawns as 'error' via error_rate (not used by UI yet).
    - Tracks the 'current container being filled' when the UI tells it an item was packed.
    """
    # Spawner side (already used by your PackagingTask)
    box_spawned = pyqtSignal(dict)     # {"color": <str>, "error": <bool>}
    metrics_ready = pyqtSignal(dict)   # {"total": int, "errors": int, "accuracy": float, "items_per_min": float}

    # New: notify when a container is filled (capacity, seconds_to_fill)
    container_filled = pyqtSignal(int, float)

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

        # Spawner metrics
        self.total = 0
        self.errors = 0

        # ---- New: Fill-tracker (kept simple & thread-safe enough for this use) ----
        self._cur_capacity = 0
        self._cur_count = 0
        self._cur_start_ts = None

    # ---------- Spawner thread ----------
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

    # ---------- UI-agnostic helpers that can be called from the UI thread ----------
    @staticmethod
    def pick_capacity():
        """Single source of truth for container capacity policy."""
        return random.choice((4, 5, 6))

    def begin_container(self, capacity: int):
        """Call this when the LEFTMOST/active container changes to a fresh one."""
        self._cur_capacity = int(capacity)
        self._cur_count = 0
        self._cur_start_ts = time.time()

    def record_pack(self) -> bool:
        """
        Call this each time the UI has 'packed' one item into the active container.
        Returns True when the container just became full and emits container_filled.
        """
        if self._cur_capacity <= 0:
            return False
        self._cur_count += 1
        if self._cur_count >= self._cur_capacity:
            secs = 0.0
            if self._cur_start_ts is not None:
                secs = max(0.0, time.time() - self._cur_start_ts)
            cap = self._cur_capacity
            # Reset so a new begin_container() can start a new cycle
            self._cur_capacity = 0
            self._cur_count = 0
            self._cur_start_ts = None
            self.container_filled.emit(cap, secs)
            return True
        return False
