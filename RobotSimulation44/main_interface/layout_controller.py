# main_interface/layout_controller.py
from PyQt5.QtWidgets import QHBoxLayout

class LayoutController:
    def __init__(self, parent_layout, task_manager, status_label=None):
        self.task_manager = task_manager
        self.status_label = status_label

        # Workspace layout
        self.workspace_area = QHBoxLayout()
        parent_layout.addLayout(self.workspace_area)

    def set_status_label(self, status_label):
        """Assign or update the status label after layout is created."""
        self.status_label = status_label

    def update_workspace(self, active_tasks):
        """Clear workspace and add panels for active tasks."""
        # Clear current workspace
        for i in reversed(range(self.workspace_area.count())):
            widget = self.workspace_area.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Add panels from task manager
        panels = self.task_manager.get_task_panels(active_tasks)
        for panel in panels:
            self.workspace_area.addWidget(panel)

        # Update status label if assigned
        if self.status_label:
            self.status_label.setText(
                f"Active tasks: {', '.join(active_tasks) if active_tasks else 'None'}"
            )

    def start_tasks(self):
        """Start all tasks that have a 'start' method."""
        for task in self.task_manager.task_instances.values():
            if hasattr(task, "start"):
                task.start()

    def stop_tasks(self):
        """Stop all tasks that have a 'stop' method."""
        for task in self.task_manager.task_instances.values():
            if hasattr(task, "stop"):
                task.stop()

