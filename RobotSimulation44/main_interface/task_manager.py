# main_interface/task_manager.py
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from tasks.sorting_task import SortingTask
from tasks.packaging_task import PackagingTask
from tasks.inspection_task import InspectionTask

class TaskManager:
    def __init__(self):
        # Store active task widget instances so we can start/stop them later
        self.task_instances = {}
        self.metrics_manager = None
        self.workspace_updater = None

    def get_task_panels(self, active_tasks):
        """Return the appropriate panels for the selected tasks."""
        panels = []

        # Ensure all known task types are considered
        all_tasks = {
            "sorting": SortingTask,
            "packaging": PackagingTask,
            "inspection": InspectionTask,
        }

        for name, cls in all_tasks.items():
            if name not in self.task_instances:
                self.task_instances[name] = cls()
                if self.metrics_manager:
                    self.task_instances[name].metrics_manager = self.metrics_manager

            # Mark enabled/disabled
            self.task_instances[name].enabled = name in active_tasks

            if name in active_tasks:
                panels.append(self.task_instances[name])

        return panels

    def set_metrics_manager(self, metrics_manager):
        self.metrics_manager = metrics_manager

    def set_workspace_updater(self, updater):
        """Inject LayoutController.update_workspace so we can refresh panels."""
        self.workspace_updater = updater

    # --- Network-driven control methods ---
    def start_all_tasks(self, msg):
        """
        Called from the User side when Observer sends 'start'.
        msg looks like:
        {
            "command": "start",
            "params": {
                "sorting": {...},
                "packaging": {...},
                "inspection": {...},
                "active": ["sorting","packaging"]
            }
        }
        """
        params = msg.get("params", {})
        active = params.get("active", [])

        # Update workspace (so panels appear)
        if self.workspace_updater:
            self.workspace_updater(active)

        # Start each enabled task with its parameters
        for name in active:
            task = self.task_instances.get(name)
            if not task:
                continue
            task_params = params.get(name, {})
            try:
                task.start(**task_params)
            except TypeError:
                task.start()

    def pause_all_tasks(self):
        """Pause all tasks if they implement pause()."""
        for task in self.task_instances.values():
            if hasattr(task, "pause"):
                task.pause()

    def stop_all_tasks(self):
        """Stop all tasks if they implement stop()."""
        for task in self.task_instances.values():
            if hasattr(task, "stop"):
                task.stop()
