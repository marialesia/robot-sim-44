# event_logger.py
import os, csv, datetime, threading

class EventLogger:
    def __init__(self):
        self._rows = []
        self._lock = threading.Lock()

    def _add(self, row):
        with self._lock:
            self._rows.append(row)

    def log_user(self, context, target, action="click", message=""):
        self._add({
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "type": "user",
            "context": context,   # e.g. "Sorting" or "TopBar"
            "target": target,     # e.g. "container_red", "Start button"
            "action": action,     # e.g. "click", "toggle"
            "message": message,   # any extra detail
        })

    def log_robot(self, context, message):
        self._add({
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "type": "robot",
            "context": context,   # e.g. "Sorting"
            "target": "",
            "action": "",
            "message": message,
        })

    def dump_csv(self, path=None):
        with self._lock:
            if not self._rows:
                return None
            rows = list(self._rows)
            self._rows.clear()

        if path is None:
            log_dir = os.path.join(os.getcwd(), "logs")
            os.makedirs(log_dir, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(log_dir, f"session_{ts}.csv")

        fieldnames = ["timestamp", "type", "context", "target", "action", "message"]
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
