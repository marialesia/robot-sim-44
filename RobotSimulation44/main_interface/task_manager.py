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

        for task in active_tasks:
            if task == "sorting":
                if "sorting" not in self.task_instances:
                    self.task_instances["sorting"] = SortingTask()
                    # attach metrics manager if available
                    if hasattr(self, "metrics_manager"):
                        self.task_instances["sorting"].metrics_manager = self.metrics_manager
                panels.append(self.task_instances["sorting"])

            elif task == "packaging":
                if "packaging" not in self.task_instances:
                    self.task_instances["packaging"] = PackagingTask()
                    if hasattr(self, "metrics_manager"):
                        self.task_instances["packaging"].metrics_manager = self.metrics_manager
                panels.append(self.task_instances["packaging"])

            elif task == "inspection":
                if "inspection" not in self.task_instances:
                    self.task_instances["inspection"] = InspectionTask()
                    if hasattr(self, "metrics_manager"):
                        self.task_instances["inspection"].metrics_manager = self.metrics_manager
                panels.append(self.task_instances["inspection"])

        return panels

    
    def set_metrics_manager(self, metrics_manager):
        self.metrics_manager = metrics_manager

