# tasks/packaging_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtWidgets import QLabel
from .base_task import BaseTask

class PackagingTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Packaging")

        # ---- Robot arm visuals ----
        self.arm.shoulder_angle = -90
        self.arm.elbow_angle = 0
        self.arm.c_arm = QColor("#8e44ad")
        self.arm.c_arm_dark = QColor("#6d2e8a")

        # ---- Single packaging container styling ----
        self.container.border = QColor("#c76a1a")
        self.container.fill_top = QColor("#ffe9d3")
        self.container.fill_bottom = QColor("#ffd9b5")
        self.container.rib = QColor(199, 106, 26, 110)

        # ---- Layout: container left, arm centered (unchanged) ----
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=2, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=3, align=Qt.AlignHCenter | Qt.AlignBottom),
            container=dict(row=1, col=0, align=Qt.AlignRight  | Qt.AlignBottom),
            col_stretch=[1, 1], row_stretch=[0, 1]
        )

        # ===== Box spawner (orange) =====
        self._box_timer = QTimer(self)
        self._box_timer.timeout.connect(self._spawn_orange_box)

        # ===== Simple packing counter (0/4) =====
        self._pack_capacity = 4
        self._pack_count = 0
        self._pack_label = QLabel(self.container)
        self._pack_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._pack_label.setStyleSheet(
            "font-weight: 700; font-size: 18px; color: #222;"
            "background: rgba(255,255,255,200);"
            "padding: 2px 8px; border-radius: 8px;"
            "border: 1px solid rgba(0,0,0,60);"
        )
        self._pack_label.setText(f"{self._pack_count}/{self._pack_capacity}")
        self._pack_label.show()

        # Keep label centered if the container resizes
        self.container.installEventFilter(self)
        self._position_pack_label()

        # ===== Minimal arm “pick-present-return” cycle (like sorting) =====
        self._pick_timer = QTimer(self)
        self._pick_timer.setInterval(16)  # ~60 FPS
        self._pick_timer.timeout.connect(self._tick_pick)

        # FSM state
        self._pick_state = "idle"
        self._pick_t = 0
        self._pick_duration = 0
        self._pick_from = (self.arm.shoulder_angle, self.arm.elbow_angle)
        self._pick_to = (self.arm.shoulder_angle, self.arm.elbow_angle)

        # Detection settings
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._touch_window_px = 18
        self._touch_cooldown_ms = 120
        self._despawn_offset_px = 0  # despawn box exactly when “touched”

        # repaint once
        self.arm.update()
        self.conveyor.update()
        self.container.update()

    # ---------- Packing counter helpers ----------
    def _update_pack_label(self):
        self._pack_label.setText(f"{self._pack_count}/{self._pack_capacity}")
        self._position_pack_label()

    def _position_pack_label(self):
        w = self.container
        lbl = self._pack_label
        x = (w.width() - lbl.width()) // 2
        y = (w.height() - lbl.height()) // 2
        lbl.move(max(0, x), max(0, y))

    def _on_item_packed(self):
        if self._pack_count < self._pack_capacity:
            self._pack_count += 1
        self._update_pack_label()

    # ---------- Spawning ----------
    def _spawn_orange_box(self):
        # BaseTask.ConveyorBeltWidget handles strings like "orange"
        self.conveyor.spawn_box(color="orange")

    # ---------- Lifecycle ----------
    def start(self):
        # Belt motion
        self.conveyor.setBeltSpeed(120)
        self.conveyor.enable_motion(True)
        if not self._box_timer.isActive():
            self._box_timer.start(1500)  # one orange box every 1.5s

        # Reset packing counter at run start
        self._pack_count = 0
        self._update_pack_label()

        # Start arm FSM
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._pick_state = "idle"
        self._pick_t = 0
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

        # Return arm to home and clear held box
        sh, el = self._pose_home()
        self._set_arm(sh, el)
        self.arm.held_box_visible = False
        self.arm.update()

    # ---------- Arm poses (very close to sorting’s) ----------
    def _pose_home(self):
        return (-90.0, 0.0)

    def _pose_prep(self):
        return (-92.0, -12.0)

    def _pose_pick(self):
        return (-110.0, -95.0)

    def _pose_lift(self):
        return (-93.0, -10.0)

    def _pose_present(self):
        """
        Quick 'present' toward the single packaging container.
        You previously preferred pointing down-left; keep that pose.
        """
        return (-240.0, -12.0)

    # ---------- FSM plumbing ----------
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
        # Global time
        self._now_ms += self._pick_timer.interval()

        # If idle, only start a cycle when a box is near the gripper
        if self._pick_state == "idle":
            if self._box_near_grip() and (self._now_ms - self._last_touch_time_ms) >= self._touch_cooldown_ms:
                self._last_touch_time_ms = self._now_ms
                self._pick_state = "to_prep"
                self._start_seg(self._pose_prep(), 120)
            else:
                return

        # Interpolate current segment
        self._pick_t += self._pick_timer.interval()
        t = min(1.0, self._pick_t / float(self._pick_duration))
        s0, e0 = self._pick_from
        s1, e1 = self._pick_to
        s = s0 + (s1 - s0) * t
        e = e0 + (e1 - e0) * t
        self._set_arm(s, e)

        # While interacting, despawn the touched box immediately
        if self._pick_state in ("hold", "lift"):
            self._despawn_if_past_cutoff()

        # Segment complete -> next state
        if t >= 1.0:
            if self._pick_state == "to_prep":
                self._pick_state = "descend"
                self._start_seg(self._pose_pick(), 120)

            elif self._pick_state == "descend":
                self._pick_state = "hold"
                # Show a box in the gripper using the detected box's colour (if any)
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
                # Count this as a packed item
                self._on_item_packed()

                self._pick_state = "return"
                # Hide the held box as we head home
                self.arm.held_box_visible = False
                self.arm.update()
                self._start_seg(self._pose_home(), 200)

            elif self._pick_state == "return":
                # brief idle before next trigger
                self._pick_state = "idle_pause"
                self._start_seg(self._pose_home(), 40)

            elif self._pick_state == "idle_pause":
                self._pick_state = "idle"

    # ---------- Helpers (shared style with sorting) ----------
    def _grip_x(self):
        """X-position where the gripper 'touches' boxes on the belt."""
        return self.conveyor.width() * 0.40

    def _box_near_grip(self):
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes:
            return False
        gx = self._grip_x()
        w = self._touch_window_px
        for x in boxes:
            if (gx - w) <= x <= (gx + w):
                return True
        return False

    def _despawn_if_past_cutoff(self):
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes:
            return
        colors = getattr(self.conveyor, "_box_colors", None)
        detect_x = self._grip_x()
        cutoff_x = detect_x + self._despawn_offset_px  # 0 -> vanish immediately on touch

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

    # ---------- Keep the counter label centered ----------
    def eventFilter(self, obj, event):
        if obj is self.container and event.type() == QEvent.Resize:
            self._position_pack_label()
        return super().eventFilter(obj, event)
