# main.py
import sys
from PyQt5.QtWidgets import QApplication
from main_interface.signal_bus import SignalBus
from main_interface.task_manager import TaskManager
from main_interface.observer_system import ObserverSystem
from main_interface.user_system import UserSystem

def main():
    app = QApplication(sys.argv)

    # Shared bus + task manager
    bus = SignalBus()
    task_manager = TaskManager()

    # Create both windows
    observer_win = ObserverSystem(bus)
    user_win = UserSystem(bus, task_manager)

    observer_win.show()
    user_win.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

    