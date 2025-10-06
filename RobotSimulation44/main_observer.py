# main_observer.py
import sys, os
from PyQt5.QtWidgets import QApplication
from main_interface.unified_interface import ObserverSystemWindow
from main_interface.task_manager import TaskManager
from network.server import Server
from event_logger import get_logger
from network.discovery import DiscoveryBroadcaster

def main():
    # Initialize QApplication
    app = QApplication(sys.argv)

    # Create TaskManager
    task_manager = TaskManager()

    # Create Observer window first (needed for server callbacks)
    observer_window = ObserverSystemWindow(task_manager)
    oc = observer_window.observer_control

    # Handle incoming messages from User
    def handle_message(msg):
        # Update metrics if received
        if msg.get("command") == "metrics":
            data = msg.get("data", {})
            observer_window.metrics_manager.update_metrics(data)
            ts = oc.get_timestamp()
            logger = get_logger()
            # Log metrics per task
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

    #Connection hooks
    def on_client_connect(addr):
        # Update GUI on successful client connection
        print(f"[Observer] Connection successful: {addr}")
        oc.set_connection_status("Connection Successful", success=True)

    def on_client_disconnect():
        # Update GUI when client disconnects
        print("[Observer] Client disconnected")
        oc.set_connection_status("Disconnected", success=False)

    # Start TCP server with callbacks
    server = Server(
        port=5000,
        on_message=handle_message,
        on_connect=on_client_connect,
        on_disconnect=on_client_disconnect
    )
    server.start()

    # Give Observer window access to server
    observer_window.server = server

    # Observer control signals to server
    # When checkboxes change, notify User to update active tasks
    oc.tasks_changed.connect(
        lambda active: server.send({"command": "update_active", "active": active})
    )

    # Start button: send start command with parameters
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

    # Complete button (or timer expiry): send complete and save logs
    def complete_handler():
        server.send({"command": "complete"})
        path = get_logger().dump_csv()
        if path:
            print(f"[Observer] Metrics saved to {path}")
            observer_window.log_button.setText(f"Log saved to {os.path.dirname(path)}")

    oc.complete_pressed.connect(complete_handler)

    # Stop button: send stop and save logs
    def stop_handler():
        server.send({"command": "stop"})
        path = get_logger().dump_csv()
        if path:
            print(f"[Observer] Metrics saved to {path}")
            observer_window.log_button.setText(f"Log saved to {os.path.dirname(path)}")

    oc.stop_pressed.connect(stop_handler)

    # Start UDP discovery broadcaster
    broadcaster = DiscoveryBroadcaster(interval=2)
    broadcaster.start()

    # Show Observer window and start event loop
    observer_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
