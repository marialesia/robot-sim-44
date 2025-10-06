# main_interface/layout_controller.py
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtCore import Qt
from event_logger import get_logger 

# Controls layout management and task operations between user and observer systems
class LayoutController:
    # Initialize layout controller and workspace area
    def __init__(self, parent_layout, task_manager, status_label=None, observer_control=None):
        self.task_manager = task_manager
        self.status_label = status_label
        self.observer_control = observer_control

        # Workspace layout
        self.workspace_area = QVBoxLayout()
        self.workspace_area.setAlignment(Qt.AlignCenter)  # <-- force centering
        parent_layout.addLayout(self.workspace_area)

    # Assign or update the status label
    def set_status_label(self, status_label):
        """Assign or update the status label after layout is created."""
        self.status_label = status_label

    # Update the workspace with panels for active tasks
    def update_workspace(self, active_tasks):
        """Clear workspace and add panels for active tasks, stacked vertically."""
        # Fully clear current workspace (widgets AND spacers)
        while self.workspace_area.count():
            item = self.workspace_area.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        # Add selected task panels (stack vertically, centered horizontally)
        panels = self.task_manager.get_task_panels(active_tasks)
        for panel in panels:
            self.workspace_area.addWidget(panel, 0, Qt.AlignHCenter)

        # Add stretch above and below so panels stay vertically centered
        self.workspace_area.insertStretch(0, 1)   # push down from top
        self.workspace_area.addStretch(1)         # push up from bottom

        # Update status label if assigned
        if self.status_label:
            self.status_label.setText(
                f"Active tasks: {', '.join(active_tasks) if active_tasks else 'None'}"
            )

    # Start all active tasks and sync sound settings
    def start_tasks(self):
        """Start all tasks that have a 'start' method and sync sound settings."""
        sounds = {}
        if self.observer_control:
            # Get sounds from the observer control panel
            sounds = self.observer_control.get_sounds_enabled()
            self.task_manager.sounds_enabled.update(sounds)

        for task in self.task_manager.task_instances.values():
            if hasattr(task, "start"):
                params = {}
                if self.observer_control:
                    # Give each task access to observer_control
                    task.observer_control = self.observer_control  

                    # Fetch correct parameters for each task type
                    class_name = task.__class__.__name__
                    if class_name == "SortingTask":
                        params = self.observer_control.get_params_for_task("sorting")
                    elif class_name == "PackagingTask":
                        params = self.observer_control.get_params_for_task("packaging")
                    elif class_name == "InspectionTask":
                        params = self.observer_control.get_params_for_task("inspection")

                # Always inject sounds dict reference
                task.sounds_enabled = self.task_manager.sounds_enabled

                if params:
                    task.start(**params)
                else:
                    task.start()

    # Complete all tasks and save CSV event log
    def complete_tasks(self):
        """Complete all tasks that have a 'complete' method', then write CSV log."""
        for task in self.task_manager.task_instances.values():
            if hasattr(task, "complete"):
                task.complete()

        # Dump buffered events to CSV on Complete
        path = get_logger().dump_csv()
        if self.status_label:
            if path:
                self.status_label.setText(f"Complete. Log saved to observer device")
            else:
                self.status_label.setText("Complete.")

    # Stop all tasks and save CSV event log
    def stop_tasks(self):
        """Stop all tasks that have a 'stop' method', then write CSV log."""
        for task in self.task_manager.task_instances.values():
            if hasattr(task, "stop"):
                task.stop()

        # Dump buffered events to CSV on Stop 
        path = get_logger().dump_csv()
        if self.status_label:
            if path:
                self.status_label.setText(f"Stopped. Log saved to: {path}")
            else:
                self.status_label.setText("Stopped.")
