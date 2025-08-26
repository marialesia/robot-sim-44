# tasks/packaging_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer
from .base_task import BaseTask
from .packaging_logic import PackagingWorker  # worker that spawns boxes

class PackagingTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Packaging")

        # ---- Arm visuals (unchanged) ----
        self.arm.shoulder_angle = -90
        self.arm.elbow_angle = 0
        self.arm.c_arm = QColor("#8e44ad")
        self.arm.c_arm_dark = QColor("#6d2e8a")

        # ---- Single container palette ----
        self.container.border = QColor("#c76a1a")
        self.container.fill_top = QColor("#ffe9d3")
        self.container.fill_bottom = QColor("#ffd9b5")
        self.container.rib = QColor(199, 106, 26, 110)

        # ---- Positions (container left, arm centered) ----
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=2, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=3, align=Qt.AlignHCenter | Qt.AlignBottom),
            container=dict(row=1, col=0, align=Qt.AlignRight | Qt.AlignBottom),
            col_stretch=[1, 1], row_stretch=[0, 1]
        )

        # ===== OLD TIMER SPAWNER (kept for reference) =====
        """
        self._box_timer = QTimer(self)
        self._box_timer.timeout.connect(lambda: self.conveyor.spawn_box(color="orange"))
        """

        # ===== Pick-cycle (like Sorting) =====
        self._pick_timer = QTimer(self)
        self._pick_timer.setInterval(16)  # ~60 FPS
        self._pick_timer.timeout.connect(self._tick_pick)

        self._pick_state = "idle"
        self._pick_t = 0
        self._pick_duration = 0
        self._pick_from = (self.arm.shoulder_angle, self.arm.elbow_angle)
        self._pick_to = (self.arm.shoulder_angle, self.arm.elbow_angle)

        # detection window & cooldown
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._touch_window_px = 18
        self._touch_cooldown_ms = 120

        # make box disappear as soon as touched
        self._despawn_offset_px = 0

        # worker handle
        self.worker = None

    # ===== GUI hooks =====
    def start(self):
        # Belt motion
        self.conveyor.setBeltSpeed(120)
        self.conveyor.enable_motion(True)

        # reset pick FSM
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._pick_state = "idle"
        self._pick_t = 0
        if not self._pick_timer.isActive():
            sh, el = self._pose_home()
            self._set_arm(sh, el)
            self._pick_timer.start()

        # Start background worker that spawns orange boxes
        if not self.worker or not self.worker.isRunning():
            self.worker = PackagingWorker(
                pace="medium",     # "slow" | "medium" | "fast"
                color="orange",
                error_rate=0.0     # keep 0 for now; Packaging can use later if needed
            )
            self.worker.box_spawned.connect(self.spawn_box_from_worker)
            self.worker.metrics_ready.connect(self._on_metrics)
            self.worker.start()

        # ===== Old timer start (reference) =====
        """
        if not self._box_timer.isActive():
            self._box_timer.start(1500)
        """

    def stop(self):
        self.conveyor.enable_motion(False)

        if self._pick_timer.isActive():
            self._pick_timer.stop()
        # return arm to home and hide held box
        sh, el = self._pose_home()
        self._set_arm(sh, el)
        self.arm.held_box_visible = False
        self.arm.update()

        if self.worker and self.worker.isRunning():
            self.worker.stop()

        # ===== Old timer stop (reference) =====
        """
        if self._box_timer.isActive():
            self._box_timer.stop()
        """

    # ===== Worker signals =====
    def spawn_box_from_worker(self, box_data):
        color = box_data.get("color", "orange")
        error = box_data.get("error", False)
        self.conveyor.spawn_box(color=color, error=error)

    def _on_metrics(self, metrics):
        print("Packaging metrics:", metrics)

    # ===== Arm poses (mirrors Sorting) =====
    def _pose_home(self):
        return (-90.0, -0.0)   # straight up

    def _pose_prep(self):
        return (-92.0, -12.0)

    def _pose_pick(self):
        return (-110.0, -95.0)

    def _pose_lift(self):
        return (-93.0, -10.0)

    def _pose_present(self):
        """
        Quick 'present' toward the single packaging container.
        (Positive shoulder tilts to the left in our drawing.)
        """
        return (-240.0, -12.0)

    def _set_arm(self, shoulder, elbow):
        self.arm.shoulder_angle = float(shoulder)
        self.arm.elbow_angle = float(elbow)
        self.arm.update()

    def _start_seg(self, to_angles, duration_ms):
        self._pick_from = (self.arm.shoulder_angle, self.arm.elbow_angle)
        self._pick_to = (float(to_angles[0]), float(to_angles[1]))
        self._pick_duration = max(1, int(duration_ms))
        self._pick_t = 0

    # ===== Pick FSM (idle → to_prep → descend → hold → lift → present → return) =====
    def _tick_pick(self):
        self._now_ms += self._pick_timer.interval()

        if self._pick_state == "idle":
            if self._box_near_grip() and (self._now_ms - self._last_touch_time_ms) >= self._touch_cooldown_ms:
                self._last_touch_time_ms = self._now_ms
                self._pick_state = "to_prep"
                self._start_seg(self._pose_prep(), 120)
            else:
                return

        # interpolate pose
        self._pick_t += self._pick_timer.interval()
        t = min(1.0, self._pick_t / float(self._pick_duration))
        s0, e0 = self._pick_from
        s1, e1 = self._pick_to
        self._set_arm(s0 + (s1 - s0) * t, e0 + (e1 - e0) * t)

        # while interacting, despawn touched box immediately
        if self._pick_state in ("hold", "lift"):
            self._despawn_if_past_cutoff()

        if t >= 1.0:
            if self._pick_state == "to_prep":
                self._pick_state = "descend"
                self._start_seg(self._pose_pick(), 120)

            elif self._pick_state == "descend":
                self._pick_state = "hold"
                # show a box in the gripper using the detected box's colour (if any)
                c = self._color_of_box_in_window()
                if c is not None:
                    self.arm.held_box_color = c
                    self.arm.held_box_visible = True
                    self.arm.update()
                self._start_seg(self._pose_pick(), 40)  # brief touch

            elif self._pick_state == "hold":
                self._pick_state = "lift"
                self._start_seg(self._pose_lift(), 120)

            elif self._pick_state == "lift":
                self._pick_state = "present"
                self._start_seg(self._pose_present(), 200)

            elif self._pick_state == "present":
                self._pick_state = "return"
                # drop visual as we return
                self.arm.held_box_visible = False
                self.arm.update()
                self._start_seg(self._pose_home(), 200)

            elif self._pick_state == "return":
                self._pick_state = "idle_pause"
                self._start_seg(self._pose_home(), 40)

            elif self._pick_state == "idle_pause":
                self._pick_state = "idle"

    # ===== Helpers =====
    def _grip_x(self):
        """Where the gripper 'detects' on the belt."""
        return self.conveyor.width() * 0.40

    def _box_near_grip(self):
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes:
            return False
        gx = self._grip_x()
        w = self._touch_window_px
        return any((gx - w) <= x <= (gx + w) for x in boxes)

    def _despawn_if_past_cutoff(self):
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes:
            return
        colors = getattr(self.conveyor, "_box_colors", None)

        detect_x = self._grip_x()
        cutoff_x = detect_x + self._despawn_offset_px  # 0 => disappear on touch

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
        boxes = getattr(self.conveyor, "_boxes", None)
        cols  = getattr(self.conveyor, "_box_colors", None)
        if not boxes or not cols:
            return None
        gx = self._grip_x()
        w = self._touch_window_px
        for i, x in enumerate(boxes):
            if (gx - w) <= x <= (gx + w):
                if i < len(cols):
                    return cols[i]
        return None
