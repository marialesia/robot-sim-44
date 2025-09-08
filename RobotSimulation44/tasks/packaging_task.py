# tasks/packaging_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer, QEvent, QPropertyAnimation
from PyQt5.QtWidgets import QLabel, QGraphicsOpacityEffect, QHBoxLayout, QSizePolicy, QWidget
from .base_task import BaseTask, StorageContainerWidget
from .packaging_logic import PackagingWorker
from event_logger import get_logger
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
        # rec: {widget,label,capacity,count,effect,anim,fading,error,fixed,orig_border,badge}
        self._containers = []

        # Helper to create badge
        def _make_badge(parent_w):
            b = QLabel("!", parent_w)
            b.setFixedSize(20, 20)
            b.setAlignment(Qt.AlignCenter)
            b.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            # default hidden; style set when shown
            b.hide()
            return b

        # Helper to create a new container record
        def _new_container(widget=None):
            w = widget or StorageContainerWidget()
            _style_container(w)
            w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

            cap = 0   # pre-start show 0/0
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

            # Error badge (hidden until error)
            badge = _make_badge(w)

            # Fade effect/animation (used when this container is the active one and reaches its trigger)
            eff = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(eff)
            eff.setOpacity(1.0)

            anim = QPropertyAnimation(eff, b"opacity", self)
            anim.setDuration(2000)  # 2s fade

            # Recenter label/badge on widget resizes & enable click handling
            w.installEventFilter(self)

            rec = {
                "widget": w,
                "label": lbl,
                "capacity": cap,
                "count": cnt,
                "effect": eff,
                "anim": anim,
                "fading": False,
                "error": False,     # flagged by worker for under/over
                "fixed": False,     # user clicked to correct
                "orig_border": w.border,
                "badge": badge
            }
            # Initial badge position
            self._position_badge(rec)
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

        # ===== Spawner / worker =====
        self.worker = None
        # Legacy timer kept for backward compatibility; we stop it once worker is used
        self._box_timer = QTimer(self)
        self._box_timer.timeout.connect(self._spawn_orange_box)

        # ===== Minimal arm 'pick-present-return' cycle =====
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

        # Worker-driven fade flag (for current leftmost container)
        self._should_fade_current = False

        # ===== Error flash timer =====
        self._flash_on = False
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(350)  # flash speed
        self._flash_timer.timeout.connect(self._on_flash_tick)

        # repaint once
        self.arm.update()
        self.conveyor.update()
        for rec in self._containers:
            rec["widget"].update()
            self._position_label(rec)

    # ---------- Helpers for labels/badges ----------
    def _position_label(self, rec):
        w = rec["widget"]; lbl = rec["label"]
        x = (w.width() - lbl.width()) // 2
        y = (w.height() - lbl.height()) // 2
        lbl.move(max(0, x), max(0, y))

    def _position_badge(self, rec):
        w = rec["widget"]; b = rec.get("badge")
        if not b:
            return
        x = (w.width() - b.width()) // 2
        y = 2  # near top edge
        b.move(max(0, x), max(0, y))

    def _update_label(self, rec):
        rec["label"].setText(f"{rec['count']}/{rec['capacity']}")
        self._position_label(rec)

    # ---------- Error visuals ----------
    def _apply_error_visuals(self):
        """Flash red border + show badge for containers with error and not fixed."""
        for rec in self._containers:
            w = rec["widget"]
            badge = rec.get("badge")
            # Fixed takes precedence: show success green, no badge/flash
            if rec.get("fixed"):
                if badge:
                    badge.hide()
                w.border = QColor("#2ecc71")  # success green
                w.update()
                continue

            if rec.get("error"):  # error: flash + badge
                # flashing border red
                w.border = QColor("#e74c3c") if self._flash_on else rec.get("orig_border", w.border)
                w.update()

                # badge styling and show
                if badge:
                    badge.setStyleSheet(
                        "color: white;"
                        "background: #e74c3c;"
                        "border: 2px solid #b03a2e;"
                        "border-radius: 10px;"
                        "font-weight: 800; font-size: 12px;"
                    )
                    badge.show()
                    self._position_badge(rec)
            else:
                # normal: restore border, hide badge
                if badge:
                    badge.hide()
                w.border = rec.get("orig_border", w.border)
                w.update()

    def _on_flash_tick(self):
        self._flash_on = not self._flash_on
        self._apply_error_visuals()

    # ---------- Worker callbacks ----------
    def _on_worker_fade(self, mode, at_count, capacity, secs):
        """
        Worker says: the current leftmost container should fade NOW.
        We set a flag; fade actually begins on the next packed item (or immediately if already reached).
        Also mark error (under/over) so visuals can reflect it.
        """
        self._should_fade_current = True

        if self._containers:
            rec = self._containers[0]
            # Only under/over are errors
            rec["error"] = (mode in ("underfill", "overfill"))
            rec["fixed"] = False
            # Log the trigger
            try:
                get_logger().log_robot(
                    "Packaging",
                    f"fade_trigger mode={mode} at {at_count}/{capacity} ({secs:.2f}s)"
                )
            except Exception:
                pass
            self._apply_error_visuals()

    # ---------- Packing count ----------
    def _on_item_packed(self):
        # Always pack into the leftmost container
        if not self._containers:
            return
        active = self._containers[0]

        # If already fading, ignore new items until shift completes
        if active["fading"]:
            return

        # Increment count and show it (overfill will read e.g., 5/4)
        active["count"] += 1
        self._update_label(active)

        # Print msg
        msg = f"Packaging Task: Packed {active['count']}/{active['capacity']}"
        print(msg)

        # Log pack
        try:
            get_logger().log_robot("Packaging", f"pack {active['count']}/{active['capacity']}")
        except Exception:
            pass

        # Tell worker one more item got packed; it will decide if this container should fade (normal/under/over)
        if self.worker:
            self.worker.record_pack()

        # Fade if worker flagged it (preferred), otherwise fallback to legacy (no worker) behavior
        need_fade = self._should_fade_current
        if not self.worker:
            need_fade = need_fade or (active["count"] >= active["capacity"])

        if need_fade and not active["fading"]:
            active["fading"] = True
            self._should_fade_current = False
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
                if self.worker and self.worker.isRunning():
                    # Running: give the new container a real capacity now
                    new_cap = PackagingWorker.pick_capacity()
                    new_rec = self._create_new_container(initial_cap=new_cap)
                else:
                    # Not running: keep it 0/0 until Start
                    new_rec = self._create_new_container(initial_cap=None)

                self._containers.append(new_rec)
                self._row_layout.addWidget(new_rec["widget"])

                # Ensure labels are centered
                for rec2 in self._containers:
                    self._position_label(rec2)
                    self._position_badge(rec2)

                # IMPORTANT: inform the worker the active container changed
                if self.worker and self._containers:
                    leftmost = self._containers[0]
                    self.worker.begin_container(leftmost["capacity"])
                    # Log begin of new active container
                    try:
                        get_logger().log_robot(
                            "Packaging",
                            f"begin_container capacity={leftmost['capacity']}"
                        )
                    except Exception:
                        pass

                # After the shift, refresh visuals (in case next leftmost is in error later)
                self._apply_error_visuals()

                # Log shift completion
                try:
                    get_logger().log_robot(
                        "Packaging",
                        f"shift_completed new_right_capacity={new_rec['capacity']}"
                    )
                except Exception:
                    pass

            # Ensure no duplicate connections on repeated fades
            try:
                anim.finished.disconnect()
            except Exception:
                pass
            anim.finished.connect(_finished)
            anim.start()

    def _create_new_container(self, initial_cap=None):
        """Create a fresh container on the far-right.
        - Before the first Start: initial_cap=None -> show 0/0
        - During a running session: pass a real capacity so it shows 0/N immediately
        """
        w = StorageContainerWidget()
        # match styling to others
        w.border = QColor("#c76a1a")
        w.fill_top = QColor("#ffe9d3")
        w.fill_bottom = QColor("#ffd9b5")
        w.rib = QColor(199, 106, 26, 110)
        w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        cap = 0 if initial_cap is None else int(initial_cap)
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

        # badge
        badge = QLabel("!", w)
        badge.setFixedSize(20, 20)
        badge.setAlignment(Qt.AlignCenter)
        badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        badge.hide()

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
            "fading": False,
            "error": False,
            "fixed": False,
            "orig_border": w.border,
            "badge": badge
        }
        self._position_label(rec)
        self._position_badge(rec)
        return rec

    # ---------- Spawning ----------
    def _spawn_orange_box(self):
        self.conveyor.spawn_box(color="orange")

    # Called by worker
    def spawn_box_from_worker(self, box_data):
        color = box_data.get("color", "orange")
        # Log spawn (robot event)
        try:
            get_logger().log_robot("Packaging", f"spawn_box color={color}")
        except Exception:
            pass
        self.conveyor.spawn_box(color=color)

    # ---------- Lifecycle ----------
    def start(self, pace=None, error_rate=None):
        # Belt motion
        self.conveyor.setBeltSpeed(120)
        self.conveyor.enable_motion(True)

        # Ensure legacy timer is OFF
        if self._box_timer.isActive():
            self._box_timer.stop()

        # Start/ensure worker
        if not self.worker or not self.worker.isRunning():
            self.worker = PackagingWorker(
                pace=pace,
                color="orange",
                error_rate=error_rate,
            )
            self.worker.box_spawned.connect(self.spawn_box_from_worker)
            self.worker.metrics_ready.connect(self._on_metrics)
            self.worker.container_should_fade.connect(self._on_worker_fade)
            self.worker.metrics_live.connect(self._on_metrics_live)
            self.worker.start()

        # Reset all containers (0/N, full opacity, not fading) and assign capacities
        for rec in self._containers:
            rec["count"] = 0
            rec["capacity"] = PackagingWorker.pick_capacity()
            rec["error"] = False
            rec["fixed"] = False
            rec["anim"].stop()
            rec["effect"].setOpacity(1.0)
            rec["widget"].show()
            rec["fading"] = False
            # restore original border, hide badge, update label
            rec["widget"].border = rec.get("orig_border", rec["widget"].border)
            if rec.get("badge"):
                rec["badge"].hide()
            self._update_label(rec)

        # Tell worker the active container's capacity (leftmost)
        if self._containers:
            leftmost = self._containers[0]
            self.worker.begin_container(leftmost["capacity"])
            # Log active container begin
            try:
                get_logger().log_robot("Packaging", f"begin_container capacity={leftmost['capacity']}")
            except Exception:
                pass
        self._should_fade_current = False

        # Start flash engine
        if not self._flash_timer.isActive():
            self._flash_timer.start()

        # Start arm FSM
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._pick_state = "idle"
        self._pick_t = 0
        if not self._pick_timer.isActive():
            sh, el = self._pose_home()
            self._set_arm(sh, el)
            self._pick_timer.start()

        # Log start control
        try:
            get_logger().log_user("Packaging", "control", "start", "pace=slow,error_rate=0.20")
        except Exception:
            pass

    def stop(self):
        self.conveyor.enable_motion(False)
        if self._box_timer.isActive():
            self._box_timer.stop()
        if self._pick_timer.isActive():
            self._pick_timer.stop()

        # stop worker thread cleanly
        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(500)

        # stop flashing
        if self._flash_timer.isActive():
            self._flash_timer.stop()
        self._flash_on = False

        # Return arm to home and clear held box
        sh, el = self._pose_home()
        self._set_arm(sh, el)
        self.arm.held_box_visible = False
        self.arm.update()

        # Log stop control
        try:
            get_logger().log_user("Packaging", "control", "stop", "stopped by user")
        except Exception:
            pass

    def _on_metrics(self, metrics):
        # CSV line for metrics
        try:
            get_logger().log_robot(
                "Packaging",
                f"metrics total={metrics.get('total')} errors={metrics.get('errors')} "
                f"acc={metrics.get('accuracy'):.2f}% ipm={metrics.get('items_per_min'):.2f}"
            )
        except Exception:
            pass
        print("Packaging metrics:", metrics)

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
                c = self._color_of_box_in_window()
                if c is not None:
                    self.arm.held_box_color = c
                    self.arm.held_box_visible = True
                    self.arm.update()
                self._pick_state = "hold"
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

    # ---------- Smart-fix ----------
    def _smart_fix(self, rec):
        """
        If the clicked container is currently marked as error (under/over),
        correct the count to capacity, turn border green, hide the badge/flash,
        but do NOT stop/restart its fade animation.
        """
        if not rec.get("error"):
            # Still log the click (no-op)
            try:
                get_logger().log_user("Packaging", "container", "click", "no error to fix")
            except Exception:
                pass
            return  # nothing to fix

        # Correct the number to exactly capacity (normalizing under/over)
        cap = rec.get("capacity", 0)
        if cap > 0:
            rec["count"] = cap
            self._update_label(rec)

        # Clear the error state; keep fade untouched
        rec["error"] = False
        rec["fixed"] = True

        # Visual: green border + hide badge
        self._mark_fixed_visual(rec)
        if rec.get("badge"):
            rec["badge"].hide()

        # Log smart-fix
        try:
            get_logger().log_user("Packaging", "container", "smart_fix", f"set to {cap}/{cap}")
        except Exception:
            pass

        # Repaint (and stop flashing on it)
        self._apply_error_visuals()

    def _mark_fixed_visual(self, rec):
        """Set a success-green border on the container to indicate the fix."""
        w = rec["widget"]
        w.border = QColor("#2ecc71")  # success green
        w.update()

    # ---------- Keep labels centered + handle clicks (smart-fix) ----------
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            # If a known container resized, re-center its label and badge
            for rec in self._containers:
                if obj is rec["widget"]:
                    self._position_label(rec)
                    self._position_badge(rec)
                    break

        # Smart-fix on click: fix under/over if user clicks the error container before it disappears
        if event.type() == QEvent.MouseButtonPress:
            for rec in self._containers:
                if obj is rec["widget"]:
                    self._smart_fix(rec)
                    return True

        return super().eventFilter(obj, event)

    def _on_metrics_live(self, metrics):
        """Receive live metrics from the worker and update MetricsManager in real time."""
        if hasattr(self, "metrics_manager") and self.metrics_manager:
            self.metrics_manager.update_metrics(metrics)
        else:
            # fallback for debugging
            print("Live metrics:", metrics)
