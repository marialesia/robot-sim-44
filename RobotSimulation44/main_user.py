# main_user.py
import sys
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication
from main_interface.unified_interface import UserSystemWindow
from main_interface.task_manager import TaskManager
from network.client import Client


class UserMessageBridge(QObject):
    update_active = pyqtSignal(list)
    start_tasks = pyqtSignal(dict)
    pause_tasks = pyqtSignal()
    stop_tasks = pyqtSignal()


def main():
    app = QApplication(sys.argv)

    task_manager = TaskManager()
    user_window = UserSystemWindow(task_manager)
    user_window.show()

    if hasattr(task_manager, "set_workspace_updater"):
        task_manager.set_workspace_updater(user_window.layout_controller.update_workspace)

    # --- Bridge setup ---
    bridge = UserMessageBridge()

    # Connect signals to real methods (GUI thread safe)
    bridge.update_active.connect(user_window.layout_controller.update_workspace)
    bridge.start_tasks.connect(task_manager.start_all_tasks)
    bridge.pause_tasks.connect(task_manager.pause_all_tasks)
    bridge.stop_tasks.connect(task_manager.stop_all_tasks)

    # --- Handle incoming messages from Observer ---
    def handle_message(msg):
        print("[User] Got:", msg)
        cmd = msg.get("command")

        if cmd == "update_active":
            bridge.update_active.emit(msg.get("active", []))
        elif cmd == "start":
            bridge.start_tasks.emit(msg)
        elif cmd == "pause":
            bridge.pause_tasks.emit()
        elif cmd == "stop":
            bridge.stop_tasks.emit()

    # Start client
    client = Client(host="127.0.0.1", port=5000, on_message=handle_message)
    client.start()

    # Inject network client into TaskManager so all tasks can send metrics
    task_manager.set_network_client(client)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
