# event_logger.py
import os, sys, csv, threading
from datetime import datetime

def _base_dir():
    """Return base dir for logs (works in dev and PyInstaller)."""
    if getattr(sys, "frozen", False):  # Running from .exe
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")

class EventLogger:
    def __init__(self):
        self._rows = []
        self._lock = threading.Lock()

    def _add(self, row):
        with self._lock:
            self._rows.append(row)

    def log_metric(self, timestamp, task, metric, count):
        """Log a single metric update."""
        self._add({
            "timestamp": timestamp,
            "task": task,
            "metric": metric,
            "count": count
        })

    def dump_csv(self, path=None):
        """Dump current rows to a CSV file."""
        with self._lock:
            if not self._rows:
                return None
            rows = list(self._rows)
            self._rows.clear()

        if path is None:
            log_dir = os.path.join(_base_dir(), "logs")
            os.makedirs(log_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(log_dir, f"session_{ts}.csv")

        fieldnames = ["timestamp", "task", "metric", "count"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

        return path


__singleton = None
def get_logger():
    global __singleton
    if __singleton is None:
        __singleton = EventLogger()
    return __singleton
