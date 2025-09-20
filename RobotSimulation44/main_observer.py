# main_observer.py
import sys, os
from PyQt5.QtWidgets import QApplication
from main_interface.unified_interface import ObserverSystemWindow
from main_interface.task_manager import TaskManager
from network.server import Server
from event_logger import get_logger


def main():
    app = QApplication(sys.argv)

    # Shared task manager (used for metrics on observer side only)
    task_manager = TaskManager()

    # Start server
    server = Server(port=5000)
    server.start()

    # Create Observer window
    observer_window = ObserverSystemWindow(task_manager, server=server)

    # --- Hook ObserverControl signals to network ---
    oc = observer_window.observer_control

    # When checkboxes change -> tell User to update workspace
    oc.tasks_changed.connect(
        lambda active: server.send({"command": "update_active", "active": active})
    )

    # Start button
    oc.start_pressed.connect(
        lambda: server.send({
            "command": "start",
            "params": {
                "sorting": oc.get_params_for_task("sorting"),
                "packaging": oc.get_params_for_task("packaging"),
                "inspection": oc.get_params_for_task("inspection"),
                "sounds": oc.get_sounds_enabled(),
                "active": oc.get_active_tasks()
            }
        })
    )

    # Complete button (or timer expiry)
    def complete_handler():
        server.send({"command": "complete"})
        # Dump metrics to CSV when completing
        path = get_logger().dump_csv()
        if path:
            print(f"[Observer] Metrics saved to {path}")
            observer_window.log_button.setText(f"Log saved to {os.path.dirname(path)}")

    oc.complete_pressed.connect(complete_handler)

    # Stop button
    def stop_handler():
        server.send({"command": "stop"})
        # Dump metrics to CSV when stopping
        path = get_logger().dump_csv()
        if path:
            print(f"[Observer] Metrics saved to {path}")
            observer_window.log_button.setText(f"Log saved to {os.path.dirname(path)}")

    oc.stop_pressed.connect(stop_handler)

    # --- Handle incoming metrics from User ---
    def handle_message(msg):
        if msg.get("command") == "metrics":
            data = msg.get("data", {})
            observer_window.metrics_manager.update_metrics(data)

            # Log metrics centrally on Observer
            ts = oc.get_timestamp()
            logger = get_logger()
            for key, value in data.items():
                # Use task prefix convention if present (e.g., sort_total, pack_errors, insp_corrections)
                if key.startswith("sort_"):
                    task = "sorting"
                elif key.startswith("pack_"):
                    task = "packaging"
                elif key.startswith("insp_"):
                    task = "inspection"
                else:
                    task = "general"
                logger.log_metric(ts, task, key, value)

    server.on_message = handle_message

    observer_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
