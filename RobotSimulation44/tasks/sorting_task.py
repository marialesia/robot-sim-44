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

        # ===== Existing box spawner (created but not started until Start) =====
        self._box_timer = QTimer(self)
        self._box_timer.timeout.connect(self.conveyor.spawn_box)

        # ===== Arm "pick" animation (timer-driven; no base_task changes) =====
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
        self._touch_window_px = 18      # how close a box must be to the gripper (horizontally)
        self._touch_cooldown_ms = 120   # min time between triggers (prevents double-trigger on one box)

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
        # initial pose
        return (-90.0, -0.0)

    def _pose_prep(self):
        # slight move over belt before descending
        return (-92.0, -12.0)

    def _pose_pick(self):
        # descend to "grip" height over belt
        return (-110.0, -95.0)

    def _pose_lift(self):
        # lift a bit as if carrying
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
        grip_x = self.conveyor.width() * 0.5  # center over belt; adjust if your gripper is offset
        w = self._touch_window_px
        # Trigger if any box center is inside [grip_x - w, grip_x + w]
        for x in boxes:
            if (grip_x - w) <= x <= (grip_x + w):
                return True
        return False
