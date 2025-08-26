# tasks/packaging_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer
from .base_task import BaseTask

class PackagingTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Packaging")

        # ---- Robot arm visuals ----
        self.arm.shoulder_angle = -90
        self.arm.elbow_angle = 0
        self.arm.c_arm = QColor("#8e44ad")
        self.arm.c_arm_dark = QColor("#6d2e8a")

        # ---- Container palette ----
        self.container.border = QColor("#c76a1a")
        self.container.fill_top = QColor("#ffe9d3")
        self.container.fill_bottom = QColor("#ffd9b5")
        self.container.rib = QColor(199, 106, 26, 110)

        # ---- Layout (unchanged except container aligned RIGHT in col 0) ----
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=2, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=3, align=Qt.AlignHCenter | Qt.AlignBottom),
            container=dict(row=1, col=0, align=Qt.AlignRight | Qt.AlignBottom),
            col_stretch=[1, 1], row_stretch=[0, 1]
        )

        # ===== Box spawner (orange) =====
        self._box_timer = QTimer(self)
        self._box_timer.timeout.connect(self._spawn_orange_box)

        # ===== Arm "touch every box" animation (same structure as sorting_task) =====
        self._pick_timer = QTimer(self)
        self._pick_timer.setInterval(16)  # ~60 FPS
        self._pick_timer.timeout.connect(self._tick_pick)

        # FSM state
        self._pick_state = "idle"
        self._pick_t = 0
        self._pick_duration = 0
        self._pick_from = (self.arm.shoulder_angle, self.arm.elbow_angle)
        self._pick_to = (self.arm.shoulder_angle, self.arm.elbow_angle)

        # Trigger window + cooldown (same defaults as sorting_task)
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._touch_window_px = 18
        self._touch_cooldown_ms = 120

        # Despawn offset (0 = disappear as soon as touched)
        self._despawn_offset_px = 0

    # ---------- simple spawner ----------
    def _spawn_orange_box(self):
        # BaseTask.ConveyorBeltWidget accepts color names
        self.conveyor.spawn_box(color="orange")

    # ===== Called by existing GUI (LayoutController.start_tasks/stop_tasks) =====
    def start(self):
        # belt
        self.conveyor.setBeltSpeed(120)   # left -> right
        self.conveyor.enable_motion(True)

        if not self._box_timer.isActive():
            self._box_timer.start(1500)  # one orange box every 1.5 seconds

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
        # clear any held-box visual on stop
        self.arm.held_box_visible = False
        self.arm.update()

    # ---------- Arm pick cycle (approach -> descend -> hold -> lift -> present -> return) ----------
    def _pose_home(self):
        return (-90.0, -0.0)

    def _pose_prep(self):
        return (-92.0, -12.0)

    def _pose_pick(self):
        return (-110.0, -95.0)

    def _pose_lift(self):
        return (-93.0, -10.0)

    # Single present pose toward the (orange) container at left of the arm
    # (-90 = up; more negative points further left/down)
    def _pose_present(self):
        return (-220.0, -12.0)

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

        # Despawn slightly later than detection (only while interacting)
        if self._pick_state in ("hold", "lift"):
            self._despawn_if_past_cutoff()

        # segment complete -> next state (fast timings; same angles)
        if t >= 1.0:
            if self._pick_state == "to_prep":
                self._pick_state = "descend"
                self._start_seg(self._pose_pick(), 120)

            elif self._pick_state == "descend":
                self._pick_state = "hold"
                # Show a box in the gripper (orange here, but we sample actual color anyway)
                c = self._color_of_box_in_window() or QColor("#c15800")
                self.arm.held_box_color = c
                self.arm.held_box_visible = True
                self.arm.update()
                self._start_seg(self._pose_pick(), 40)     # brief touch

            elif self._pick_state == "hold":
                self._pick_state = "lift"
                self._start_seg(self._pose_lift(), 120)

            elif self._pick_state == "lift":
                # point toward the container before returning
                self._pick_state = "present"
                self._start_seg(self._pose_present(), 200)

            elif self._pick_state == "present":
                self._pick_state = "return"
                # hide the held box as we head home
                self.arm.held_box_visible = False
                self.arm.update()
                self._start_seg(self._pose_home(), 200)

            elif self._pick_state == "return":
                # brief idle before next box trigger
                self._pick_state = "idle_pause"
                self._start_seg(self._pose_home(), 40)

            elif self._pick_state == "idle_pause":
                self._pick_state = "idle"

    # ---------- helpers ----------
    def _grip_x(self):
        """Single source of truth for the gripper's detection X (edit here to shift detection)."""
        return self.conveyor.width() * 0.40

    def _box_near_grip(self):
        """Detection-only: True if any box is within the window around the gripper."""
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes:
            return False
        grip_x = self._grip_x()
        w = self._touch_window_px
        for x in boxes:
            if (grip_x - w) <= x <= (grip_x + w):
                return True
        return False

    def _despawn_if_past_cutoff(self):
        """Remove a box after it passes the later cutoff (independent of detection)."""
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes:
            return
        colors = getattr(self.conveyor, "_box_colors", None)

        detect_x = self._grip_x()
        cutoff_x = detect_x + self._despawn_offset_px  # 0 => disappear right at touch

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

    def _color_of_box_in_window(self):
        """Return the QColor of the first box currently inside the detection window (or None)."""
        boxes = getattr(self.conveyor, "_boxes", None)
        cols  = getattr(self.conveyor, "_box_colors", None)
        if not boxes or not cols:
            return None
        grip_x = self._grip_x()
        w = self._touch_window_px
        for i, x in enumerate(boxes):
            if (grip_x - w) <= x <= (grip_x + w):
                if i < len(cols):
                    return cols[i]
        return None
