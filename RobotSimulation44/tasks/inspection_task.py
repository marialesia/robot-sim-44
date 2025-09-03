# tasks/inspection_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from .base_task import BaseTask, StorageContainerWidget

class InspectionTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Inspection")

        # --- Arm styling (unchanged) ---
        self.arm.shoulder_angle = -100
        self.arm.elbow_angle = -20
        self.arm.c_arm = QColor("#2e86c1")

        # --- Use the built-in container as the LEFT (green) one ---
        self.container_left = self.container
        self.container_left.border = QColor("#1f7a3a")
        self.container_left.fill_top = QColor("#d9f7e6")
        self.container_left.fill_bottom = QColor("#bff0d3")
        self.container_left.rib = QColor(31, 122, 58, 110)

        # --- Create a RIGHT (red) container ---
        self.container_right = StorageContainerWidget()
        self.container_right.border = QColor("#8c1f15")
        self.container_right.fill_top = QColor("#ffd6d1")
        self.container_right.fill_bottom = QColor("#ffb8b0")
        self.container_right.rib = QColor(140, 31, 21, 110)

        # --- Positions: conveyor & arm stay centered/top; containers mirror left/right ---
        # Use 3 columns so we can place containers on columns 0 and 2 with the arm centered.
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=3, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=3, align=Qt.AlignHCenter | Qt.AlignBottom),
            container=dict(row=1, col=1, align=Qt.AlignHCenter | Qt.AlignVCenter),  # placeholder; we’ll move it
            col_stretch=[1, 1, 1],
            row_stretch=[0, 1],
            spacing=24
        )

        # Remove the placeholder placement of the built-in container
        try:
            self.grid.removeWidget(self.container_left)
        except Exception:
            pass

        # Add both containers: left on col 0, right on col 2
        self.grid.addWidget(self.container_left,  1, 0, 1, 1, Qt.AlignRight  | Qt.AlignBottom)
        self.grid.addWidget(self.container_right, 1, 2, 1, 1, Qt.AlignLeft   | Qt.AlignBottom)

        # Initial repaint
        self.arm.update()
        self.conveyor.update()
        self.container_left.update()
        self.container_right.update()

    # ===== Called by existing GUI (LayoutController.start_tasks/stop_tasks) =====
    def start(self):
        # Positive = left > right
        self.conveyor.setBeltSpeed(60)  # tweak for difficulty as needed
        self.conveyor.enable_motion(True)

    def stop(self):
        self.conveyor.enable_motion(False)
