# tasks/packaging_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer
from .base_task import BaseTask

class PackagingTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Packaging")

        self.arm.shoulder_angle = -80
        self.arm.elbow_angle = 10
        self.arm.c_arm = QColor("#8e44ad")
        self.arm.c_arm_dark = QColor("#6d2e8a")

        self.container.border = QColor("#c76a1a")
        self.container.fill_top = QColor("#ffe9d3")
        self.container.fill_bottom = QColor("#ffd9b5")
        self.container.rib = QColor(199, 106, 26, 110)

        # Positions (container left, arm right)
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=2, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=3, align=Qt.AlignHCenter | Qt.AlignBottom),
            container=dict(row=1, col=0, align=Qt.AlignLeft  | Qt.AlignBottom),
            col_stretch=[1, 1], row_stretch=[0, 1]
        )

        # ===== Box spawner (orange) =====
        self._box_timer = QTimer(self)
        self._box_timer.timeout.connect(self._spawn_orange_box)

    def _spawn_orange_box(self):
        # BaseTask.ConveyorBeltWidget handles strings like "orange"
        self.conveyor.spawn_box(color="orange")

    # ===== Called by existing GUI (LayoutController.start_tasks/stop_tasks) =====
    def start(self):
        # Positive = left > right
        self.conveyor.setBeltSpeed(60)  # tweak as desired
        self.conveyor.enable_motion(True)

        if not self._box_timer.isActive():
            self._box_timer.start(1000)  # one orange box per second

    def stop(self):
        self.conveyor.enable_motion(False)
        if self._box_timer.isActive():
            self._box_timer.stop()
