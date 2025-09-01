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

        # ---- Style for packaging containers ----
        def _style_container(w):
            w.border = QColor("#c76a1a")
            w.fill_top = QColor("#ffe9d3")
            w.fill_bottom = QColor("#ffd9b5")
            w.rib = QColor(199, 106, 26, 110)

        _style_container(self.container)  # use BaseTask's default as the first

        # ---- Layout: keep conveyor + arm; replace single container with a row of 4 ----
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=2, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=2, align=Qt.AlignHCenter | Qt.AlignBottom),
            container=dict(row=1, col=0, align=Qt.AlignRight | Qt.AlignBottom),
            col_stretch=[1, 1], row_stretch=[0, 1]
        )

        # We'll remove the single container from the grid and reinsert as part of a row.
        try:
            self.grid.removeWidget(self.container)
        except Exception:
            pass

        # --- Row holding 4 containers (leftmost is the active packing target) ---
        self._row = QWidget()
        self._row_layout = QHBoxLayout(self._row)
        self._row_layout.setContentsMargins(0, 0, 0, 0)
        self._row_layout.setSpacing(12)

        # Build container records list
        self._containers = []  # each: dict(widget, label, capacity, count, effect, anim, fading)

        # Helper to create a new container record
        def _new_container(widget=None):
            w = widget or StorageContainerWidget()
            _style_container(w)
            w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

            # capacity: 4, 5, or 6
            cap = random.choice((4, 5, 6))
            cnt = 0

            # Counter label centered on the widget
            lbl = QLabel(w)
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            lbl.setStyleSheet(
                "font-weight: 700; font-size: 18px; color: #222;"
                "background: rgba(255,255,255,200);"
                "padding: 2px 8px; border-radius: 8px;"
                "border: 1px solid rgba(0,0,0,60);"
            )
            lbl.setText(f"{cnt}/{cap}")
            lbl.show()

            # Fade effect/animation (used when this container is the active one and reaches capacity)
            eff = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(eff)
            eff.setOpacity(1.0)

            anim = QPropertyAnimation(eff, b"opacity", self)
            anim.setDuration(2000)  # 2s fade
            # Note: we connect the finished handler later when we start a fade

            # Recenter label on widget resizes
            w.installEventFilter(self)

            rec = {
                "widget": w,
                "label": lbl,
                "capacity": cap,
                "count": cnt,
                "effect": eff,
                "anim": anim,
                "fading": False
            }
            return rec

        # Create 4 containers; use BaseTask's self.container as the first, others new
        first_rec = _new_container(self.container)
        self._containers.append(first_rec)
        self._row_layout.addWidget(first_rec["widget"])

        for _ in range(3):
            rec = _new_container()
            self._containers.append(rec)
            self._row_layout.addWidget(rec["widget"])

        # Put the row back into the grid — same placement style as before
        self.grid.addWidget(self._row, 1, 0, 1, 2, Qt.AlignRight | Qt.AlignBottom)

        # ===== Box spawner (orange) =====
        self._box_timer = QTimer(self)
        self._box_timer.timeout.connect(self._spawn_orange_box)

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
        for rec in self._containers:
            rec["widget"].update()
            self._position_label(rec)

    # ---------- Helpers for labels ----------
    def _position_label(self, rec):
        w = rec["widget"]; lbl = rec["label"]
        x = (w.width() - lbl.width()) // 2
        y = (w.height() - lbl.height()) // 2
        lbl.move(max(0, x), max(0, y))

    def _update_label(self, rec):
        rec["label"].setText(f"{rec['count']}/{rec['capacity']}")
        self._position_label(rec)

    # ---------- Packing count ----------
    def _on_item_packed(self):
        # Always pack into the leftmost container
        if not self._containers:
            return
        active = self._containers[0]

        # If already fading, ignore new items until shift completes
        if active["fading"]:
            return

        if active["count"] < active["capacity"]:
            active["count"] += 1
            self._update_label(active)

        # Hit capacity -> start a one-time fade, then shift
        if active["count"] >= active["capacity"] and not active["fading"]:
            active["fading"] = True
            eff = active["effect"]; anim = active["anim"]; w = active["widget"]

            anim.stop()
            eff.setOpacity(1.0)
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)

            # When fade finishes, remove leftmost and append a fresh one on the right
            def _finished():
                # Hide/remove the widget from layout
                w.hide()
                self._row_layout.removeWidget(w)
                try:
                    # Drop the record
                    self._containers.pop(0)
                except Exception:
                    pass

                # Create and append a new container to the far-right
                new_rec = self._create_new_container()
                self._containers.append(new_rec)
                self._row_layout.addWidget(new_rec["widget"])

                # Ensure labels are centered
                for rec2 in self._containers:
                    self._position_label(rec2)

            anim.finished.connect(_finished)
            anim.start()

    def _create_new_container(self):
        # Fresh container on the far-right with 0/N and full opacity
        w = StorageContainerWidget()
        # match styling to others
        w.border = QColor("#c76a1a")
        w.fill_top = QColor("#ffe9d3")
        w.fill_bottom = QColor("#ffd9b5")
        w.rib = QColor(199, 106, 26, 110)
        w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        cap = random.choice((4, 5, 6))
        cnt = 0

        lbl = QLabel(w)
        lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lbl.setStyleSheet(
            "font-weight: 700; font-size: 18px; color: #222;"
            "background: rgba(255,255,255,200);"
            "padding: 2px 8px; border-radius: 8px;"
            "border: 1px solid rgba(0,0,0,60);"
        )
        lbl.setText(f"{cnt}/{cap}")
        lbl.show()

        eff = QGraphicsOpacityEffect(w)
        w.setGraphicsEffect(eff)
        eff.setOpacity(1.0)

        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(2000)

        w.installEventFilter(self)

        rec = {
            "widget": w,
            "label": lbl,
            "capacity": cap,
            "count": cnt,
            "effect": eff,
            "anim": anim,
            "fading": False
        }
        self._position_label(rec)
        return rec

    # ---------- Spawning ----------
    def _spawn_orange_box(self):
        self.conveyor.spawn_box(color="orange")

    # ---------- Lifecycle ----------
    def start(self):
        # Belt motion
        self.conveyor.setBeltSpeed(120)
        self.conveyor.enable_motion(True)
        if not self._box_timer.isActive():
            self._box_timer.start(1500)  # one orange box every 1.5s

        # Reset all containers (0/N, full opacity, not fading)
        for rec in self._containers:
            rec["count"] = 0
            # randomize capacities at the start of a run to make each “cycle” fresh
            rec["capacity"] = random.choice((4, 5, 6))
            self._update_label(rec)
            rec["anim"].stop()
            rec["effect"].setOpacity(1.0)
            rec["widget"].show()
            rec["fading"] = False

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
        """Present toward the row (still aimed at the leftmost/active one)."""
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
                # Count this as a packed item (into the LEFTMOST container)
                self._on_item_packed()

                self._pick_state = "return"
                self.arm.held_box_visible = False
                self.arm.update()
                self._start_seg(self._pose_home(), 200)

            elif self._pick_state == "return":
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

    # ---------- Keep every counter label centered on resize ----------
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            # If a known container resized, re-center its label
            for rec in self._containers:
                if obj is rec["widget"]:
                    self._position_label(rec)
                    break
        return super().eventFilter(obj, event)
