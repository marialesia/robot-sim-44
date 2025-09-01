# tasks/packaging_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer, QEvent, QPropertyAnimation
from PyQt5.QtWidgets import QLabel, QGraphicsOpacityEffect, QHBoxLayout, QSizePolicy, QWidget
from .base_task import BaseTask, StorageContainerWidget
import random

class PackagingTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Packaging")

        # ---- Robot arm visuals ----
        self.arm.shoulder_angle = -90
        self.arm.elbow_angle = 0
        self.arm.c_arm = QColor("#8e44ad")
        self.arm.c_arm_dark = QColor("#6d2e8a")

        # ---- Single packaging container styling (this will be the LEFTMOST of the row) ----
        self.container.border = QColor("#c76a1a")
        self.container.fill_top = QColor("#ffe9d3")
        self.container.fill_bottom = QColor("#ffd9b5")
        self.container.rib = QColor(199, 106, 26, 110)

        # ---- Layout: keep conveyor + arm the same; we'll replace the container with a row of 4 ----
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=2, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=2, align=Qt.AlignHCenter | Qt.AlignBottom),
            # we temporarily place the single container, then immediately replace it with a row
            container=dict(row=1, col=0, align=Qt.AlignRight | Qt.AlignBottom),
            col_stretch=[1, 1], row_stretch=[0, 1]
        )

        # --- Build a compact row of 4 containers (primary + 3 more to its right) ---
        self.grid.removeWidget(self.container)  # take it out to put into the row

        # Create 3 additional containers (same style for now)
        self.container_b = StorageContainerWidget()
        self.container_c = StorageContainerWidget()
        self.container_d = StorageContainerWidget()
        for w in (self.container_b, self.container_c, self.container_d):
            w.border = QColor("#c76a1a")
            w.fill_top = QColor("#ffe9d3")
            w.fill_bottom = QColor("#ffd9b5")
            w.rib = QColor(199, 106, 26, 110)

        # Make a tight row widget to hold all four
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        for w in (self.container, self.container_b, self.container_c, self.container_d):
            w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
            row_layout.addWidget(w)

        # Add the row where the single container was; span across both columns to keep it near the arm
        self.grid.addWidget(row, 1, 0, 1, 2, Qt.AlignRight | Qt.AlignBottom)

        # ===== Box spawner (orange) =====
        self._box_timer = QTimer(self)
        self._box_timer.timeout.connect(self._spawn_orange_box)

        # ===== Fade-out on full (applies to the PRIMARY container only) =====
        self._fade_effect = QGraphicsOpacityEffect(self.container)
        self.container.setGraphicsEffect(self._fade_effect)
        self._fade_effect.setOpacity(1.0)

        self._fade_anim = QPropertyAnimation(self._fade_effect, b"opacity", self)
        self._fade_anim.setDuration(2000)  # 2s to fade to invisible
        self._fade_anim.finished.connect(self.container.hide)
        self._fade_started = False

        # ===== Simple packing counter — label sits on the PRIMARY container =====
        self._pack_capacity = 0
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

        # Keep label centered if the PRIMARY container resizes
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
        self.container_b.update()
        self.container_c.update()
        self.container_d.update()

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

        # Start fade-out once when capacity is reached
        if self._pack_count >= self._pack_capacity and not self._fade_started:
            self._fade_started = True
            self._fade_anim.stop()
            self._fade_effect.setOpacity(1.0)
            self._fade_anim.setStartValue(1.0)
            self._fade_anim.setEndValue(0.0)
            self._fade_anim.start()

    # ---------- Spawning ----------
    def _spawn_orange_box(self):
        # BaseTask.ConveyorBeltWidget handles strings like "orange"
        self.conveyor.spawn_box(color="orange")

    # ---------- Lifecycle ----------
    def start(self):
        # Pick a capacity for this run: 4, 5, or 6
        self._pack_capacity = random.choice((4, 5, 6))

        # Belt motion
        self.conveyor.setBeltSpeed(120)
        self.conveyor.enable_motion(True)
        if not self._box_timer.isActive():
            self._box_timer.start(1500)  # one orange box every 1.5s

        # Reset packing counter and refresh the label to show "0/<capacity>"
        self._pack_count = 0
        self._update_pack_label()

        # Make sure the container is visible at the start of each run
        if hasattr(self, "_hide_timer") and self._hide_timer.isActive():
            self._hide_timer.stop()
        self.container.show()

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

    # ---------- Arm poses ----------
    def _pose_home(self):
        return (-90.0, 0.0)

    def _pose_prep(self):
        return (-92.0, -12.0)

    def _pose_pick(self):
        return (-110.0, -95.0)

    def _pose_lift(self):
        return (-93.0, -10.0)

    def _pose_present(self):
        """Present toward the row (still aimed at the primary/leftmost)."""
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
                # Count this as a packed item (into the PRIMARY container)
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

    # ---------- Helpers ----------
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

    # ---------- Keep the counter label centered on the PRIMARY container ----------
    def eventFilter(self, obj, event):
        if obj is self.container and event.type() == QEvent.Resize:
            self._position_pack_label()
        return super().eventFilter(obj, event)
