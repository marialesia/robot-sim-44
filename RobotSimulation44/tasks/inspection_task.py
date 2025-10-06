# tasks/inspection_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer, QEvent, QPropertyAnimation, QRect
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSizePolicy, QLabel
from .base_task import BaseTask, StorageContainerWidget
from .inspection_logic import InspectionWorker
from event_logger import get_logger
import random
import time
from audio_manager import AudioManager


class InspectionTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Inspection")

        # Robot arm visuals
        self.arm.shoulder_angle = -90
        self.arm.elbow_angle = -0
        self.arm.c_arm = QColor("#27ae60")
        self.arm.c_arm_dark = QColor("#1e8449")

        # Two containers: LEFT = green, RIGHT = red
        self.container_green = self.container
        self.container_green.border = QColor("#1f7a3a")
        self.container_green.fill_top = QColor("#d9f7e6")
        self.container_green.fill_bottom = QColor("#bff0d3")
        self.container_green.rib = QColor(31, 122, 58, 110)

        self.container_red = StorageContainerWidget()
        self.container_red.border = QColor("#8c1f15")
        self.container_red.fill_top = QColor("#ffd6d1")
        self.container_red.fill_bottom = QColor("#ffb8b0")
        self.container_red.rib = QColor(140, 31, 21, 110)

        # Layout: conveyor & arm top; containers in a compact row below
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=3, align=Qt.AlignTop), # Change the position of the conveyor belt here
            arm=dict(row=0, col=0, colSpan=3, align=Qt.AlignHCenter | Qt.AlignBottom), # Change the position of the arm here
            container=dict(row=2, col=1, align=Qt.AlignHCenter | Qt.AlignVCenter),  # Placeholder
            col_stretch=[1, 1, 1],
            row_stretch=[0, 0, 1],
            spacing=24
        )

        # Remove the green container from the grid if it already exists
        try:
            self.grid.removeWidget(self.container_green)
        except Exception:
            pass

        # Group all containers into one tight horizontal row (centered)
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        # Set size policies so both containers stay evenly sized and expand vertically
        self.container_green.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.container_red.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # Add both containers to the row layout with spacing between them
        row_layout.addWidget(self.container_green)
        row_layout.addSpacing(160)
        row_layout.addWidget(self.container_red)

        # Add the row layout into the main grid layout, centered horizontally
        self.grid.addWidget(row, 3, 0, 1, 3, Qt.AlignHCenter | Qt.AlignTop)

        # Clickable containers & badges/flash
        self._slot_to_widget = {
            "green": self.container_green,
            "red":   self.container_red,
        }
        for slot, w in self._slot_to_widget.items():
            w._slot = slot
            w.installEventFilter(self)

        # Initialize error tracking
        self._errors = {}
        self._bin_errors = {k: [] for k in self._slot_to_widget.keys()}
        self._next_eid = 1
        self._selected_error = None

        # Original border colors
        self._orig_borders = {k: w.border for k, w in self._slot_to_widget.items()}
        self._slot_color_map = {
            "green": QColor("#1f7a3a"),
            "red":   QColor("#c82828"),
        }

        # Drag ghost for error correction
        self._drag_label = None        # QLabel that follows mouse
        self._drag_color = None        # QColor of the carried box
        self._drag_timer = QTimer(self)
        self._drag_timer.setInterval(16)   # ~60fps
        self._drag_timer.timeout.connect(self._update_drag_ghost)

        # Badges
        self._badges = {}
        self._create_error_badges()

        # Flashing
        self._flash_on = False
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(350)
        self._flash_timer.timeout.connect(self._flash_tick)

        # Repaint
        self.arm.update()
        self.conveyor.update()
        self.container_green.update()
        self.container_red.update()

        # Existing box spawner (legacy, disabled once worker is used)
        self._box_timer = QTimer(self)
        self._box_timer.timeout.connect(self.conveyor.spawn_box)

        # Arm "touch a box" animation
        self._pick_timer = QTimer(self)
        self._pick_timer.setInterval(16)
        self._pick_timer.timeout.connect(self._tick_pick)

        # FSM state
        self._pick_state = "idle"
        self._pick_t = 0
        self._pick_duration = 0
        self._pick_from = (self.arm.shoulder_angle, self.arm.elbow_angle)
        self._pick_to = (self.arm.shoulder_angle, self.arm.elbow_angle)

        # Trigger settings
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._touch_window_px = 18
        self._touch_cooldown_ms = 120

        # Despawn offset
        self._despawn_offset_px = 0

        # Target slot for present
        self._target_slot = None
        self._present_slot_override = None
        self._pending_color = None

        # For Reaction time
        self._error_start_times = {}
        # For correction accuracy
        self._total_corrections = 0
        self._correct_corrections = 0

        # Worker
        self.worker = None

        # Audio
        self.audio = AudioManager()
        self._alarm_active = False

    # Called by the observer GUI
    def start(self, pace=None, error_rate=None, error_rate_percent=None):
        # Guard: only run if this task is enabled
        if not getattr(self, "enabled", True):
            return

        # Belt motion
        self.conveyor.setBeltSpeed(120)
        self.conveyor.enable_motion(True)

        # reset trigger state so we can fire immediately after a Stop
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._pick_state = "idle"
        self._pick_t = 0
        self._target_slot = None
        self._present_slot_override = None
        self._pending_color = None

        # reset metrics when new task is started
        if hasattr(self, "metrics_manager"):
            self.metrics_manager.reset_metrics()

        # Start arm pick monitor
        if not self._pick_timer.isActive():
            sh, el = self._pose_home()
            self._set_arm(sh, el)
            self._pick_timer.start()

        # Start flashing timer
        if not self._flash_timer.isActive():
            self._flash_timer.start()

        # Start the worker logic
        if self.worker is None:
            self.worker = InspectionWorker(
                pace=pace,
                error_rate=error_rate,
                error_rate_percent=error_rate_percent
            )
            self.worker.box_spawned.connect(self.spawn_box_from_worker)
            self.worker.box_sorted.connect(self._on_box_sorted)
            self.worker.metrics_live.connect(self._on_metrics_live)
            self.worker.start()
        elif not self.worker.isRunning():
            self.worker.running = True
            if not self.worker.isRunning():
                self.worker.start()
    
        # Playing conveyor sound
        self.play_sound("conveyor")


    def complete(self):
        # Stop motions
        self.conveyor.enable_motion(False)
        if self._box_timer.isActive():
            self._box_timer.stop()
        if self._pick_timer.isActive():
            self._pick_timer.stop()
        if self._flash_timer.isActive():
            self._flash_timer.stop()

        #Stop conveyor sound and alarm
        self.audio.stop_alarm()
        self.audio.stop_conveyor()

        # Clear all boxes from the conveyor
        if hasattr(self.conveyor, "_boxes"):
            self.conveyor._boxes.clear()
        if hasattr(self.conveyor, "_box_colors"):
            self.conveyor._box_colors.clear()
        self.conveyor.update()

        # Reset borders and hide badges
        for slot, w in self._slot_to_widget.items():
            w.border = self._orig_borders.get(slot, w.border)
            w.update()
        for b in self._badges.values():
            b.hide()

        # Return arm to home
        sh, el = self._pose_home()
        self._set_arm(sh, el)
        self.arm.held_box_visible = False
        self.arm.update()

        # Clear highlight if any selection
        if self._selected_error is not None:
            for slot in self._slot_to_widget.keys():
                self._highlight_bin(slot, False)
            self._selected_error = None

        # Stop worker logic
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker = None

        # Reset correction counters
        self._total_corrections = 0
        self._correct_corrections = 0

    def stop(self):
        # Stop motions
        self.conveyor.enable_motion(False)
        if self._box_timer.isActive():
            self._box_timer.stop()
        if self._pick_timer.isActive():
            self._pick_timer.stop()
        if self._flash_timer.isActive():
            self._flash_timer.stop()

        # Stop conveyor sound and alarm
        self.audio.stop_alarm()
        self.audio.stop_conveyor()

        # Clear all boxes from the conveyor
        if hasattr(self.conveyor, "_boxes"):
            self.conveyor._boxes.clear()
        if hasattr(self.conveyor, "_box_colors"):
            self.conveyor._box_colors.clear()
        self.conveyor.update()

        # Reset borders and hide badges
        for slot, w in self._slot_to_widget.items():
            w.border = self._orig_borders.get(slot, w.border)
            w.update()
        for b in self._badges.values():
            b.hide()

        # Return arm to home
        sh, el = self._pose_home()
        self._set_arm(sh, el)
        self.arm.held_box_visible = False
        self.arm.update()

        # Clear highlight if any selection
        if self._selected_error is not None:
            for slot in self._slot_to_widget.keys():
                self._highlight_bin(slot, False)
            self._selected_error = None

        # Stop worker logic
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker = None

        # Reset metrics
        if hasattr(self, "metrics_manager"):
            self.metrics_manager.reset_metrics()

        # Reset correction counters
        self._total_corrections = 0
        self._correct_corrections = 0

    # Arm pick cycle (approach -> descend -> hold -> lift -> present -> return)
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
            "green": (-220.0, -10.0), # left-mid
            "red":   (40.0,  10.0),   # right-mid
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
                
                # Lock color & slot at trigger time
                self._pending_color = self._color_of_box_in_window()
                self._target_slot = self._color_to_slot(self._pending_color) if self._pending_color else None
                self._pick_state = "to_prep"
                self._start_seg(self._pose_prep(), 120)
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
            
        # segment complete -> next state
        if t >= 1.0:
            if self._pick_state == "to_prep":
                self._pick_state = "descend"
                self._start_seg(self._pose_pick(), 120)

            elif self._pick_state == "descend":
                # Trigger sorting only when arm reaches box
                nearest_color = self._color_of_box_in_window()
                if nearest_color and self.worker:
                    hex_color = nearest_color.name() if hasattr(nearest_color, "name") else nearest_color
                    COLOR_MAP = {"#c82828": "red", "#1f7a3a": "green"}
                    self.worker.sort_box(COLOR_MAP.get(hex_color, "green"))

                # play robotic arm audio
                self.play_sound("robotic_arm")

                self._pick_state = "hold"
                # Capture held box color
                c = self._color_of_box_in_window() or self._pending_color
                if c is not None:
                    self.arm.held_box_color = c
                    self.arm.held_box_visible = True
                    self._target_slot = self._color_to_slot(c)
                    self.arm.update()
                self._start_seg(self._pose_pick(), 40)

            elif self._pick_state == "hold":
                self._pick_state = "lift"
                self._start_seg(self._pose_lift(), 120)

            elif self._pick_state == "lift":
                # Still move the arm towards the target container
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
                # Animate flying box at the moment of drop
                slot_to_use = self._present_slot_override or self._target_slot
                if slot_to_use:
                    target_widget = self._slot_to_widget.get(slot_to_use)
                    if target_widget and getattr(self.arm, "held_box_color", None):
                        self._animate_flying_box(self.arm.held_box_color, target_widget)
                        
                # Hide held box and return arm
                self._pick_state = "return"
                self.arm.held_box_visible = False
                self.arm.update()
                self._start_seg(self._pose_home(), 200)

            elif self._pick_state == "return":
                self._pick_state = "idle_pause"
                self._target_slot = None
                self._pending_color = None
                self._present_slot_override = None
                self._start_seg(self._pose_home(), 40)

            elif self._pick_state == "idle_pause":
                self._pick_state = "idle"

    # Helpers
    def _grip_x(self):
        # Single source of truth for the gripper's detection X (edit here to shift detection) 
        return self.conveyor.width() * 0.44 # Change this value to increate/decrease the position where the robot arm picks up a box

    def _box_near_grip(self):
        # Detection-only: True if any box is within the window around the gripper 
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
        # Remove a box after it passes the later cutoff (independent of detection) 
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes:
            return
        # Get the list of box colors
        colors = getattr(self.conveyor, "_box_colors", None)
        
        # Use the same detection X as the gripper trigger
        detect_x = self._grip_x()
        cutoff_x = detect_x + self._despawn_offset_px # set offset to 0 so the box disappears as soon as its touched
        
        # Find the first box that has passed the cutoff point
        hit_index = -1
        for i, x in enumerate(boxes):
            if x >= cutoff_x:
                hit_index = i
                break
        
        # Remove the box and its color if a cutoff was detected
        if hit_index != -1:
            del boxes[hit_index]
            if isinstance(colors, list) and hit_index < len(colors):
                del colors[hit_index]
            self.conveyor.update()
            
    # Helper to get nearest box color
    def _color_of_box_in_window(self):
        # Return the QColor of the first box currently inside the detection window (or None) 
        boxes = getattr(self.conveyor, "_boxes", None)
        cols = getattr(self.conveyor, "_box_colors", None)
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
        if key == "#1f7a3a":
            return "green"
        return "green"

    def _animate_flying_box(self, color, target_widget):
        # Spawn a temporary box at the gripper and animate it flying into the container 
        if not target_widget:
            return
        
        # Create a tiny square QLabel as the flying box
        box = QLabel(self.scene)
        box.setStyleSheet(
            f"background-color: {color.name()}; "
            f"border: 1px solid {color.darker(200).name()}; "
            "border-radius: 3px;"
        )
        box.resize(24, 24)  # same as conveyor box size
        box.show()
        box.lower()
        
        # Start position: approximate gripper center in scene coords
        arm_pos = self.arm.mapTo(self.scene, self.arm.gripper_center())
        start_rect = QRect(int(arm_pos.x() - 12), int(arm_pos.y() - 12), 24, 28)

        # End position: center of target container
        end_pos = target_widget.mapTo(self.scene, target_widget.rect().center())
        end_rect = QRect(end_pos.x() - 12, end_pos.y() - 12, 24, 28)
        
        # Animate
        anim = QPropertyAnimation(box, b"geometry", self)
        anim.setDuration(500)
        anim.setStartValue(start_rect)
        anim.setEndValue(end_rect)
        anim.finished.connect(box.deleteLater)
        anim.start()

    # Click handling
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
        # Return the slot of the currently selected (held) error, if any
        if self._selected_error is None:
            return None
        rec = self._errors.get(self._selected_error)
        return rec['current'] if rec else None


    # Drag ghost helpers
    def _start_drag_box(self, color: QColor):
        # Spawn a ghost box inside the scene, behind the containers 
        if self._drag_label:
            self._drag_label.deleteLater()

        lbl = QLabel(self.scene)
        lbl.setStyleSheet(
            f"background-color: {color.name()}; "
            f"border: 1px solid {color.darker(200).name()}; "
            "border-radius: 3px;"
        )
        lbl.resize(24, 24)
        lbl.show()
        lbl.lower()  # keep behind containers

        self._drag_label = lbl
        self._drag_color = color
        
        # Position immediately at cursor (scene coordinates)
        from PyQt5 import QtGui
        pos = self.scene.mapFromGlobal(QtGui.QCursor.pos())
        lbl.move(pos.x() - 12, pos.y() - 12)

        if not self._drag_timer.isActive():
            self._drag_timer.start()

    def _end_drag_box(self):
        # Remove the drag label and stop following 
        if self._drag_timer.isActive():
            self._drag_timer.stop()
        if self._drag_label:
            self._drag_label.deleteLater()
            self._drag_label = None
        self._drag_color = None

    def _update_drag_ghost(self):
        # Timer tick: keep ghost glued to the cursor
        if not self._drag_label:
            return
        from PyQt5 import QtGui
        pos = self.scene.mapFromGlobal(QtGui.QCursor.pos())
        self._drag_label.move(pos.x() - 12, pos.y() - 12)


    # Badges
    def _create_error_badges(self):
        # Create a small colored '!' badge for each bin (initially hidden) 
        for slot, w in self._slot_to_widget.items():
            lbl = QLabel("!", w)
            lbl.setFixedSize(40, 40)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            lbl.setStyleSheet(
                "color: white; background: rgba(0,0,0,0); border-radius: 20px; "
                "font-weight: 800; font-size: 24px;"
            )
            lbl.hide()
            self._badges[slot] = lbl
            self._position_badge(slot)

    def _position_badge(self, slot):
        # Center the badge along the top inside the container 
        w = self._slot_to_widget.get(slot)
        b = self._badges.get(slot)
        if not w or not b:
            return
        x = (w.width() - b.width()) // 2
        y = 2
        b.move(max(0, x), max(0, y))

    def _apply_flash_colors(self):
        # Apply flashing borders per-bin based on oldest unresolved error, and update badges, Alarm starts only if an error has been active for >=2s, and stops when all are cleared 
        selected_slot = self._current_selected_slot()
        for slot, w in self._slot_to_widget.items():
            ids = self._bin_errors.get(slot, [])
            badge = self._badges.get(slot)

            if ids:
                head = ids[0]
                rec = self._errors.get(head)
                if rec:
                    # Border flashing color (based on error color)
                    flash_q = self._slot_color_map.get(rec['color'], self._orig_borders.get(slot, w.border))
                    if slot != selected_slot:  # selection highlight takes priority
                        w.border = flash_q if self._flash_on else self._orig_borders.get(slot, w.border)
                        w.update()

                    if badge:
                        q = self._slot_color_map.get(rec['color'])
                        if q:
                            badge.setStyleSheet(
                                "color: white; "
                                f"background: {q.name()}; "
                                f"border: 2px solid {q.darker(130).name()}; "
                                "border-radius: 20px; font-weight: 800; font-size: 24px;"
                            )
                            badge.show()
            else:
                # No errors -> restore original + hide badge
                if w.border != self._orig_borders.get(slot, w.border) and slot != selected_slot:
                    w.border = self._orig_borders.get(slot, w.border)
                    w.update()
                if badge:
                    badge.hide()

        # Alarm logic
        if self._errors and not self._alarm_active:
            oldest_age = 0.0  # track age of the oldest unresolved error
            for eid, start in self._error_start_times.items():
                age = time.time() - start
                if age > oldest_age:
                    oldest_age = age
            if oldest_age >= 2.0:
                # wait until 2s old error
                self.play_sound("alarm")
                self._alarm_active = True
        elif not self._errors and self._alarm_active:
            self.audio.stop_alarm()
            self._alarm_active = False

    def _flash_tick(self):
        self._flash_on = not self._flash_on
        self._apply_flash_colors()

    def _on_container_clicked(self, slot):
        # === CASE 1: Not holding anything, attempt to PICK from this bin ===
        if self._selected_error is None:
            ids = self._bin_errors.get(slot, [])
            if not ids:
                print(f"(Inspection Task: No errors in {slot} to pick up)")
                return

            # FIFO pick one error from the clicked bin
            eid = ids.pop(0)
            rec = self._errors.get(eid)
            if not rec:
                return

            self._selected_error = eid
            self._highlight_bin(slot, True)
            print(f"Inspection Task: Picked error #{eid}: {rec['color']} currently in {slot}. "
                  f"Click the correct container ({rec['actual']}).")

            # Spawn ghost box
            q = self._slot_color_map.get(rec['color'])
            if q:
                self._start_drag_box(q)
                
            # Update flashing/badges immediately (selected bin stops flashing)
            self._apply_flash_colors()
            return
        
        # === CASE 2: Holding an error, drop it into clicked bin ===
        eid = self._selected_error
        rec = self._errors.get(eid)
        if not rec:
            self._selected_error = None
            self._end_drag_box()
            self._apply_flash_colors()
            return
        
        # Remove highlight from previous bin
        self._highlight_bin(rec['current'], False)
        prev = rec['current']
        new_slot = slot
        
        # Remove the error ID from the previous bin if it was still listed there
        try:
            if eid in self._bin_errors.get(prev, []):
                self._bin_errors[prev].remove(eid)
        except ValueError:
            pass

        rec['current'] = new_slot
        self._total_corrections += 1

        if new_slot == rec['actual']:
            # Correct placement — resolve error
            self._correct_corrections += 1
            self._error_start_times.pop(eid, None)
            print(f"Inspection Task: Resolved error #{eid}: moved {rec['color']} to {new_slot}")
            
            # Remove from error lists
            if eid in self._errors:
                del self._errors[eid]
                
            # Play correct chime
            self.play_sound("correct_chime")
            
            # Stop alarm if no errors remain
            if not self._errors and self._alarm_active:
                self.audio.stop_alarm()
                self._alarm_active = False
        else:
            # Wrong placement — treat as permanently failed, clear the error too
            self._error_start_times.pop(eid, None)
            print(f"Inspection Task: Error #{eid} placed incorrectly in {new_slot} and cleared (was {rec['actual']})")
            # Remove error record
            if eid in self._errors:
                del self._errors[eid]
                
            # Play incorrect chime here
            self.play_sound("incorrect_chime")

        # End drag + deselect
        self._selected_error = None
        self._end_drag_box()
        
        # Refresh flashing + badges
        self._apply_flash_colors()

    # Worker signal handlers
    def spawn_box_from_worker(self, box_data):
        color = box_data["color"]
        error = box_data["error"]
        self.conveyor.spawn_box(color=color, error=error)

    def _on_box_sorted(self, color, correct):
        # Only allow recognized colors to be processed
        assert color in {"green", "red"}

        if correct:
            # If sorting is correct, show the correct slot highlight and play correct chime
            self._present_slot_override = color
            into = color
            msg = f"Inspection Task: sorted {color} into {into} - correct"
            print(msg)
            self.play_sound("correct_chime")
        else:
            # If sorting is incorrect, determine which wrong bin it was placed in
            wrong = "red" if color == "green" else "green"
            self._present_slot_override = wrong
            into = wrong
            
            # create an error record living in the wrong bin
            eid = self._next_eid
            self._next_eid += 1
            rec = {"id": eid, "color": color, "actual": color, "current": into}
            self._errors[eid] = rec
            self._bin_errors[into].append(eid)
            
            # Record pickup time
            self._error_start_times[eid] = time.time()
            msg = f"Inspection Task: sorted {color} into {into} - error (expected {color})"
            print(msg)
            
            # play only the incorrect chime
            self.play_sound("incorrect_chime")
            
            # Alarm will be started/stopped by _apply_flash_colors (after 2s if unresolved)

            # Update flashing/badges immediately so the bin shows this (oldest) error color
            self._apply_flash_colors()

    def _on_metrics_live(self, metrics):
        # Always include correction fields
        metrics['insp_correction_rate'] = (
            (self._correct_corrections / self._total_corrections) * 100
            if self._total_corrections > 0 else 0.0
        )
        metrics['insp_corrections'] = self._correct_corrections

        # Update local metrics manager
        if hasattr(self, "metrics_manager") and self.metrics_manager:
            self.metrics_manager.update_metrics(metrics)

        # Log to Observer
        oc = getattr(self, "observer_control", None)
        if oc:
            ts = oc.get_timestamp()
            logger = get_logger()
            logger.log_metric(ts, "inspection", "boxes inspected", metrics.get("insp_total", 0))
            logger.log_metric(ts, "inspection", "errors", metrics.get("insp_errors", 0))
            logger.log_metric(ts, "inspection", "errors corrected", self._correct_corrections)

        # Forward over network
        client = getattr(self, "network_client", None)
        if client:
            client.send({"command": "metrics", "data": metrics})


    def play_sound(self, sound_name):
        # Use injected sounds_enabled dict from TaskManager
        sounds_enabled = getattr(self, "sounds_enabled", {}) or {}

        if sound_name == "conveyor" and sounds_enabled.get("conveyor", False):
            self.audio.start_conveyor()
        elif sound_name == "robotic_arm" and sounds_enabled.get("robotic_arm", False):
            self.audio.play_robotic_arm()
        elif sound_name == "correct_chime" and sounds_enabled.get("correct_chime", False):
            self.audio.play_correct()
        elif sound_name == "incorrect_chime" and sounds_enabled.get("incorrect_chime", False):
            self.audio.play_incorrect()
        elif sound_name == "alarm" and sounds_enabled.get("alarm", False):
            self.audio.start_alarm()
