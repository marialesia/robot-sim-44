# main.py
import sys
from PyQt5.QtWidgets import QApplication
from main_interface.unified_interface import UserSystemWindow, ObserverSystemWindow
from main_interface.task_manager import TaskManager

def main():
    app = QApplication(sys.argv)

    # Shared task manager
    task_manager = TaskManager()

    # Create both windows
    user_window = UserSystemWindow(task_manager)
    observer_window = ObserverSystemWindow(task_manager)

    # Assign observer control from observer window to user's layout controller
    user_window.layout_controller.observer_control = observer_window.observer_control

    # Connect signals AFTER assignment
    observer_window.observer_control.tasks_changed.connect(
        user_window.layout_controller.update_workspace
    )
    observer_window.observer_control.start_pressed.connect(
        user_window.layout_controller.start_tasks
    )
    observer_window.observer_control.complete_pressed.connect(
        user_window.layout_controller.complete_tasks
    )
    observer_window.observer_control.stop_pressed.connect(
        user_window.layout_controller.stop_tasks
    )

    # Show windows
    user_window.show()
    observer_window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
