# tasks/packaging_logic.py
import time, random
from PyQt5.QtCore import QThread, pyqtSignal


class PackagingWorker(QThread):
    """
    Background 'brain' for the Packaging task.

    Responsibilities:
    - Spawns boxes at a configurable pace (unchanged).
    - Chooses per-container scenario based on error_rate:
        * normal   -> fade at capacity
        * underfill-> fade below capacity (e.g., 2/4)
        * overfill -> fade above capacity (e.g., 5/4)
    - Tells the UI when the current (leftmost) container should fade.
    """
    # Spawner side (already used by your PackagingTask)
    box_spawned = pyqtSignal(dict)     # {"color": <str>, "error": <bool>}
    metrics_ready = pyqtSignal(dict)   # {"total": int, "errors": int, "accuracy": float, "items_per_min": float}

    # New: UI should fade the active container NOW
    # args: mode ("normal"|"underfill"|"overfill"), count_at_trigger, capacity, seconds_elapsed
    container_should_fade = pyqtSignal(str, int, int, float)

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

        # ---- Per-container decision state (for the current LEFTMOST only) ----
        self._cur_capacity = 0
        self._cur_count = 0
        self._cur_start_ts = None

        self._mode = "normal"         # "normal" | "underfill" | "overfill"
        self._fade_trigger = 0         # count threshold to trigger fade
        self._fired = False            # ensure we signal only once per container

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

    # ---------- Container decision API (called from UI thread) ----------

    @staticmethod
    def pick_capacity():
        """Single source of truth for container capacity policy."""
        return random.choice((4, 5, 6))

    def begin_container(self, capacity: int):
        """
        Call this when the LEFTMOST active container changes to a fresh one.
        We pick a scenario for THIS container based on error_rate.
        """
        self._cur_capacity = int(capacity)
        self._cur_count = 0
        self._cur_start_ts = time.time()
        self._fired = False

        # Decide scenario
        if random.random() < self.error_rate:
            # error container: 50/50 underfill vs overfill
            if random.random() < 0.5:
                # underfill: fade at some count in [1, capacity-1]
                self._mode = "underfill"
                self._fade_trigger = max(1, random.randint(1, max(1, self._cur_capacity - 1)))
            else:
                # overfill: fade at capacity+1 or capacity+2
                self._mode = "overfill"
                self._fade_trigger = self._cur_capacity + random.randint(1, 2)
        else:
            # normal: fade exactly at capacity
            self._mode = "normal"
            self._fade_trigger = self._cur_capacity

    def record_pack(self) -> bool:
        """
        Call this each time the UI has 'packed' one item into the active container.
        Returns True when the container should fade now (also emits container_should_fade).
        """
        if self._cur_capacity <= 0:
            return False

        self._cur_count += 1

        if not self._fired and self._cur_count >= self._fade_trigger:
            self._fired = True
            secs = 0.0
            if self._cur_start_ts is not None:
                secs = max(0.0, time.time() - self._cur_start_ts)
            # Tell the UI to fade the current container NOW
            self.container_should_fade.emit(self._mode, self._cur_count, self._cur_capacity, secs)
            return True

        return False
