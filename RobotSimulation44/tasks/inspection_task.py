# tasks/inspection_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer
from .base_task import BaseTask, StorageContainerWidget
from .inspection_logic import InspectionWorker

class InspectionTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Inspection")

        # ---- Robot arm visuals ----
        self.arm.shoulder_angle = -90
        self.arm.elbow_angle = 0
        self.arm.c_arm = QColor("#3f88ff")
        self.arm.c_arm_dark = QColor("#2f6cc9")

        # ---- Containers (only Red and Green) ----
        self.container_red = StorageContainerWidget()
        self.container_red.border = QColor("#8c1f15")
        self.container_red.fill_top = QColor("#ffd6d1")
        self.container_red.fill_bottom = QColor("#ffb8b0")
        self.container_red.rib = QColor(140, 31, 21, 120)

        self.container_green = StorageContainerWidget()
        self.container_green.border = QColor("#1f7a3a")
        self.container_green.fill_top = QColor("#d9f7e6")
        self.container_green.fill_bottom = QColor("#bff0d3")
        self.container_green.rib = QColor(31, 122, 58, 120)

        # ---- Layout: Conveyor (row 0), Arm (row 1), Containers (row 3) ----
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=2, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=2, align=Qt.AlignHCenter | Qt.AlignBottom),
            col_stretch=[1, 1],
            row_stretch=[0, 0, 1],
            spacing=18
        )

        # Place only red and green containers
        self.grid.addWidget(self.container_red,   3, 0, 1, 1, Qt.AlignHCenter | Qt.AlignTop)
        self.grid.addWidget(self.container_green, 3, 1, 1, 1, Qt.AlignHCenter | Qt.AlignTop)

        # Repaint
        self.arm.update()
        self.conveyor.update()
        self.container_red.update()
        self.container_green.update()

        # ===== Arm "touch every box" animation =====
        self._pick_timer = QTimer(self)
        self._pick_timer.setInterval(16)  # ~60 FPS
        self._pick_timer.timeout.connect(self._tick_pick)

        # FSM state
        self._pick_state = "idle"
        self._pick_t = 0
        self._pick_duration = 0
        self._pick_from = (self.arm.shoulder_angle, self.arm.elbow_angle)
        self._pick_to = (self.arm.shoulder_angle, self.arm.elbow_angle)

        # --- Trigger settings ---
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._touch_window_px = 18
        self._touch_cooldown_ms = 120

        # --- Despawn offset ---
        self._despawn_offset_px = 24

        # Worker
        self.worker = None

    def start(self):
        self.conveyor.setBeltSpeed(120)
        self.conveyor.enable_motion(True)

        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._pick_state = "idle"
        self._pick_t = 0

        if not self._pick_timer.isActive():
            sh, el = self._pose_home()
            self._set_arm(sh, el)
            self._pick_timer.start()

        if not self.worker or not self.worker.isRunning():
            self.worker = InspectionWorker(
                pace="slow",   # "slow", "medium", or "fast"
                bin_count=2,   # only red and green
                error_rate=0.1
            )
            self.worker.box_spawned.connect(self.spawn_box_from_worker)
            self.worker.box_sorted.connect(self._on_box_sorted)
            self.worker.metrics_ready.connect(self._on_metrics)
            self.worker.start()

    def stop(self):
        self.conveyor.enable_motion(False)
        if self._pick_timer.isActive():
            self._pick_timer.stop()
        sh, el = self._pose_home()
        self._set_arm(sh, el)
        if self.worker and self.worker.isRunning():
            self.worker.stop()

    # Arm pose helpers
    def _pose_home(self): return (-90.0, 0.0)
    def _pose_prep(self): return (-92.0, -12.0)
    def _pose_pick(self): return (-110.0, -95.0)
    def _pose_lift(self): return (-93.0, -10.0)

    def _set_arm(self, shoulder, elbow):
        self.arm.shoulder_angle = float(shoulder)
        self.arm.elbow_angle = float(elbow)
        self.arm.update()

    def _start_seg(self, to_angles, duration_ms):
        self._pick_from = (self.arm.shoulder_angle, self.arm.elbow_angle)
        self._pick_to = (float(to_angles[0]), float(to_angles[1]))
        self._pick_duration = max(1, int(duration_ms))
        self._pick_t = 0

    def _tick_pick(self):
        self._now_ms += self._pick_timer.interval()
        if self._pick_state == "idle":
            if self._box_near_grip() and (self._now_ms - self._last_touch_time_ms) >= self._touch_cooldown_ms:
                self._last_touch_time_ms = self._now_ms
                self._pick_state = "to_prep"
                self._start_seg(self._pose_prep(), 120)
            else:
                return

        self._pick_t += self._pick_timer.interval()
        t = min(1.0, self._pick_t / float(self._pick_duration))
        s0, e0 = self._pick_from
        s1, e1 = self._pick_to
        s = s0 + (s1 - s0) * t
        e = e0 + (e1 - e0) * t
        self._set_arm(s, e)

        if self._pick_state in ("hold", "lift"):
            self._despawn_if_past_cutoff()

        if t >= 1.0:
            if self._pick_state == "to_prep":
                self._pick_state = "descend"
                self._start_seg(self._pose_pick(), 120)
            elif self._pick_state == "descend":
                nearest_color = self._get_nearest_box_color()
                if nearest_color:
                    self.worker.sort_box(nearest_color)
                self._pick_state = "hold"
                self._start_seg(self._pose_pick(), 40)
            elif self._pick_state == "hold":
                self._pick_state = "lift"
                self._start_seg(self._pose_lift(), 120)
            elif self._pick_state == "lift":
                self._pick_state = "return"
                self._start_seg(self._pose_home(), 160)
            elif self._pick_state == "return":
                self._pick_state = "idle_pause"
                self._start_seg(self._pose_home(), 40)
            elif self._pick_state == "idle_pause":
                self._pick_state = "idle"

    def _box_near_grip(self):
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes:
            return False
        grip_x = self.conveyor.width() * 0.44
        w = self._touch_window_px
        return any((grip_x - w) <= x <= (grip_x + w) for x in boxes)

    def _despawn_if_past_cutoff(self):
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes:
            return
        colors = getattr(self.conveyor, "_box_colors", None)
        detect_x = self.conveyor.width() * 0.44
        cutoff_x = detect_x + self._despawn_offset_px
        hit_index = -1
        for i, x in enumerate(boxes):
            if x >= cutoff_x:
                hit_index = i
                break
        if hit_index != -1:
            del boxes[hit_index]
            if isinstance(colors, list) and hit_index < len(colors):
                del colors[hit_index]
            self.conveyor.update()

    def _get_nearest_box_color(self):
        grip_x = self.conveyor.width() * 0.44
        w = self._touch_window_px
        COLOR_MAP = {
            "#c82828": "red",
            "#1f7a3a": "green"
        }
        for x, c in zip(self.conveyor._boxes, self.conveyor._box_colors):
            if (grip_x - w) <= x <= (grip_x + w):
                return COLOR_MAP.get(c.name(), "unknown")
        return None

    def _on_box_sorted(self, color, correct):
        print(f"Sorted {color} {'✅' if correct else '❌'}")

    def _on_metrics(self, metrics):
        print("Final metrics:", metrics)

    def spawn_box_from_worker(self, box_data):
        color = box_data["color"]
        error = box_data["error"]
        self.conveyor.spawn_box(color=color, error=error)
