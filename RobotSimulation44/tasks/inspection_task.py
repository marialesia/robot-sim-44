from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from .base_task import BaseTask

class InspectionTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Inspection")

        self.arm.shoulder_angle = -100
        self.arm.elbow_angle = -20
        self.arm.c_arm = QColor("#2e86c1")
        self.container.border = QColor("#224")
        self.container.fill_top = QColor("#eef2ff")
        self.container.fill_bottom = QColor("#dfe7ff")
        self.container.rib = QColor(80, 90, 160, 110)

        # Positions (side-by-side, centered)
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=2, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=3, align=Qt.AlignHCenter | Qt.AlignBottom),
            container=dict(row=1, col=1, align=Qt.AlignHCenter | Qt.AlignVCenter),
            col_stretch=[1, 1], row_stretch=[0, 1], spacing=24
        )
