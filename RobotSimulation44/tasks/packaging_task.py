
from PyQt5 import QtCore
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer, QEvent, QPropertyAnimation
from PyQt5.QtWidgets import QLabel, QGraphicsOpacityEffect, QHBoxLayout, QSizePolicy, QWidget
from .base_task import BaseTask, StorageContainerWidget
from .packaging_logic import PackagingWorker
from event_logger import get_logger
from audio_manager import AudioManager
import random
import time


class PackagingTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Packaging")

        # ---- Audio ----
        self.audio = AudioManager()
        self._alarm_active = False  # track alarm state like SortingTask

        # ---- Robot arm visuals ----
        self.arm.shoulder_angle = -90
        self.arm.elbow_angle = 0
        self.arm.c_arm = QColor("#8e44ad")
        self.arm.c_arm_dark = QColor("#6d2e8a")

        # ---- Color rotation (always keep R, B, G visible) ----
        self._rot = ["red", "blue", "green"]
        self._next_idx = random.randint(0, 2)   # start point for rotation

        # ---- helpers ----
        def _apply_style_by_color(w, color: str):
            if color == "red":
                w.border = QColor("#8c1f15")
                w.fill_top = QColor("#ffd6d1")
                w.fill_bottom = QColor("#ffb8b0")
                w.rib = QColor(140, 31, 21, 110)
            elif color == "blue":
                w.border = QColor("#2b4a91")
                w.fill_top = QColor("#dbe8ff")
                w.fill_bottom = QColor("#c7daff")
                w.rib = QColor(43, 74, 145, 110)
            else:  # green
                w.border = QColor("#1f7a3a")
                w.fill_top = QColor("#d9f7e6")
                w.fill_bottom = QColor("#bff0d3")
                w.rib = QColor(31, 122, 58, 110)

        self._apply_style_by_color = _apply_style_by_color

        # Style the BaseTask's default container to match first color in rotation
        first_color = self._rot[self._next_idx]
        self._apply_style_by_color(self.container, first_color)

        # ---- Layout ----
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=2, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=2, align=Qt.AlignHCenter | Qt.AlignBottom),
            container=dict(row=1, col=0, align=Qt.AlignRight | Qt.AlignBottom),
            col_stretch=[1, 1], row_stretch=[0, 1]
        )
        try:
            self.grid.removeWidget(self.container)
        except Exception:
            pass

        # Row of 4 containers (leftmost is active)
        self._row = QWidget()
        self._row_layout = QHBoxLayout(self._row)
        self._row_layout.setContentsMargins(0, 0, 0, 0)
        self._row_layout.setSpacing(12)
        # rec: widget,label,capacity,count,effect,anim,fading,error,fixed,orig_border,badge,color,mis_color,batch_spawned,err_start
        self._containers = []

        def _make_badge(parent_w):
            b = QLabel("!", parent_w)
            b.setFixedSize(40, 40)
            b.setAlignment(Qt.AlignCenter)
            b.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            b.hide()
            return b

        def _new_container(widget=None, color=None):
            w = widget or StorageContainerWidget()
            c = color or self._rot[self._next_idx]
            self._apply_style_by_color(w, c)
            w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

            cap = 0
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

            badge = _make_badge(w)

            eff = QGraphicsOpacityEffect(w); w.setGraphicsEffect(eff); eff.setOpacity(1.0)
            anim = QPropertyAnimation(eff, b"opacity", self); anim.setDuration(2000)

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
                "badge": badge,
                "color": c,         # container's color (red/blue/green)
                "mis_color": None,  # wrong box color when mis-sorted into front
                "batch_spawned": False,
                "err_start": None,  # timestamp when this container entered error state
            }
            self._position_badge(rec)
            return rec

        # Build 4 containers in rotation: c0, c1, c2, c0
        c0 = self._rot[self._next_idx]
        first_rec = _new_container(self.container, c0)
        self._containers.append(first_rec); self._row_layout.addWidget(first_rec["widget"])

        c1 = self._rot[(self._next_idx + 1) % 3]
        rec = _new_container(color=c1); self._containers.append(rec); self._row_layout.addWidget(rec["widget"])

        c2 = self._rot[(self._next_idx + 2) % 3]
        rec = _new_container(color=c2); self._containers.append(rec); self._row_layout.addWidget(rec["widget"])

        c3 = c0
        rec = _new_container(color=c3); self._containers.append(rec); self._row_layout.addWidget(rec["widget"])

        # After placing c0,c1,c2,c0 -> next appended should be c1
        self._next_idx = (self._next_idx + 1) % 3

        self.grid.addWidget(self._row, 1, 0, 1, 2, Qt.AlignRight | Qt.AlignBottom)

        # For Sorting correction accuracy
        self._total_corrections = 0
        self._correct_corrections = 0

        # ===== Spawner / worker =====
        self.worker = None

        # Timed drip-spawner for batches
        self._box_timer = QTimer(self)
        self._box_timer.setInterval(1500)          # drip speed; tweak if needed
        self._box_timer.timeout.connect(self._drip_spawn_tick)

        # Pending batch state
        self._batch_active = False
        self._batch_color = None
        self._batch_remaining = 0

        # ===== Arm pick cycle =====
        self._pick_timer = QTimer(self)
        self._pick_timer.setInterval(16)
        self._pick_timer.timeout.connect(self._tick_pick)

        self._pick_state = "idle"
        self._pick_t = 0
        self._pick_duration = 0
        self._pick_from = (self.arm.shoulder_angle, self.arm.elbow_angle)
        self._pick_to = (self.arm.shoulder_angle, self.arm.elbow_angle)

        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._touch_window_px = 18
        self._touch_cooldown_ms = 120
        self._despawn_offset_px = 0

        self._should_fade_current = False

        # flashing for error badge
        self._flash_on = False
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(350)
        self._flash_timer.timeout.connect(self._on_flash_tick)

        # ----- selection state for click-to-fix (like sorting) -----
        self._selected_active = False         # True when user has "picked" the bad item
        self._selected_expected = None        # 'red'|'blue'|'green' expected destination color

        # --- Drag ghost for error correction ---
        self._drag_label = None        # QLabel that follows mouse
        self._drag_color = None        # QColor of the carried box
        self._drag_timer = QTimer(self)
        self._drag_timer.setInterval(16)   # ~60fps
        self._drag_timer.timeout.connect(self._update_drag_ghost)

        # paint once
        self.arm.update()
        self.conveyor.update()
        for rec in self._containers:
            rec["widget"].update()
            self._position_label(rec)

    # ---------- UI helpers ----------
    def _position_label(self, rec):
        w = rec["widget"]; lbl = rec["label"]
        x = (w.width() - lbl.width()) // 2
        y = (w.height() - lbl.height()) // 2
        lbl.move(max(0, x), max(0, y))

    def _position_badge(self, rec):
        w = rec["widget"]; b = rec.get("badge")
        if not b: return
        x = (w.width() - b.width()) // 2
        y = 2
        b.move(max(0, x), max(0, y))

    def _update_label(self, rec):
        rec["label"].setText(f"{rec['count']}/{rec['capacity']}")
        self._position_label(rec)

    # ---------- Error visuals + alarm parity with Sorting ----------
    def _apply_error_visuals(self):
        for i, rec in enumerate(self._containers):
            w = rec["widget"]
            badge = rec.get("badge")

            # Selection highlight for front takes priority
            if i == 0 and self._selected_active:
                w.border = QColor("#ffbf00")  # amber
                w.update()
                if badge:
                    badge.hide()  # suppress badge while selected
                continue

            if rec.get("fixed"):
                if badge:
                    badge.hide()
                w.border = rec.get("orig_border", w.border)
                w.update()
                continue

            if rec.get("error"):
                mis = rec.get("mis_color")
                if mis == "red":
                    flash_color = QColor("#c82828")
                elif mis == "blue":
                    flash_color = QColor("#2b4a91")
                elif mis == "green":
                    flash_color = QColor("#1f7a3a")
                else:
                    flash_color = QColor("#e74c3c")

                w.border = flash_color if self._flash_on else rec.get("orig_border", w.border)
                w.update()

                if badge:
                    badge.setStyleSheet(
                        f"color: white; background: {flash_color.name()};"
                        "border: 2px solid rgba(0,0,0,80); border-radius: 20px;"
                        "font-weight: 800; font-size: 24px;"
                    )
                    badge.show()
                    self._position_badge(rec)
            else:
                if badge:
                    badge.hide()
                w.border = rec.get("orig_border", w.border)
                w.update()

        # Keep alarm state in sync after drawing
        self._update_alarm_state()

    def _on_flash_tick(self):
        self._flash_on = not self._flash_on
        self._apply_error_visuals()

    def _normalize_box_color(self, c):
        """Return canonical 'red'|'blue'|'green' or None if unknown."""
        if isinstance(c, str):
            s = c.strip().lower()
            return s if s in ("red", "blue", "green") else None
        try:
            hexv = c.name().lower()
        except Exception:
            return None
        hex_map = {
            "#c82828": "red",
            "#2b4a91": "blue",
            "#1f7a3a": "green",
        }
        return hex_map.get(hexv)

    # ---------- Alarm helpers (same behavior as Sorting) ----------
    def _any_error_and_oldest_age(self):
        """Returns (has_any_error: bool, oldest_age_seconds: float)."""
        oldest = 0.0
        found = False
        now = time.time()
        for rec in self._containers:
            if rec.get("error"):
                found = True
                t0 = rec.get("err_start")
                if t0:
                    age = now - t0
                    if age > oldest:
                        oldest = age
        return found, oldest

    def _update_alarm_state(self):
        """Start alarm only if an error has persisted >=2s; stop when all cleared."""
        has_err, oldest_age = self._any_error_and_oldest_age()
        if has_err:
            if oldest_age >= 2.0 and not self._alarm_active:
                self.audio.start_alarm()
                self._alarm_active = True
        else:
            if self._alarm_active:
                self.audio.stop_alarm()
                self._alarm_active = False
            # also cancel any pending delayed starts
            try:
                self.audio.cancel_alarm_delay()
            except Exception:
                pass

    # ---------- Scheduling & spawning ----------
    def _count_boxes_on_belt(self, color: str) -> int:
        cols = getattr(self.conveyor, "_box_colors", None)
        if not isinstance(cols, list):
            return 0
        total = 0
        for c in cols:
            if self._normalize_box_color(c) == color:
                total += 1
        return total

    def _schedule_batch_for_front(self):
        """Ensure a full batch for the lead container is scheduled and dripped via timer."""
        if not self._containers:
            return
        front = self._containers[0]
        color = front.get("color")
        cap = int(front.get("capacity", 0))
        cnt = int(front.get("count", 0))
        if cap <= 0:
            front["batch_spawned"] = True
            return

        on_belt = self._count_boxes_on_belt(color)
        scheduled = self._batch_remaining if (self._batch_active and self._batch_color == color) else 0
        need = max(0, cap - cnt - on_belt - scheduled)

        if need <= 0:
            front["batch_spawned"] = True
            if self._batch_active and self._batch_color == color:
                excess = cnt + on_belt + self._batch_remaining - cap
                if excess > 0:
                    self._batch_remaining = max(0, self._batch_remaining - excess)
                    if self._batch_remaining == 0:
                        self._batch_active = False
                        self._box_timer.stop()
            return

        # Add needed amount to the current schedule (or start a new one)
        self._batch_color = color
        self._batch_remaining = need
        self._batch_active = True
        front["batch_spawned"] = True  # gate repeated scheduling for this lead

        if not self._box_timer.isActive():
            # Delay before drip spawning starts 
            QTimer.singleShot(1500, lambda: (
                self._box_timer.start() if (self._batch_active and self._batch_remaining > 0) else None
            ))
        
        try:
            get_logger().log_robot(
                "Packaging",
                f"schedule_batch color={color} need={need} "
                f"(cap={cap}, cnt={cnt}, on_belt={on_belt}, scheduled_pre={scheduled})"
            )
        except Exception:
            pass

    def _drip_spawn_tick(self):
        """Spawn at most one box each tick, respecting capacity."""
        if not self._batch_active or self._batch_remaining <= 0:
            self._box_timer.stop()
            self._batch_active = False
            self._batch_remaining = 0
            return

        if not self._containers:
            self._box_timer.stop()
            self._batch_active = False
            self._batch_remaining = 0
            return

        front = self._containers[0]
        lead_color = front.get("color")

        # If lead container changed, reschedule
        if lead_color != self._batch_color:
            self._batch_active = False
            self._batch_remaining = 0
            self._box_timer.stop()
            self._schedule_batch_for_front()
            return

        cap = int(front.get("capacity", 0))
        cnt = int(front.get("count", 0))
        on_belt = self._count_boxes_on_belt(self._batch_color)
        scheduled = self._batch_remaining

        if cnt + on_belt + scheduled > cap:
            excess = cnt + on_belt + scheduled - cap
            self._batch_remaining = max(0, self._batch_remaining - excess)
            scheduled = self._batch_remaining
            if self._batch_remaining == 0:
                self._batch_active = False
                self._box_timer.stop()
                return

        # === Inject error rate here ===
        spawn_color = self._batch_color
        if self.worker and random.random() < self.worker.error_rate:
            # pick a wrong color
            choices = [c for c in self._rot if c != self._batch_color]
            if choices:
                spawn_color = random.choice(choices)

        if cnt + on_belt + scheduled <= cap and self._batch_remaining > 0:
            self.conveyor.spawn_box(color=spawn_color)
            self._batch_remaining -= 1

        if self._batch_remaining <= 0:
            self._batch_active = False
            self._box_timer.stop()

    # ---------- Worker callbacks ----------
    def _on_worker_fade(self, mode, at_count, capacity, secs):
        """
        Worker suggests a fade when it *thinks* capacity was reached.
        Now: always fade once front count >= capacity, even if errored.
        """
        if not self._containers:
            return
        rec = self._containers[0]

        if rec["count"] >= rec["capacity"] > 0:
            self._should_fade_current = True
        else:
            if self.worker:
                self.worker.rearm_fade()
    
    def _animate_flying_box(self, color, target_widget):
        """Spawn a temporary box at the gripper and animate it flying into the container."""
        if not target_widget:
            return

        box = QLabel(self.scene)
        box.setStyleSheet(
            f"background-color: {color.name()}; "
            f"border: 1px solid {color.darker(200).name()}; "
            "border-radius: 3px;"
        )
        box.resize(24, 24)  # same as conveyor box size
        box.show()
        box.lower() 

        # Start at gripper center
        arm_pos = self.arm.mapTo(self.scene, self.arm.gripper_center())
        start_rect = QtCore.QRect(int(arm_pos.x() - 12), int(arm_pos.y() - 12), 24, 28)

        # End at target container center
        end_pos = target_widget.mapTo(self.scene, target_widget.rect().center())
        end_rect = QtCore.QRect(end_pos.x() - 12, end_pos.y() - 12, 24, 28)

        anim = QPropertyAnimation(box, b"geometry", self)
        anim.setDuration(500)
        anim.setStartValue(start_rect)
        anim.setEndValue(end_rect)
        anim.finished.connect(box.deleteLater)
        anim.start()

    # ---------- Packing count & new error detection ----------
    def _on_item_packed(self):
        if not self._containers:
            return
        active = self._containers[0]
        if active["fading"]:
            return

        # audio at pack
        try:
            self.audio.play_robotic_arm()
        except Exception:
            pass

        raw_packed = getattr(self.arm, "held_box_color", None)
        packed_color = self._normalize_box_color(raw_packed)
        active_color = self._normalize_box_color(active.get("color"))

        # increment front container count
        active["count"] += 1
        self._update_label(active)

        # fly-in animation
        target_widget = active["widget"]
        if getattr(self.arm, "held_box_color", None):
            self._animate_flying_box(self.arm.held_box_color, target_widget)
        try:
            get_logger().log_robot("Packaging", f"pack {active['count']}/{active['capacity']} color={packed_color}")
        except Exception:
            pass

        # --- Error vs Correct handling ---
        if packed_color is not None and active_color is not None and (packed_color != active_color):
            # Wrong placement: append to queue, display the first pending color
            q = active.setdefault("mis_queue", [])
            q.append(packed_color)
            active["mis_color"] = q[0]
            active["mis_count"] = len(q)
            active["error"] = True
            active["fixed"] = False
            active["err_start"] = time.time()

            try:
                # Play incorrect chime immediately (alarm handled later by _update_alarm_state)
                self.audio.play_incorrect()
            except Exception:
                pass
            self._apply_error_visuals()
            if self.worker:
                self.worker.rearm_fade()
        else:
            # Correct placement
            try:
                self.audio.play_correct()
            except Exception:
                pass

        if self.worker:
            is_error = (packed_color is not None and 
                        active_color is not None and 
                        (packed_color != active_color))
            self.worker.record_pack(is_error=is_error)

        # Fade condition
        if self._should_fade_current or (active["count"] >= active["capacity"] > 0):
            if not active["fading"]:
                self._begin_fade_and_shift_front()


    # ---------- Fade helpers (front and mid-line) ----------
    def _begin_fade_and_shift_front(self):
        """Fade current front, shift row, append next color in rotation."""
        if not self._containers:
            return
        self._fade_and_remove_at_index(0)

    def _begin_fade_and_shift_other(self, idx: int):
        """Fade out container at index `idx` (0-based), then remove it and append a new
        container using the rotation color. If idx == 0, delegate to _begin_fade_and_shift()."""
        if not (0 <= idx < len(self._containers)):
            return
        if idx == 0:
            # Use the existing front-fade logic
            self._begin_fade_and_shift()
            return

        rec = self._containers[idx]
        if rec.get("fading"):
            return

        rec["fading"] = True
        eff = rec["effect"]; anim = rec["anim"]; w = rec["widget"]
        anim.stop()
        eff.setOpacity(1.0)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)

        def _finished():
            # remove the faded one
            w.hide()
            self._row_layout.removeWidget(w)
            try:
                self._containers.pop(idx)
            except Exception:
                pass

            # append a new container using rotation
            new_color = self._rot[self._next_idx]
            new_cap = PackagingWorker.pick_capacity() if (self.worker and self.worker.isRunning()) else 0
            new_rec = self._create_new_container(initial_cap=new_cap, color=new_color)
            self._containers.append(new_rec)
            self._row_layout.addWidget(new_rec["widget"])

            # advance rotation
            self._next_idx = (self._next_idx + 1) % 3

            # refresh positions/visuals
            for r in self._containers:
                self._position_label(r)
                self._position_badge(r)
            self._apply_error_visuals()

            # re-check front batch scheduling (front might be unaffected, but safe)
            self._schedule_batch_for_front()

        try:
            anim.finished.disconnect()
        except Exception:
            pass
        anim.finished.connect(_finished)
        anim.start()


    def _fade_and_remove_at_index(self, idx):
        """Generic fade-out for any container at index idx (0..n-1)."""
        if idx < 0 or idx >= len(self._containers):
            return
        rec = self._containers[idx]
        w = rec["widget"]
        eff = rec["effect"]
        anim = rec["anim"]

        # If this is the front, stop batch + selection, reset fade flags
        if idx == 0:
            self._batch_active = False
            self._batch_remaining = 0
            self._batch_color = None
            if self._box_timer.isActive():
                self._box_timer.stop()
            self._selected_active = False
            self._selected_expected = None
            self._should_fade_current = False

        # Mark fading and prep animation
        rec["fading"] = True
        try:
            anim.stop()
        except Exception:
            pass
        eff.setOpacity(1.0)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)

        def _finished():
            # remove widget and record
            w.hide()
            self._row_layout.removeWidget(w)
            try:
                self._containers.pop(idx)
            except Exception:
                pass

            # append new container using rotation color
            new_color = self._rot[self._next_idx]
            new_cap = PackagingWorker.pick_capacity() if (self.worker and self.worker.isRunning()) else 0
            new_rec = self._create_new_container(initial_cap=new_cap, color=new_color)
            self._containers.append(new_rec)
            self._row_layout.addWidget(new_rec["widget"])

            # labels/badges
            for rec2 in self._containers:
                self._position_label(rec2)
                self._position_badge(rec2)

            # next rotation color
            self._next_idx = (self._next_idx + 1) % 3

            # If we removed the front, inform worker about new active container
            if idx == 0 and self.worker and self._containers:
                leftmost = self._containers[0]
                self.worker.begin_container(leftmost["capacity"], leftmost.get("color"))
                try:
                    get_logger().log_robot(
                        "Packaging",
                        f"begin_container capacity={leftmost['capacity']} color={leftmost.get('color')}"
                    )
                except Exception:
                    pass
                # refresh visuals
                self._apply_error_visuals()
                # Schedule the exact batch for the new front
                self._schedule_batch_for_front()
            else:
                # For mid-line removals, just refresh visuals (front unchanged)
                self._apply_error_visuals()

        try:
            anim.finished.disconnect()
        except Exception:
            pass
        anim.finished.connect(_finished)
        anim.start()

    # ---------- Create container ----------
    def _create_new_container(self, initial_cap=None, color=None):
        w = StorageContainerWidget()
        c = color or self._rot[self._next_idx]
        self._apply_style_by_color(w, c)
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

        badge = QLabel("!", w)
        badge.setFixedSize(40, 40)
        badge.setAlignment(Qt.AlignCenter)
        badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        badge.hide()

        eff = QGraphicsOpacityEffect(w); w.setGraphicsEffect(eff); eff.setOpacity(1.0)
        anim = QPropertyAnimation(eff, b"opacity", self); anim.setDuration(2000)
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
            "badge": badge,
            "color": c,
            "mis_color": None,
            "batch_spawned": False,
            "err_start": None,
        }
        self._position_label(rec)
        self._position_badge(rec)
        return rec

    # ---------- Worker hook (now just a scheduler poke) ----------
    def spawn_box_from_worker(self, box_data=None):
        """
        Called by worker pacing; we now use it only to (re)check and schedule
        the batch for the current lead.
        """
        self._schedule_batch_for_front()

    # ---------- Lifecycle ----------
    def start(self, pace=None, error_rate=None, limit="4 - 6"):
        # --- Guard: only run if this task is enabled ---
        if not getattr(self, "enabled", True):
            return

        self.conveyor.setBeltSpeed(120)
        self.conveyor.enable_motion(True)
        # conveyor audio
        try:
            self.audio.start_conveyor()
        except Exception:
            pass

        if self._box_timer.isActive():
            self._box_timer.stop()

        # --- dynamic box spacing based on pace ---
        spacing_map = {"slow": 3000, "medium": 2000, "fast": 1000}
        interval = spacing_map.get(pace, 500)
        self._box_timer.setInterval(interval)

        if not self.worker or not self.worker.isRunning():
            self.worker = PackagingWorker(pace=pace, error_rate=error_rate)
            self.worker.limit = limit  # <-- store selected limit on worker
            self.worker.box_spawned.connect(self.spawn_box_from_worker)
            self.worker.metrics_ready.connect(self._on_metrics)
            self.worker.container_should_fade.connect(self._on_worker_fade)
            self.worker.metrics_live.connect(self._on_metrics_live)
            self.worker.start()

        # reset counts/caps (colors remain fixed per rotation)
        for rec in self._containers:
            rec["count"] = 0
            rec["capacity"] = PackagingWorker.pick_capacity(limit)  # <-- use chosen limit
            rec["error"] = False
            rec["fixed"] = False
            rec["err_start"] = None
            rec["anim"].stop()
            rec["effect"].setOpacity(1.0)
            rec["widget"].show()
            rec["fading"] = False
            rec["batch_spawned"] = False
            rec["widget"].border = rec.get("orig_border", rec["widget"].border)
            if rec.get("badge"):
                rec["badge"].hide()
            self._update_label(rec)

        # tell worker the active container's capacity and color
        if self._containers:
            leftmost = self._containers[0]
            self.worker.begin_container(leftmost["capacity"], leftmost.get("color"))
            try:
                get_logger().log_robot(
                    "Packaging",
                    f"begin_container capacity={leftmost['capacity']} color={leftmost.get('color')}"
                )
            except Exception:
                pass
        self._should_fade_current = False

        if not self._flash_timer.isActive():
            self._flash_timer.start()

        # arm FSM start
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._pick_state = "idle"
        self._pick_t = 0
        if not self._pick_timer.isActive():
            sh, el = self._pose_home()
            self._set_arm(sh, el)
            self._pick_timer.start()

        # clear selection state
        self._selected_active = False
        self._selected_expected = None

        # Schedule the exact batch for the initial front
        self._schedule_batch_for_front()

        # ensure alarm/audio clean slate
        self._alarm_active = False
        try:
            self.audio.cancel_alarm_delay()
            self.audio.stop_alarm()
        except Exception:
            pass

        try:
            get_logger().log_user(
                "Packaging",
                "control",
                "start",
                f"pace={pace},error_rate={error_rate},limit={limit}"
            )
        except Exception:
            pass


    def pause(self):
        self.conveyor.enable_motion(False)
        if self._box_timer.isActive():
            self._box_timer.stop()
        if self._pick_timer.isActive():
            self._pick_timer.stop()

        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(500)

        if self._flash_timer.isActive():
            self._flash_timer.stop()
        self._flash_on = False

        self._selected_active = False
        self._selected_expected = None
        self._batch_active = False
        self._batch_remaining = 0
        self._batch_color = None

        if hasattr(self.conveyor, "_boxes"):
            self.conveyor._boxes.clear()
        if hasattr(self.conveyor, "_box_colors"):
            self.conveyor._box_colors.clear()
        self.conveyor.update()

        try:
            self.audio.stop_conveyor()
            self.audio.stop_alarm()
            self.audio.cancel_alarm_delay()
        except Exception:
            pass
        self._alarm_active = False

        sh, el = self._pose_home()
        self._set_arm(sh, el)
        self.arm.held_box_visible = False
        self.arm.update()

    def stop(self):
        self.conveyor.enable_motion(False)
        if self._box_timer.isActive():
            self._box_timer.stop()
        if self._pick_timer.isActive():
            self._pick_timer.stop()

        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(500)

        if self._flash_timer.isActive():
            self._flash_timer.stop()
        self._flash_on = False

        # clear selection & batch state
        self._selected_active = False
        self._selected_expected = None
        self._batch_active = False
        self._batch_remaining = 0
        self._batch_color = None

        #  clear all boxes from the conveyor 
        if hasattr(self.conveyor, "_boxes"):
            self.conveyor._boxes.clear()
        if hasattr(self.conveyor, "_box_colors"):
            self.conveyor._box_colors.clear()
        self.conveyor.update()

        # stop audios
        try:
            self.audio.stop_conveyor()
            self.audio.stop_alarm()
            self.audio.cancel_alarm_delay()
        except Exception:
            pass
        self._alarm_active = False

        sh, el = self._pose_home()
        self._set_arm(sh, el)
        self.arm.held_box_visible = False
        self.arm.update()

        try:
            get_logger().log_user("Packaging", "control", "stop", "stopped by user")
        except Exception:
            pass

        # ===== reset metrics =====
        if hasattr(self, "metrics_manager"):
            self.metrics_manager.reset_metrics()

    def _on_metrics(self, metrics):
        try:
            get_logger().log_robot(
                "Packaging",
                f"metrics total={metrics.get('pack_total')} errors={metrics.get('pack_errors')} "
                f"acc={metrics.get('pack_accuracy'):.2f}% ipm={metrics.get('pack_items_per_min'):.2f}"
            )
        except Exception:
            pass
        print("Packaging metrics:", metrics)

    # ---------- Arm poses ----------
    def _pose_home(self):    return (-90.0, 0.0)
    def _pose_prep(self):    return (-92.0, -12.0)
    def _pose_pick(self):    return (-110.0, -95.0)
    def _pose_lift(self):    return (-93.0, -10.0)
    def _pose_present(self): return (40.0,  10.0)

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
        self._now_ms += self._pick_timer.interval()

        if self._pick_state == "idle":
            if self._box_near_grip() and (self._now_ms - self._last_touch_time_ms) >= self._touch_cooldown_ms:
                self._last_touch_time_ms = self._now_ms
                self._pick_state = "to_prep"
                self._start_seg(self._pose_prep(), 120)
            else:
                return

        self._pick_t += self._pick_timer.interval()
        t = min(1.0, self._pick_t / float(self._pick_duration))
        s0, e0 = self._pick_from
        s1, e1 = self._pick_to
        s = s0 + (s1 - s0) * t
        e = e0 + (e1 - e0) * t
        self._set_arm(s, e)

        if self._pick_state in ("hold", "lift"):
            self._despawn_if_past_cutoff()

        if t >= 1.0:
            if self._pick_state == "to_prep":
                self._pick_state = "descend"
                self._start_seg(self._pose_pick(), 120)

            elif self._pick_state == "descend":
                # play robotic arm sound as it reaches the box
                try:
                    self.audio.play_robotic_arm()
                except Exception:
                    pass
                c = self._color_of_box_in_window()
                if c is not None:
                    self.arm.held_box_color = c
                    self.arm.held_box_visible = True
                    self.arm.update()
                self._pick_state = "hold"
                self._start_seg(self._pose_pick(), 40)

            elif self._pick_state == "hold":
                self._pick_state = "lift"
                self._start_seg(self._pose_lift(), 120)

            elif self._pick_state == "lift":
                self._pick_state = "present"
                self._start_seg(self._pose_present(), 200)

            elif self._pick_state == "present":
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

    # ---------- Belt/box helpers ----------
    def _grip_x(self):
        return self.conveyor.width() * 0.44 # Change this value to increate/decrease the position where the robot arm picks up a box

    def _box_near_grip(self):
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes: return False
        gx = self._grip_x(); w = self._touch_window_px
        for x in boxes:
            if (gx - w) <= x <= (gx + w):
                return True
        return False

    def _despawn_if_past_cutoff(self):
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes: return
        colors = getattr(self.conveyor, "_box_colors", None)
        detect_x = self._grip_x()
        cutoff_x = detect_x + self._despawn_offset_px
        hit_index = -1
        for i, x in enumerate(boxes):
            if x >= cutoff_x:
                hit_index = i; break
        if hit_index != -1:
            del boxes[hit_index]
            if isinstance(colors, list) and hit_index < len(colors):
                del colors[hit_index]
            self.conveyor.update()

    def _color_of_box_in_window(self):
        boxes = getattr(self.conveyor, "_boxes", None)
        cols  = getattr(self.conveyor, "_box_colors", None)
        if not boxes or not cols: return None
        gx = self._grip_x(); w = self._touch_window_px
        for i, x in enumerate(boxes):
            if (gx - w) <= x <= (gx + w):
                if i < len(cols):
                    return cols[i]
        return None

    # ---------- Error smart-fix (click to pick, click to place — one attempt) ----------
    def _smart_fix_pick_or_place(self, clicked_rec):
        """
        One-attempt fix flow with queued errors:
          - Click front (if errored) to pick the *next* wrong color (queue head).
          - Click ANY container to place:
              - If target color == expected (queue head) -> remove one from queue.
              - Else -> still consume one from the queue (user moved the wrong item).
          - Keep error active until the queue is empty; then clear.
          - If a non-front container becomes full due to the drop, fade it immediately.
        """
        if not self._containers:
            return

        # Identify indices
        try:
            idx_clicked = self._containers.index(clicked_rec)
        except ValueError:
            return
        front = self._containers[0]

        # Cancel fading if user starts fixing an errored, fading front
        if idx_clicked == 0 and front.get("fading") and front.get("error"):
            front["fading"] = False
            self._should_fade_current = False
            eff = front["effect"]; anim = front["anim"]
            anim.stop()
            eff.setOpacity(1.0)
            try:
                get_logger().log_user("Packaging", "container_front", "cancel_fade", "error fix started")
            except Exception:
                pass
            # continue into normal pick flow

        # 1) If no selection yet: click front (if errored) to pick it
        if not self._selected_active:
            if idx_clicked == 0 and front.get("error"):
                q = front.setdefault("mis_queue", [])
                # expected color is always the queue head
                self._selected_active = True
                self._selected_expected = (q[0] if q else front.get("mis_color"))
                self._apply_error_visuals()  # amber border on front

                # --- Spawn ghost box matching expected color ---
                if self._selected_expected:
                    qcolor = QColor("#e74c3c") if self._selected_expected == "red" \
                             else QColor("#3498db") if self._selected_expected == "blue" \
                             else QColor("#27ae60")
                    self._start_drag_box(qcolor)

                try:
                    get_logger().log_user("Packaging", "container_front", "pick",
                                          f"needs={self._selected_expected}")
                except Exception:
                    pass
            else:
                try:
                    get_logger().log_user("Packaging", "container", "click", "no selection active")
                except Exception:
                    pass
            return

        # 2) Selection active: clicking ANY container attempts a drop
        target_color = clicked_rec.get("color")
        expected = self._selected_expected
        if expected is None:
            self._selected_active = False
            self._end_drag_box()
            self._apply_error_visuals()
            return

        # Consume 1 from front either way (we're removing a wrong item from the front)
        if front["count"] > 0:
            front["count"] -= 1
            self._update_label(front)
        clicked_rec["count"] += 1
        self._update_label(clicked_rec)

        self._total_corrections += 1

        # Update the error queue
        q = front.setdefault("mis_queue", [])
        if q:
            # Remove the head regardless of where it was dropped
            q.pop(0)
        front["mis_count"] = len(q)
        front["mis_color"] = q[0] if q else None
        front["error"] = bool(q)
        front["fixed"] = not q

        if target_color == expected:
            self._correct_corrections += 1
            try:
                self.audio.play_correct()
            except Exception:
                pass
            try:
                get_logger().log_user("Packaging", f"container_{target_color}", "drop", "resolved_or_progress")
            except Exception:
                pass
        else:
            # Wrong drop target: we still consumed one wrong item from the front
            try:
                self.audio.play_incorrect()
            except Exception:
                pass
            try:
                get_logger().log_user("Packaging", f"container_{target_color}", "drop",
                                      "incorrect placement (error consumed)")
            except Exception:
                pass

        # If a non-front container filled due to this drop, fade it right away
        if idx_clicked != 0:
            cap = int(clicked_rec.get("capacity", 0))
            cnt = int(clicked_rec.get("count", 0))
            if cap > 0 and cnt >= cap and not clicked_rec.get("fading"):
                self._begin_fade_and_shift_other(idx_clicked)

        # Reset selection/visuals
        self._selected_active = False
        self._selected_expected = None
        self._end_drag_box()
        self._apply_error_visuals()

        if self.worker:
            self.worker.rearm_fade()


    # --- Drag ghost helpers ---
    def _start_drag_box(self, color: QColor):
        """Spawn a small label that follows the mouse pointer until dropped."""
        if self._drag_label:
            self._drag_label.deleteLater()

        lbl = QLabel(self.scene)  # keep ghost in scene so it's global
        lbl.setStyleSheet(
            f"background-color: {color.name()}; "
            f"border: 1px solid {color.darker(200).name()}; "
            "border-radius: 3px;"
        )
        lbl.resize(24, 24)
        lbl.show()
        lbl.lower()

        self._drag_label = lbl
        self._drag_color = color

        from PyQt5 import QtGui
        global_pos = QtGui.QCursor.pos()
        scene_pos = self.scene.mapFromGlobal(global_pos)
        w, h = lbl.width(), lbl.height()
        lbl.move(scene_pos.x() - w // 2, scene_pos.y() - h // 2)

        if not self._drag_timer.isActive():
            self._drag_timer.start()

    def _end_drag_box(self):
        """Remove the drag label and stop following."""
        if self._drag_timer.isActive():
            self._drag_timer.stop()
        if self._drag_label:
            self._drag_label.deleteLater()
            self._drag_label = None
        self._drag_color = None

    def _update_drag_ghost(self):
        """Timer tick: keep ghost glued to the cursor."""
        if not self._drag_label:
            return
        from PyQt5 import QtGui
        global_pos = QtGui.QCursor.pos()
        scene_pos = self.scene.mapFromGlobal(global_pos)
        w, h = self._drag_label.width(), self._drag_label.height()
        self._drag_label.move(scene_pos.x() - w // 2, scene_pos.y() - h // 2)


    def _mark_fixed_visual(self, rec):
        w = rec["widget"]
        # back to original (no green success outline)
        w.border = rec.get("orig_border", w.border)
        w.update()

    # ---------- Keep labels centered + handle clicks ----------
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            for rec in self._containers:
                if obj is rec["widget"]:
                    self._position_label(rec)
                    self._position_badge(rec)
                    break
        if event.type() == QEvent.MouseButtonPress:
            for rec in self._containers:
                if obj is rec["widget"]:
                    self._smart_fix_pick_or_place(rec)
                    return True
        return super().eventFilter(obj, event)

    def _on_metrics_live(self, metrics):
        if hasattr(self, "metrics_manager") and self.metrics_manager:
            if self._total_corrections > 0:
                metrics['pack_correction_rate'] = (self._correct_corrections / self._total_corrections) * 100
            else:
                metrics['pack_correction_rate'] = 0.0

            self.metrics_manager.update_metrics(metrics)

        # --- Log 3 core metrics every update ---
        oc = getattr(self, "observer_control", None)  # injected from LayoutController
        if oc:
            ts = oc.get_timestamp()  # MM:SS from ObserverControl timer
            logger = get_logger()

            logger.log_metric(ts, "packaging", "boxes packed", metrics.get("pack_total", 0))
            logger.log_metric(ts, "packaging", "errors", metrics.get("pack_errors", 0))
            logger.log_metric(ts, "packaging", "errors corrected", self._correct_corrections)

