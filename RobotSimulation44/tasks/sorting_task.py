# tasks/sorting_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from .base_task import BaseTask, StorageContainerWidget

class SortingTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Sorting")

        # ---- Robot arm visuals ----
        self.arm.shoulder_angle = -95
        self.arm.elbow_angle = -5
        self.arm.c_arm = QColor("#3f88ff")
        self.arm.c_arm_dark = QColor("#2f6cc9")

        # ---- Containers: Blue (middle) uses the built-in self.container ----
        # Blue (middle)
        self.container.border = QColor("#2b4a91")
        self.container.fill_top = QColor("#dbe8ff")
        self.container.fill_bottom = QColor("#c7daff")
        self.container.rib = QColor(43, 74, 145, 120)

        # Red (left)
        self.container_left = StorageContainerWidget()
        self.container_left.border = QColor("#8c1f15")
        self.container_left.fill_top = QColor("#ffd6d1")
        self.container_left.fill_bottom = QColor("#ffb8b0")
        self.container_left.rib = QColor(140, 31, 21, 120)

        # Green (right)
        self.container_right = StorageContainerWidget()
        self.container_right.border = QColor("#1f7a3a")
        self.container_right.fill_top = QColor("#d9f7e6")
        self.container_right.fill_bottom = QColor("#bff0d3")
        self.container_right.rib = QColor(31, 122, 58, 120)

        # ---- Layout: Conveyor (row 0), Arm (row 1, spanning 3 cols),
        #              Three containers (row 3: red, blue, green) ----
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=3, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=3, align=Qt.AlignHCenter | Qt.AlignBottom),
            container=dict(row=3, col=1, align=Qt.AlignHCenter | Qt.AlignTop),  # Blue in the middle
            col_stretch=[1, 1, 1],
            row_stretch=[0, 0, 1],
            spacing=18
        )

        # Add Red (left) and Green (right) on the same row under the arm
        self.grid.addWidget(self.container_left,  3, 0, 1, 1, Qt.AlignLeft  | Qt.AlignTop)
        self.grid.addWidget(self.container_right, 3, 2, 1, 1, Qt.AlignRight | Qt.AlignTop)

        # Repaint
        self.arm.update()
        self.conveyor.update()
        self.container_left.update()
        self.container.update()
        self.container_right.update()

    # ===== Called by existing GUI (LayoutController.start_tasks/stop_tasks) =====
    def start(self):
        # Positive = left > right
        self.conveyor.setBeltSpeed(120)
        self.conveyor.enable_motion(True)

    def stop(self):
        self.conveyor.enable_motion(False)
