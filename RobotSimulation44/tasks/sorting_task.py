# tasks/sorting_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSizePolicy, QLabel
from .base_task import BaseTask, StorageContainerWidget
from .sorting_logic import SortingWorker
from audio_manager import AudioManager
import random  # for picking a wrong bin on purpose when worker flags an error
from event_logger import get_logger 


class SortingTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Sorting")

        # ---- Audio ----
        self.audio = AudioManager()

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

        # --- Clickable containers: map slot -> widget and install event filters ---
        self._slot_to_widget = {
            "red":    self.container_red,
            "blue":   self.container_blue,
            "green":  self.container_green,
            "purple": self.container_purple,
            "orange": self.container_orange,
            "teal":   self.container_teal,
        }
        for slot, w in self._slot_to_widget.items():
            w._slot = slot  # tag widget for click handling
            w.installEventFilter(self)

        # --- Error move model ---
        self._errors = {}                                # id -> {id,color,actual,current}
        self._bin_errors = {k: [] for k in self._slot_to_widget.keys()}  # slot -> [ids]
        self._next_eid = 1
        self._selected_error = None                      # currently “picked up” error id (or None)

        # Save original borders so we can highlight & restore
        self._orig_borders = {k: w.border for k, w in self._slot_to_widget.items()}

        # Color map for error colors
        self._slot_color_map = {
            "red": QColor("#c82828"),
            "blue": QColor("#2b4a91"),
            "green": QColor("#1f7a3a"),
            "purple": QColor("#6a1b9a"),
            "orange": QColor("#c15800"),
            "teal": QColor("#b8efe6"),
        }

        # ---- Exclamation badges (one per bin) ----
        self._badges = {}
        self._create_error_badges()

        # ---- Flashing outline timer for bins with errors ----
        self._flash_on = False
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(350)   # speed of flash
        self._flash_timer.timeout.connect(self._flash_tick)

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
        self._present_slot_override = None  # when worker says incorrect, we aim here

        # --- capture color at trigger-time to avoid races ---
        self._pending_color = None  # color captured exactly when the cycle starts

        # --- initialize worker ---
        self.worker = None

    # ===== Called by your existing GUI =====
    def start(self, pace=None, bin_count=None, error_rate=None):
        # belt motion
        self.conveyor.setBeltSpeed(120)   # left -> right
        self.conveyor.enable_motion(True)

        # reset trigger state so we can fire immediately after a Stop
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._pick_state = "idle"
        self._pick_t = 0
        self._target_slot = None  # reset target on start
        self._present_slot_override = None
        self._pending_color = None

        # start arm pick monitor
        if not self._pick_timer.isActive():
            sh, el = self._pose_home()
            self._set_arm(sh, el)
            self._pick_timer.start()

        # start flashing timer
        if not self._flash_timer.isActive():
            self._flash_timer.start()

        # ===== start the worker logic =====
        if self.worker is None:
            # first time: create worker
            self.worker = SortingWorker(
                pace=pace,
                bin_count=bin_count,
                error_rate=error_rate
            )
            self.worker.box_spawned.connect(self.spawn_box_from_worker)
            self.worker.box_sorted.connect(self._on_box_sorted)
            self.worker.metrics_live.connect(self._on_metrics_live)
            self.worker.start()
        elif not self.worker.isRunning():
            # worker exists but was paused: resume
            self.worker.running = True
            if not self.worker.isRunning():
                self.worker.start()

    def pause(self):
        self.conveyor.enable_motion(False)
        if self._box_timer.isActive():
            self._box_timer.stop()
        if self._pick_timer.isActive():
            self._pick_timer.stop()
        if self._flash_timer.isActive():
            self._flash_timer.stop()

        # reset borders and hide badges
        for slot, w in self._slot_to_widget.items():
            w.border = self._orig_borders.get(slot, w.border)
            w.update()
        for b in self._badges.values():
            b.hide()

        # return arm to home
        sh, el = self._pose_home()
        self._set_arm(sh, el)
        # clear any held-box visual on pause
        self.arm.held_box_visible = False
        self.arm.update()

        # clear highlight if any selection
        if self._selected_error is not None:
            for slot in self._slot_to_widget.keys():
                self._highlight_bin(slot, False)
            self._selected_error = None

        # ===== pause the worker logic =====
        if self.worker and self.worker.isRunning():
            self.worker.pause()

    def stop(self):
        # ===== stop motions =====
        self.conveyor.enable_motion(False)

        if self._box_timer.isActive():
            self._box_timer.stop()
        if self._pick_timer.isActive():
            self._pick_timer.stop()
        if self._flash_timer.isActive():
            self._flash_timer.stop()

        # ===== clear all boxes from the conveyor =====
        if hasattr(self.conveyor, "_boxes"):
            self.conveyor._boxes.clear()
        if hasattr(self.conveyor, "_box_colors"):
            self.conveyor._box_colors.clear()
        self.conveyor.update()

        # reset borders and hide badges
        for slot, w in self._slot_to_widget.items():
            w.border = self._orig_borders.get(slot, w.border)
            w.update()
        for b in self._badges.values():
            b.hide()

        # return arm to home
        sh, el = self._pose_home()
        self._set_arm(sh, el)
        self.arm.held_box_visible = False
        self.arm.update()

        # clear highlight if any selection
        if self._selected_error is not None:
            for slot in self._slot_to_widget.keys():
                self._highlight_bin(slot, False)
            self._selected_error = None

        # ===== stop worker logic =====
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker = None   # fully drop it so we must re-create on start

        # ===== reset metrics (optional) =====
        if hasattr(self, "metrics_manager"):
            self.metrics_manager.reset_metrics()


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
                # --- Trigger sorting only when arm reaches box ---
                nearest_color = self._color_of_box_in_window()
                if nearest_color:
                    hex_color = nearest_color.name() if hasattr(nearest_color, "name") else nearest_color
                    COLOR_MAP = {
                        "#c82828": "red",
                        "#2b4a91": "blue",
                        "#1f7a3a": "green",
                        "#6a1b9a": "purple",
                        "#c15800": "orange",
                        "#b8efe6": "teal"
                    }
                    self.worker.sort_box(COLOR_MAP.get(hex_color, "unknown"))

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
                # Prefer the worker's outcome if it has arrived (may point to a wrong bin)
                slot_to_use = self._present_slot_override or self._target_slot
                if slot_to_use:
                    self._pick_state = "present"
                    self._start_seg(self._pose_present(slot_to_use), 200)
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
                self._present_slot_override = None
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

    # --- helper to get nearest box color ---
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

    # Pick a wrong bin (used when worker flags an incorrect sort)
    def _wrong_slot_for(self, slot):
        candidates = ["red", "blue", "green", "purple", "orange", "teal"]
        try:
            candidates.remove(slot)
        except ValueError:
            pass
        return random.choice(candidates) if candidates else slot

    # ===== Click handling / event filter =====
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            slot = getattr(obj, "_slot", None)
            if slot:
                self._on_container_clicked(slot)
                return True
        elif event.type() == QEvent.Resize:
            # Keep the badge centered at the top inside each container
            slot = getattr(obj, "_slot", None)
            if slot:
                self._position_badge(slot)
        return super().eventFilter(obj, event)

    def _highlight_bin(self, slot, on):
        w = self._slot_to_widget.get(slot)
        if not w:
            return
        if on:
            w.border = QColor("#ffbf00")  # amber highlight while “holding”
        else:
            w.border = self._orig_borders.get(slot, w.border)
        w.update()

    def _current_selected_slot(self):
        """Return the slot of the currently selected (held) error, if any."""
        if self._selected_error is None:
            return None
        rec = self._errors.get(self._selected_error)
        return rec['current'] if rec else None

    # ---- badges ----
    def _create_error_badges(self):
        """Create a small colored '!' badge for each bin (initially hidden)."""
        for slot, w in self._slot_to_widget.items():
            lbl = QLabel("!", w)
            lbl.setFixedSize(22, 22)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            lbl.setStyleSheet(
                "color: white; background: rgba(0,0,0,0); border-radius: 11px; "
                "font-weight: 800; font-size: 14px;"
            )
            lbl.hide()
            self._badges[slot] = lbl
            self._position_badge(slot)

    def _position_badge(self, slot):
        """Center the badge along the top inside the container."""
        w = self._slot_to_widget.get(slot)
        b = self._badges.get(slot)
        if not w or not b:
            return
        x = (w.width() - b.width()) // 2
        y = 2  # just inside the top edge
        b.move(max(0, x), max(0, y))

    def _apply_flash_colors(self):
        """Apply flashing borders per-bin based on oldest unresolved error, and update badges."""
        selected_slot = self._current_selected_slot()
        for slot, w in self._slot_to_widget.items():
            ids = self._bin_errors.get(slot, [])
            badge = self._badges.get(slot)

            if ids:
                head = ids[0]
                rec = self._errors.get(head)
                if rec:
                    # Border flashing
                    flash_q = self._slot_color_map.get(
                        rec['color'], self._orig_borders.get(slot, w.border)
                    )
                    if slot != selected_slot:  # selection highlight takes priority
                        w.border = flash_q if self._flash_on else self._orig_borders.get(slot, w.border)
                        w.update()

                    # Badge: solid colored circle with white "!"
                    if badge:
                        q = self._slot_color_map.get(rec['color'])
                        if q:
                            badge.setStyleSheet(
                                "color: white; "
                                f"background: {q.name()}; "
                                f"border: 2px solid {q.darker(130).name()}; "
                                "border-radius: 11px; font-weight: 800; font-size: 14px;"
                            )
                            badge.show()
            else:
                # No errors -> restore original + hide badge
                if w.border != self._orig_borders.get(slot, w.border) and slot != selected_slot:
                    w.border = self._orig_borders.get(slot, w.border)
                    w.update()
                if badge:
                    badge.hide()

    def _flash_tick(self):
        self._flash_on = not self._flash_on
        self._apply_flash_colors()

    def _on_container_clicked(self, slot):
        # Always log the user click
        get_logger().log_user("Sorting", f"container_{slot}", "click", "container clicked")

        # No selection yet: try to pick one error from this wrong bin
        if self._selected_error is None:
            ids = self._bin_errors.get(slot, [])
            if not ids:
                print(f"(Sorting Task: No errors in {slot} to pick up)")
                get_logger().log_user("Sorting", f"container_{slot}", "click", "no errors to pick up")
                return
            eid = ids.pop(0)  # FIFO: one error per click
            rec = self._errors.get(eid)
            if not rec:
                return
            self._selected_error = eid
            self._highlight_bin(slot, True)
            msg = (f"Sorting Task: Picked error #{eid}: {rec['color']} currently in {slot}. "
                   f"Click the correct container ({rec['actual']}).")
            print(msg)
            get_logger().log_user("Sorting", f"container_{slot}", "pick", f"eid={eid}, color={rec['color']}, needs={rec['actual']}")

            #play "correct" sound when box is fixed
            self.audio.play_correct_chime_()

            # update flashing/badges immediately (selected bin should stop flashing)
            self._apply_flash_colors()
            return

        # We’re holding an error; drop it onto the clicked bin
        eid = self._selected_error
        rec = self._errors.get(eid)
        if not rec:
            self._selected_error = None
            self._apply_flash_colors()
            return

        # Remove highlight from previous bin
        self._highlight_bin(rec['current'], False)
        prev = rec['current']
        new_slot = slot

        # Clean up any stale membership from previous bin
        try:
            if eid in self._bin_errors.get(prev, []):
                self._bin_errors[prev].remove(eid)
        except ValueError:
            pass

        rec['current'] = new_slot

        if new_slot == rec['actual']:
            # Resolved!
            print(f"Sorting Task: Resolved error #{eid}: moved {rec['color']} to {new_slot} ✅")
            get_logger().log_user("Sorting", f"container_{new_slot}", "drop", f"resolved eid={eid}, color={rec['color']}")
            try:
                if eid in self._bin_errors.get(new_slot, []):
                    self._bin_errors[new_slot].remove(eid)
            except ValueError:
                pass
            del self._errors[eid]
            self._selected_error = None
        else:
            # Still wrong: place into this bin and keep “holding” it
            self._bin_errors[new_slot].append(eid)
            self._selected_error = eid
            self._highlight_bin(new_slot, True)
            print(f"Sorting Task: Moved error #{eid} onto {new_slot} (needs {rec['actual']}). Click again to fix.")
            get_logger().log_user("Sorting", f"container_{new_slot}", "drop", f"still wrong eid={eid}, needs={rec['actual']}")

        # Refresh flashing + badges to reflect new oldest-error colors per bin
        self._apply_flash_colors()

    # ===== Worker signal handlers =====
    def _on_box_spawned(self, box_data):
        color = box_data["color"]
        error = box_data["error"]

    def _on_box_sorted(self, color, correct):
        # color is a string like "red", "blue", etc.
        valid = {"red", "blue", "green", "purple", "orange", "teal"}
        if color not in valid:
            return

        if correct:
            self._present_slot_override = color
            into = color
            msg = f"Sorting Task: sorted {color} into {into} ✅ correct"
            print(msg)
            get_logger().log_robot("Sorting", msg)
            # play a "correct" sound
            self.audio.play_correct_chime()
        else:
            wrong = self._present_slot_override or self._wrong_slot_for(color)
            self._present_slot_override = wrong
            into = wrong

            # create an error record living in the wrong bin
            eid = self._next_eid
            self._next_eid += 1
            rec = {"id": eid, "color": color, "actual": color, "current": into}
            self._errors[eid] = rec
            self._bin_errors[into].append(eid)

            msg = f"Sorting Task: sorted {color} into {into} ❌ error (expected {color})"
            print(msg)
            get_logger().log_robot("Sorting", msg)

            # play an "incorrect" sound
            self.audio.play_incorrect_chime()

            # Update flashing/badges immediately so the bin shows this (oldest) error color
            self._apply_flash_colors()

    def _on_metrics_live(self, metrics):
        """Receive live metrics from the worker and update MetricsManager in real time."""
        if hasattr(self, "metrics_manager") and self.metrics_manager:
            self.metrics_manager.update_metrics(metrics)
        else:
            # fallback for debugging
            print("Live metrics:", metrics)

    def spawn_box_from_worker(self, box_data):
        """Called when worker wants to spawn a box."""
        color = box_data["color"]
        error = box_data["error"]
        # Spawn the box with color and error info
        self.conveyor.spawn_box(color=color, error=error)
