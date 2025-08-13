# tasks/base_task.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import Qt

class BaseTask(QWidget):
    def __init__(self, task_name="Task"):
        super().__init__()

        # Main layout
        layout = QVBoxLayout(self)

        # Task label at the top
        title_label = QLabel(f"{task_name} Workspace")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)

        # Warehouse scene container
        warehouse_scene = QFrame()
        warehouse_scene.setFrameShape(QFrame.Box)
        warehouse_scene.setLineWidth(2)
        warehouse_scene.setFixedHeight(400)
        warehouse_layout = QHBoxLayout(warehouse_scene)
        warehouse_layout.setSpacing(20)

        # Conveyor belt (gray rectangle)
        conveyor_belt = QFrame()
        conveyor_belt.setFrameShape(QFrame.Box)
        conveyor_belt.setLineWidth(1)
        conveyor_belt.setFixedSize(300, 100)
        conveyor_belt.setStyleSheet("background-color: lightgray;")
        warehouse_layout.addWidget(conveyor_belt, alignment=Qt.AlignVCenter)

        # Robot arm (blue rectangle)
        robot_arm = QFrame()
        robot_arm.setFrameShape(QFrame.Box)
        robot_arm.setLineWidth(1)
        robot_arm.setFixedSize(50, 150)
        robot_arm.setStyleSheet("background-color: steelblue;")
        warehouse_layout.addWidget(robot_arm, alignment=Qt.AlignBottom)

        # Placeholder storage area (green rectangle)
        storage_area = QFrame()
        storage_area.setFrameShape(QFrame.Box)
        storage_area.setLineWidth(1)
        storage_area.setFixedSize(150, 150)
        storage_area.setStyleSheet("background-color: lightgreen;")
        warehouse_layout.addWidget(storage_area, alignment=Qt.AlignBottom)

        layout.addWidget(warehouse_scene)
