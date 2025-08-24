# tasks/sorting_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSizePolicy
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
        # Blue - reusing the built-in container
        self.container_blue = self.container
        self.container_blue.border = QColor("#2b4a91")
        self.container_blue.fill_top = QColor("#dbe8ff")
        self.container_blue.fill_bottom = QColor("#c7daff")
        self.container_blue.rib = QColor(43, 74, 145, 120)

        # Red
        self.container_red = StorageContainerWidget()
        self.container_red.border = QColor("#8c1f15")
        self.container_red.fill_top = QColor("#ffd6d1")
        self.container_red.fill_bottom = QColor("#ffb8b0")
        self.container_red.rib = QColor(140, 31, 21, 120)

        # Green
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
            arm=dict(row=0, col=0, colSpan=6, align=Qt.AlignHCenter | Qt.AlignBottom),  # Change the position of the arm here
            col_stretch=[1, 1, 1],
            row_stretch=[0, 0, 1],
            spacing=18
        )

        '''
        # Place all containers on the same row
        # self.grid.addWidget(widget, row, column, rowSpan, columnSpan, alignment) 
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
        '''
        # Group all containers into one tight horizontal row (centered)
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        # Keep each container compact so the row doesn't stretch across the whole window
        for w in (self.container_red, self.container_blue, self.container_green,
                  self.container_purple, self.container_orange, self.container_teal):
            w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
            row_layout.addWidget(w)

        # Add the row to the same grid area where your containers were (row 3), span all 6 columns
        self.grid.addWidget(row, 3, 0, 1, 6, Qt.AlignHCenter | Qt.AlignTop)


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

        # --- Despawn offset (independent of detection) ---
        self._despawn_offset_px = 0  # +pixels to the RIGHT of detection; increase = disappears later

        # --- remember which container direction to "present" toward after lift ---
        self._target_slot = None  # one of: red/blue/green/purple/orange/teal

        # --- capture color at trigger-time to avoid races ---
        self._pending_color = None  # color captured exactly when the cycle starts

    # ===== Called by your existing GUI =====
    def start(self):
        # belt motion
        self.conveyor.setBeltSpeed(120)   # left -> right
        self.conveyor.enable_motion(True)

        # start spawning boxes periodically
        if not self._box_timer.isActive():
            # self._box_timer.start(800)    # one box every 0.8s
            self._box_timer.start(2000)    # one box every 2.0s

        # reset trigger state so we can fire immediately after a Stop
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._pick_state = "idle"
        self._pick_t = 0
        self._target_slot = None  # reset target on start
        self._pending_color = None

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

    # Quick 'pointing' poses toward each container’s general direction
    # (arm rotation from base, elbow rotation)
    # -90 is directly up
    def _pose_present(self, slot):
        poses = {
            "red":    (-200.0, -8.0),   # far left
            "blue":   (-220.0, -10.0),  # left-mid
            "green":  (-240.0, -12.0),  # slightly left of center
            "purple": (60.0,  12.0),    # slightly right of center
            "orange": (40.0,  10.0),    # right-mid
            "teal":   (20.0,  8.0),     # far right
        }
        return poses.get(slot, self._pose_lift())

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

                # Lock color & slot at trigger time (more reliable than sampling later)
                self._pending_color = self._color_of_box_in_window()
                self._target_slot = self._color_to_slot(self._pending_color) if self._pending_color else None

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
                # Prefer a live sample; fall back to the color we locked at trigger time
                c = self._color_of_box_in_window() or self._pending_color
                if c is not None:
                    self.arm.held_box_color = c
                    self.arm.held_box_visible = True
                    # remember which direction to present toward
                    self._target_slot = self._color_to_slot(c)
                    self.arm.update()
                self._start_seg(self._pose_pick(), 40)     # brief touch

            elif self._pick_state == "hold":
                self._pick_state = "lift"
                self._start_seg(self._pose_lift(), 120)

            elif self._pick_state == "lift":
                # point toward the matching container before returning
                if self._target_slot:
                    self._pick_state = "present"
                    self._start_seg(self._pose_present(self._target_slot), 200)
                else:
                    self._pick_state = "return"
                    self.arm.held_box_visible = False
                    self.arm.update()
                    self._start_seg(self._pose_home(), 160)

            elif self._pick_state == "present":
                self._pick_state = "return"
                # hide the held box as we head home
                self.arm.held_box_visible = False
                self.arm.update()
                self._start_seg(self._pose_home(), 200)

            elif self._pick_state == "return":
                # brief idle before next box trigger
                self._pick_state = "idle_pause"
                self._target_slot = None
                self._pending_color = None
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
        grip_x = self._grip_x()  # unified detection X
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

        # Use the same detection X as the gripper trigger
        detect_x = self._grip_x()
        cutoff_x = detect_x + self._despawn_offset_px  # set offset to 0 so the box disappears as soon as its touched (line 133)

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
        grip_x = self._grip_x()  # unified detection X
        w = self._touch_window_px
        for i, x in enumerate(boxes):
            if (grip_x - w) <= x <= (grip_x + w):
                if i < len(cols):
                    return cols[i]
        return None

    # Map a QColor to a slot name matching the containers
    def _color_to_slot(self, qcolor):
        try:
            key = qcolor.name().lower()
        except Exception:
            return None
        if key == "#c82828":
            return "red"
        if key == "#2b4a91":
            return "blue"
        if key == "#1f7a3a":
            return "green"
        if key == "#6a1b9a":
            return "purple"
        if key == "#c15800":
            return "orange"
        if key == "#b8efe6":
            return "teal"
        return None
