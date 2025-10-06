# event_logger.py
import os, sys, csv, threading
from datetime import datetime

# Return base directory for logs (works in dev and PyInstaller)
def _base_dir():
    if getattr(sys, "frozen", False):  # Running from .exe
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")

class EventLogger:
    def __init__(self):
        # Store log rows in memory
        self._rows = []
        self._lock = threading.Lock()

    # Add a row thread-safely
    def _add(self, row):
        with self._lock:
            self._rows.append(row)

    # Log a single metric update
    def log_metric(self, timestamp, task, metric, count):
        self._add({
            "timestamp": timestamp,
            "task": task,
            "metric": metric,
            "count": count
        })

    # Dump all logged rows to a CSV file
    def dump_csv(self, path=None):
        with self._lock:
            if not self._rows:
                return None
            rows = list(self._rows)
            self._rows.clear()

        # Determine path if not given
        if path is None:
            log_dir = os.path.join(_base_dir(), "logs")
            os.makedirs(log_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(log_dir, f"session_{ts}.csv")

        # Write CSV file
        fieldnames = ["timestamp", "task", "metric", "count"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

        return path


# Singleton logger instance
__singleton = None
def get_logger():
    global __singleton
    if __singleton is None:
        __singleton = EventLogger()
    return __singleton
