# main_user.py
import sys
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from main_interface.unified_interface import UserSystemWindow
from main_interface.task_manager import TaskManager
from network.client import Client
from network.discovery import DiscoveryListener


class UserMessageBridge(QObject):
    # Bridge signals between network messages and task manager / GUI
    update_active = pyqtSignal(list)
    start_tasks = pyqtSignal(dict)
    pause_tasks = pyqtSignal()
    stop_tasks = pyqtSignal()


def main():
    # Enable high-DPI scaling for GUI
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Create QApplication
    app = QApplication(sys.argv)

    # Initialize TaskManager and main user window
    task_manager = TaskManager()
    user_window = UserSystemWindow(task_manager)
    user_window.show()

    # Allow TaskManager to update workspace through layout controller
    if hasattr(task_manager, "set_workspace_updater"):
        task_manager.set_workspace_updater(user_window.layout_controller.update_workspace)

    # Initialize bridge for message handling
    bridge = UserMessageBridge()
    bridge.update_active.connect(user_window.layout_controller.update_workspace)
    bridge.start_tasks.connect(task_manager.start_all_tasks)
    bridge.pause_tasks.connect(task_manager.pause_all_tasks)
    bridge.stop_tasks.connect(task_manager.stop_all_tasks)

    # Handle incoming messages from observer / server
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
        elif cmd == "complete":  
            user_window.layout_controller.complete_tasks()

    # Listener is created here so we can reference it inside connect_to_observer
    listener = DiscoveryListener(on_found=lambda ip, port: connect_to_observer(ip, port))

    # Connect to observer once discovered
    def connect_to_observer(ip, port):
        print(f"[User] Found observer at {ip}:{port}")
        client = Client(host=ip, port=port, on_message=handle_message)
        client.start()
        task_manager.set_network_client(client)

        # Stop discovery once connected
        listener.stop()

    # Start listening for discovery broadcasts
    listener.start()

    # Run application event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
