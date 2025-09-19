# main_interface/task_manager.py
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from tasks.sorting_task import SortingTask
from tasks.packaging_task import PackagingTask
from tasks.inspection_task import InspectionTask

class TaskManager:
    def __init__(self):
        # Store active task widget instances so we can start/stop them later
        self.task_instances = {}

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
                if hasattr(self, "metrics_manager"):
                    self.task_instances[name].metrics_manager = self.metrics_manager

            # --- NEW: mark enabled/disabled ---
            self.task_instances[name].enabled = name in active_tasks

            if name in active_tasks:
                panels.append(self.task_instances[name])

        return panels
    
    
    def set_metrics_manager(self, metrics_manager):
        self.metrics_manager = metrics_manager

