# main_observer.py
import sys, os
from PyQt5.QtWidgets import QApplication
from main_interface.unified_interface import ObserverSystemWindow
from main_interface.task_manager import TaskManager
from network.server import Server
from event_logger import get_logger
from network.discovery import DiscoveryBroadcaster

def main():
    app = QApplication(sys.argv)

    task_manager = TaskManager()

    # Create Observer window first (so we can pass it to server callbacks)
    observer_window = ObserverSystemWindow(task_manager)
    oc = observer_window.observer_control

    # --- Handle incoming messages from User ---
    def handle_message(msg):
        if msg.get("command") == "metrics":
            data = msg.get("data", {})
            observer_window.metrics_manager.update_metrics(data)
            ts = oc.get_timestamp()
            logger = get_logger()
            for key, value in data.items():
                if key.startswith("sort_"):
                    task = "sorting"
                elif key.startswith("pack_"):
                    task = "packaging"
                elif key.startswith("insp_"):
                    task = "inspection"
                else:
                    task = "general"
                logger.log_metric(ts, task, key, value)

    # --- Connection hooks ---
    def on_client_connect(addr):
        print(f"[Observer] Connection successful: {addr}")
        oc.set_connection_status("Connection Successful", success=True)

    def on_client_disconnect():
        print("[Observer] Client disconnected")
        oc.set_connection_status("Disconnected", success=False)

    # Start server with callbacks
    server = Server(
        port=5000,
        on_message=handle_message,
        on_connect=on_client_connect,
        on_disconnect=on_client_disconnect
    )
    server.start()

    # Give Observer window access to server
    observer_window.server = server

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
        path = get_logger().dump_csv()
        if path:
            print(f"[Observer] Metrics saved to {path}")
            observer_window.log_button.setText(f"Log saved to {os.path.dirname(path)}")

    oc.complete_pressed.connect(complete_handler)

    # Stop button
    def stop_handler():
        server.send({"command": "stop"})
        path = get_logger().dump_csv()
        if path:
            print(f"[Observer] Metrics saved to {path}")
            observer_window.log_button.setText(f"Log saved to {os.path.dirname(path)}")

    oc.stop_pressed.connect(stop_handler)

    # Start UDP broadcaster
    broadcaster = DiscoveryBroadcaster(interval=2)
    broadcaster.start()

    observer_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
