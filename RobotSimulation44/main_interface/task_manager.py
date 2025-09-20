# main_interface/task_manager.py
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from tasks.sorting_task import SortingTask
from tasks.packaging_task import PackagingTask
from tasks.inspection_task import InspectionTask

class TaskManager:
    def __init__(self):
        self.task_instances = {}
        self.metrics_manager = None
        self.workspace_updater = None
        self.network_client = None
        self.sounds_enabled = {    # always keep current sounds state
            "conveyor": True,
            "robotic_arm": True,
            "correct_chime": True,
            "incorrect_chime": True,
            "alarm": True
        }

    def get_task_panels(self, active_tasks):
        panels = []
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
                if self.network_client:
                    self.task_instances[name].network_client = self.network_client
                # inject sounds_enabled reference
                self.task_instances[name].sounds_enabled = self.sounds_enabled

            self.task_instances[name].enabled = name in active_tasks

            if name in active_tasks:
                panels.append(self.task_instances[name])

        return panels

    def set_metrics_manager(self, metrics_manager):
        self.metrics_manager = metrics_manager

    def set_workspace_updater(self, updater):
        self.workspace_updater = updater

    def set_network_client(self, client):
        self.network_client = client
        for t in self.task_instances.values():
            t.network_client = client

    def start_all_tasks(self, msg):
        params = msg.get("params", {})
        active = params.get("active", [])

        # Update sounds if present
        if "sounds" in params:
            self.sounds_enabled.update(params["sounds"])

        # Update workspace
        if self.workspace_updater:
            self.workspace_updater(active)

        # Start each active task
        for name in active:
            task = self.task_instances.get(name)
            if not task:
                continue
            # keep sounds reference up-to-date
            task.sounds_enabled = self.sounds_enabled
            task_params = params.get(name, {})
            try:
                task.start(**task_params)
            except TypeError:
                task.start()

    def pause_all_tasks(self):
        for task in self.task_instances.values():
            if hasattr(task, "pause"):
                task.pause()

    def stop_all_tasks(self):
        for task in self.task_instances.values():
            if hasattr(task, "stop"):
                task.stop()
