# main_observer.py
import sys
from PyQt5.QtWidgets import QApplication
from main_interface.unified_interface import ObserverSystemWindow
from main_interface.task_manager import TaskManager
from network.server import Server


def main():
    app = QApplication(sys.argv)

    task_manager = TaskManager()
    server = Server(port=5000)
    server.start()

    observer_window = ObserverSystemWindow(task_manager, server=server)
    oc = observer_window.observer_control

    oc.tasks_changed.connect(
        lambda active: server.send({"command": "update_active", "active": active})
    )

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
    oc.stop_pressed.connect(lambda: server.send({"command": "stop"}))

    def handle_message(msg):
        if msg.get("command") == "metrics":
            data = msg.get("data", {})
            observer_window.metrics_manager.update_metrics(data)

    server.on_message = handle_message

    observer_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
