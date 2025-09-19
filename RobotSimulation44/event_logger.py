# event_logger.py
import os, csv, threading

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
            "timestamp": timestamp,   # e.g. "00:10" from ObserverControl
            "task": task,             # e.g. "sorting"
            "metric": metric,         # e.g. "boxes sorted"
            "count": count            # integer
        })

    def dump_csv(self, path=None):
        """Dump current rows to a CSV file."""
        with self._lock:
            if not self._rows:
                return None
            rows = list(self._rows)
            self._rows.clear()

        if path is None:
            log_dir = os.path.join(os.getcwd(), "logs")
            os.makedirs(log_dir, exist_ok=True)
            from datetime import datetime
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
