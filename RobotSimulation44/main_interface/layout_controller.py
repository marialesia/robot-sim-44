# main_interface/layout_controller.py
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtCore import Qt
from event_logger import get_logger 

class LayoutController:
    def __init__(self, parent_layout, task_manager, status_label=None, observer_control=None):
        self.task_manager = task_manager
        self.status_label = status_label
        self.observer_control = observer_control

        # Workspace layout
        self.workspace_area = QHBoxLayout()
        parent_layout.addLayout(self.workspace_area)

    def set_status_label(self, status_label):
        """Assign or update the status label after layout is created."""
        self.status_label = status_label

    def update_workspace(self, active_tasks):
        """Clear workspace and add panels for active tasks, centered as a group."""
        # Fully clear current workspace (widgets AND spacers)
        while self.workspace_area.count():
            item = self.workspace_area.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        # Add left spacer -> keeps the group centered
        self.workspace_area.addStretch(1)

        # Add selected task panels
        panels = self.task_manager.get_task_panels(active_tasks)
        for panel in panels:
            # Align near the top; horizontal centering is handled by the stretches
            self.workspace_area.addWidget(panel, 0, Qt.AlignVCenter)

        # Add right spacer
        self.workspace_area.addStretch(1)

        # Update status label if assigned
        if self.status_label:
            self.status_label.setText(
                f"Active tasks: {', '.join(active_tasks) if active_tasks else 'None'}"
            )

    def start_tasks(self):
        """Start all tasks that have a 'start' method."""
        for task in self.task_manager.task_instances.values():
            if hasattr(task, "start"):
                params = {}
                if self.observer_control:
                    # Check the task type
                    class_name = task.__class__.__name__
                    if class_name == "SortingTask":
                        params = self.observer_control.get_params_for_task("sorting")
                    elif class_name == "PackagingTask":
                        params = self.observer_control.get_params_for_task("packaging")
                    elif class_name == "InspectionTask":
                        params = self.observer_control.get_params_for_task("inspection")
                    # else leave params empty for tasks with no parameters

                if params:
                    task.start(**params)
                else:
                    task.start()

    def pause_tasks(self):
        """Pause all tasks that have a 'pause' method', then write CSV log."""
        for task in self.task_manager.task_instances.values():
            if hasattr(task, "pause"):
                task.pause()

        # --- Dump buffered events to CSV on Pause --- 
        path = get_logger().dump_csv()
        if self.status_label:
            if path:
                self.status_label.setText(f"Paused. Log saved to: {path}")
            else:
                self.status_label.setText("Paused. (No events to log.)")

    def stop_tasks(self):
        """Stop all tasks that have a 'stop' method', then write CSV log."""
        for task in self.task_manager.task_instances.values():
            if hasattr(task, "stop"):
                task.stop()

        # --- Dump buffered events to CSV on Pause --- 
        path = get_logger().dump_csv()
        if self.status_label:
            if path:
                self.status_label.setText(f"Stopped. Log saved to: {path}")
            else:
                self.status_label.setText("Stopped. (No events to log.)")
