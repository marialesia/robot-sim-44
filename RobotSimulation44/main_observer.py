# main_observer.py
import sys
from PyQt5.QtWidgets import QApplication
from main_interface.unified_interface import ObserverSystemWindow
from main_interface.task_manager import TaskManager
from network.server import Server

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

    # Start, Pause, Stop buttons
    oc.start_pressed.connect(
        lambda: server.send({
            "command": "start",
            "params": {
                "sorting": oc.get_params_for_task("sorting"),
                "packaging": oc.get_params_for_task("packaging"),
                "inspection": oc.get_params_for_task("inspection"),
                "active": oc.get_active_tasks()
            }
        })
    )
    oc.pause_pressed.connect(lambda: server.send({"command": "pause"}))
    oc.stop_pressed.connect(lambda: server.send({"command": "stop"}))

    observer_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
