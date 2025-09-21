# main_interface/fps_overlay.py
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QTimer, Qt

class FPSOverlay(QLabel):
    def __init__(self, task_manager, parent=None):
        super().__init__(parent)
        self.task_manager = task_manager
        self.setStyleSheet("color: lime; font-weight: bold; background: transparent;")
        self.setAlignment(Qt.AlignRight | Qt.AlignTop)

        # Update once per second
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_fps)
        self.timer.start(1000)

    def update_fps(self):
        active = self.task_manager.task_instances.values()
        fps_values = [t.get_fps() for t in active if hasattr(t, "get_fps")]
        if fps_values:
            avg = sum(fps_values) / len(fps_values)
            self.setText(f"FPS: {avg:.0f}")
        else:
            self.setText("FPS: --")
