# tasks/sorting_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer
from .base_task import BaseTask, StorageContainerWidget

class SortingTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Sorting")

        # ---- Robot arm visuals ----
        self.arm.shoulder_angle = -90
        self.arm.elbow_angle = -0
        self.arm.c_arm = QColor("#3f88ff")
        self.arm.c_arm_dark = QColor("#2f6cc9")

        # ---- Containers (all defined together) ----
        # Blue (middle) reusing the built-in container
        self.container_blue = self.container
        self.container_blue.border = QColor("#2b4a91")
        self.container_blue.fill_top = QColor("#dbe8ff")
        self.container_blue.fill_bottom = QColor("#c7daff")
        self.container_blue.rib = QColor(43, 74, 145, 120)

        # Red (left)
        self.container_red = StorageContainerWidget()
        self.container_red.border = QColor("#8c1f15")
        self.container_red.fill_top = QColor("#ffd6d1")
        self.container_red.fill_bottom = QColor("#ffb8b0")
        self.container_red.rib = QColor(140, 31, 21, 120)

        # Green (right)
        self.container_green = StorageContainerWidget()
        self.container_green.border = QColor("#1f7a3a")
        self.container_green.fill_top = QColor("#d9f7e6")
        self.container_green.fill_bottom = QColor("#bff0d3")
        self.container_green.rib = QColor(31, 122, 58, 120)

        # Purple
        self.container_purple = StorageContainerWidget()
        self.container_purple.border = QColor("#6a1b9a")
        self.container_purple.fill_top = QColor("#f0e3ff")
        self.container_purple.fill_bottom = QColor("#e3ccff")
        self.container_purple.rib = QColor(106, 27, 154, 120)

        # Orange
        self.container_orange = StorageContainerWidget()
        self.container_orange.border = QColor("#c15800")
        self.container_orange.fill_top = QColor("#ffe8cc")
        self.container_orange.fill_bottom = QColor("#ffd4a8")
        self.container_orange.rib = QColor(193, 88, 0, 120)

        # Teal
        self.container_teal = StorageContainerWidget()
        self.container_teal.border = QColor("#00796b")
        self.container_teal.fill_top = QColor("#d2f5ef")
        self.container_teal.fill_bottom = QColor("#b8efe6")
        self.container_teal.rib = QColor(0, 121, 107, 120)

        # ---- Layout: Conveyor (row 0), Arm (row 1), Containers (row 3) ----
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=6, align=Qt.AlignTop),  # Change the position of the conveyor belt here
            arm=dict(row=0, col=2, colSpan=2, align=Qt.AlignHCenter | Qt.AlignBottom),  # Change the position of the arm here
            col_stretch=[1, 1, 1],
            row_stretch=[0, 0, 1],
            spacing=18
        )

        # Place all containers on the same row
        self.grid.addWidget(self.container_red,    3, 0, 1, 1, Qt.AlignHCenter | Qt.AlignTop)
        self.grid.addWidget(self.container_blue,   3, 1, 1, 1, Qt.AlignHCenter | Qt.AlignTop)
        self.grid.addWidget(self.container_green,  3, 2, 1, 1, Qt.AlignHCenter | Qt.AlignTop)
        self.grid.addWidget(self.container_purple, 3, 3, 1, 1, Qt.AlignHCenter | Qt.AlignTop)
        self.grid.addWidget(self.container_orange, 3, 4, 1, 1, Qt.AlignHCenter | Qt.AlignTop)
        self.grid.addWidget(self.container_teal,   3, 5, 1, 1, Qt.AlignHCenter | Qt.AlignTop)

        # Ensure new columns expand evenly
        self.grid.setColumnStretch(3, 1)
        self.grid.setColumnStretch(4, 1)
        self.grid.setColumnStretch(5, 1)

        # Repaint
        self.arm.update()
        self.conveyor.update()
        self.container_red.update()
        self.container_blue.update()
        self.container_green.update()
        self.container_purple.update()
        self.container_orange.update()
        self.container_teal.update()

        # ===== Existing box spawner (created but not started until Start) =====
        self._box_timer = QTimer(self)
        self._box_timer.timeout.connect(self.conveyor.spawn_box)

        # ===== Arm "touch every box" animation (timer-driven) =====
        self._pick_timer = QTimer(self)
        self._pick_timer.setInterval(16)  # ~60 FPS
        self._pick_timer.timeout.connect(self._tick_pick)

        # FSM state
        self._pick_state = "idle"
        self._pick_t = 0
        self._pick_duration = 0
        self._pick_from = (self.arm.shoulder_angle, self.arm.elbow_angle)
        self._pick_to = (self.arm.shoulder_angle, self.arm.elbow_angle)

        # --- Trigger settings to touch every box ---
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._touch_window_px = 18
        self._touch_cooldown_ms = 120

    # ===== Called by your existing GUI =====
    def start(self):
        # belt motion
        self.conveyor.setBeltSpeed(120)   # left -> right
        self.conveyor.enable_motion(True)

        # start spawning boxes periodically
        if not self._box_timer.isActive():
            self._box_timer.start(800)    # one box every 0.8s

        # reset trigger state so we can fire immediately after a Stop
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._pick_state = "idle"
        self._pick_t = 0

        # start arm pick monitor
        if not self._pick_timer.isActive():
            sh, el = self._pose_home()
            self._set_arm(sh, el)
            self._pick_timer.start()

    def stop(self):
        self.conveyor.enable_motion(False)
        if self._box_timer.isActive():
            self._box_timer.stop()
        if self._pick_timer.isActive():
            self._pick_timer.stop()
        # return arm to home
        sh, el = self._pose_home()
        self._set_arm(sh, el)

    # ---------- Arm pick cycle (approach -> descend -> hold -> lift -> return) ----------
    def _pose_home(self):
        return (-90.0, -0.0)

    def _pose_prep(self):
        return (-92.0, -12.0)

    def _pose_pick(self):
        return (-110.0, -95.0)

    def _pose_lift(self):
        return (-93.0, -10.0)

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
        # global time
        self._now_ms += self._pick_timer.interval()

        # If idle, only start a cycle when a box is near the gripper
        if self._pick_state == "idle":
            if self._box_near_grip() and (self._now_ms - self._last_touch_time_ms) >= self._touch_cooldown_ms:
                self._last_touch_time_ms = self._now_ms
                self._pick_state = "to_prep"
                self._start_seg(self._pose_prep(), 120)  # fast move
            else:
                return

        # advance interpolation for non-idle states
        self._pick_t += self._pick_timer.interval()
        t = min(1.0, self._pick_t / float(self._pick_duration))
        s0, e0 = self._pick_from
        s1, e1 = self._pick_to
        s = s0 + (s1 - s0) * t
        e = e0 + (e1 - e0) * t
        self._set_arm(s, e)

        # segment complete -> next state (fast timings; same angles)
        if t >= 1.0:
            if self._pick_state == "to_prep":
                self._pick_state = "descend"
                self._start_seg(self._pose_pick(), 120)
            elif self._pick_state == "descend":
                self._pick_state = "hold"
                self._start_seg(self._pose_pick(), 40)     # brief touch
            elif self._pick_state == "hold":
                self._pick_state = "lift"
                self._start_seg(self._pose_lift(), 120)
            elif self._pick_state == "lift":
                self._pick_state = "return"
                self._start_seg(self._pose_home(), 160)
            elif self._pick_state == "return":
                # brief idle before next box trigger
                self._pick_state = "idle_pause"
                self._start_seg(self._pose_home(), 40)
            elif self._pick_state == "idle_pause":
                self._pick_state = "idle"

    # ---------- helpers ----------
    def _box_near_grip(self):
        """Returns True if any box is within a small window around the gripper's x-position."""
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes:
            return False
        grip_x = self.conveyor.width() * 0.44  # shifted left per your tweak
        w = self._touch_window_px
        for x in boxes:
            if (grip_x - w) <= x <= (grip_x + w):
                return True
        return False
