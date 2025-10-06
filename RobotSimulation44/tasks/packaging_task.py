# tasks/packaging_task.py
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

        # Audio
        self.audio = AudioManager()
        self._alarm_active = False  # track alarm state

        # Robot arm visuals
        self.arm.shoulder_angle = -90
        self.arm.elbow_angle = 0
        self.arm.c_arm = QColor("#8e44ad")
        self.arm.c_arm_dark = QColor("#6d2e8a")

        # Layout
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=6, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=6, align=Qt.AlignHCenter | Qt.AlignBottom),
            col_stretch=[1, 1, 1],
            row_stretch=[0, 0, 1],  # row index 2 gets the stretch
            spacing=18
        )

        # Style helper
        def _apply_style_by_color(w, color: str):
            c = (color or "").lower()
            if c == "red":
                w.border = QColor("#8c1f15")
                w.fill_top = QColor("#ffd6d1")
                w.fill_bottom = QColor("#ffb8b0")
                w.rib = QColor(140, 31, 21, 110)
            elif c == "blue":
                w.border = QColor("#2b4a91")
                w.fill_top = QColor("#dbe8ff")
                w.fill_bottom = QColor("#c7daff")
                w.rib = QColor(43, 74, 145, 110)
            elif c == "green":
                w.border = QColor("#1f7a3a")
                w.fill_top = QColor("#d9f7e6")
                w.fill_bottom = QColor("#bff0d3")
                w.rib = QColor(31, 122, 58, 110)
            elif c == "purple":
                w.border = QColor("#6a1b9a")
                w.fill_top = QColor("#f0e3ff")
                w.fill_bottom = QColor("#e3ccff")
                w.rib = QColor(106, 27, 154, 110)
            elif c == "orange":
                w.border = QColor("#c15800")
                w.fill_top = QColor("#ffe8cc")
                w.fill_bottom = QColor("#ffd4a8")
                w.rib = QColor(193, 88, 0, 110)
            elif c == "teal":
                w.border = QColor("#00796b")
                w.fill_top = QColor("#d2f5ef")
                w.fill_bottom = QColor("#b8efe6")
                w.rib = QColor(0, 121, 107, 110)
            else:
                # default to green-ish
                w.border = QColor("#1f7a3a")
                w.fill_top = QColor("#d9f7e6")
                w.fill_bottom = QColor("#bff0d3")
                w.rib = QColor(31, 122, 58, 110)

        self._apply_style_by_color = _apply_style_by_color

        # Remove BaseTask's default single container (prevents “stray” widget)
        if hasattr(self, "container") and self.container is not None:
            try:
                self.grid.removeWidget(self.container)
            except Exception:
                pass
            self.container.hide()
            self.container.setParent(None)
            self.container.deleteLater()
            self.container = None

        # Build all six containers once
        def _make_container(color_name: str):
            w = StorageContainerWidget()
            self._apply_style_by_color(w, color_name)
            w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

            # Packaging-only UI bits
            lbl = QLabel(w)
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            lbl.setStyleSheet(
                "font-weight: 700; font-size: 18px; color: #222;"
                "background: rgba(255,255,255,200);"
                "padding: 2px 8px; border-radius: 8px;"
                "border: 1px solid rgba(0,0,0,60);"
            )
            lbl.setText("0/0")
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
                "capacity": 0,
                "count": 0,
                "effect": eff,
                "anim": anim,
                "fading": False,
                "error": False,
                "fixed": False,
                "orig_border": w.border,
                "badge": badge,
                "color": color_name,
                "mis_color": None,
                "batch_spawned": False,
                "err_start": None,
                "mis_queue": [],
            }
            return rec

        self._all_colors = ["red", "blue", "green", "purple", "orange", "teal"]
        self._all = {c: _make_container(c) for c in self._all_colors}

        # Group all containers into one tight horizontal row (centered)
        self._row = QWidget()
        self._row_layout = QHBoxLayout(self._row)
        self._row_layout.setContentsMargins(0, 0, 0, 0)
        self._row_layout.setSpacing(12)
        for c in self._all_colors:
            self._row_layout.addWidget(self._all[c]["widget"])

        # IMPORTANT: place the row on grid row 2 (the stretched row)
        self.grid.addWidget(self._row, 2, 0, 1, 6, Qt.AlignHCenter | Qt.AlignTop)

        # Click handling parity
        self._slot_to_widget = {c: self._all[c]["widget"] for c in self._all_colors}

        # Ordered visible list; start() will filter visibility.
        self._containers = [self._all[c] for c in self._all_colors]

        # flashing timer for error badges
        self._flash_on = False
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(350)
        self._flash_timer.timeout.connect(self._on_flash_tick)

        # drag ghost
        self._drag_label = None
        self._drag_color = None
        self._drag_timer = QTimer(self)
        self._drag_timer.setInterval(16)
        self._drag_timer.timeout.connect(self._update_drag_ghost)

        # drip/batch spawner
        self._box_timer = QTimer(self)
        self._box_timer.setInterval(1500)
        self._box_timer.timeout.connect(self._drip_spawn_tick)

        # batch state
        self._batch_active = False
        self._batch_color = None
        self._batch_remaining = 0
        
        # gap between color batches (ms)
        self._batch_gap_ms = 3000

        # arm FSM
        self._pick_timer = QTimer(self)
        self._pick_timer.setInterval(16)
        self._pick_timer.timeout.connect(self._tick_pick)
        self._pick_state = "idle"
        self._pick_t = 0
        self._pick_duration = 0
        thetas = (self.arm.shoulder_angle, self.arm.elbow_angle)
        self._pick_from = thetas
        self._pick_to = thetas
        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._touch_window_px = 18
        self._touch_cooldown_ms = 120
        self._despawn_offset_px = 0

        self._should_fade_current = False

        # selection state
        self._selected_active = False
        self._selected_expected = None
        self._selected_source = None  # the bin we "picked" from

        # Held box metadata
        self._held_intended_color = None

        # per-box intended-color ring, aligned with conveyor _boxes
        self._intended_colors = []  # list[str]; same length/order as self.conveyor._boxes/_box_colors

        # metrics for corrections
        self._total_corrections = 0
        self._correct_corrections = 0

        # worker
        self.worker = None

        # initial paint
        self.arm.update()
        self.conveyor.update()
        for rec in self._all.values():
            rec["widget"].update()
            self._position_label(rec)

    # UI helpers
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

    # Error visuals + alarm
    def _apply_error_visuals(self):
        for i, rec in enumerate(self._containers):
            w = rec["widget"]
            badge = rec.get("badge")

            # highlight selected source bin (yellow border)
            if self._selected_active and rec is self._selected_source:
                w.border = QColor("#ffbf00")
                w.update()
                if badge:
                    badge.hide()
                continue

            if rec.get("fixed"):
                if badge: badge.hide()
                w.border = rec.get("orig_border", w.border)
                w.update()
                continue

            if rec.get("error"):
                mis = rec.get("mis_color")
                color_map = {
                    "red": QColor("#c82828"),
                    "blue": QColor("#2b4a91"),
                    "green": QColor("#1f7a3a"),
                    "purple": QColor("#6a1b9a"),
                    "orange": QColor("#c15800"),
                    "teal": QColor("#b8efe6"),
                }
                flash_color = color_map.get(mis, QColor("#e74c3c"))
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
                if badge: badge.hide()
                w.border = rec.get("orig_border", w.border)
                w.update()

        self._update_alarm_state()

    def _on_flash_tick(self):
        self._flash_on = not self._flash_on
        self._apply_error_visuals()

    # Alarm helpers
    def _any_error_and_oldest_age(self):
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
        has_err, oldest_age = self._any_error_and_oldest_age()
        if has_err:
            if oldest_age >= 2.0 and not self._alarm_active:
                self.play_sound("alarm")
                self._alarm_active = True
        else:
            if self._alarm_active:
                self.audio.stop_alarm()
                self._alarm_active = False
            try:
                self.audio.cancel_alarm_delay()
            except Exception:
                pass

    # Spawning & batches (batch = spawn planner ONLY)
    def _count_boxes_on_belt(self, color: str) -> int:
        cols = getattr(self.conveyor, "_box_colors", None)
        if not isinstance(cols, list):
            return 0
        norm = self._normalize_box_color
        return sum(1 for c in cols if norm(c) == color)

    def _need_for_color(self, color: str) -> int:
        # How many more boxes of this color we still need to spawn to fill its container 
        rec = next((r for r in self._containers
                    if r.get("color") == color and r["widget"].isVisible()), None)
        if not rec:
            return 0
        cap = int(rec.get("capacity", 0))
        cnt = int(rec.get("count", 0))
        if cap <= 0:
            return 0
        on_belt = self._count_boxes_on_belt(color)
        return max(0, cap - cnt - on_belt)

    def _pick_next_batch_color(self) -> str:
        # Pick randomly among colors that still need boxes 
        candidates = []
        for rec in self._containers:
            if not rec["widget"].isVisible():
                continue
            color = rec.get("color")
            need = self._need_for_color(color)
            if need > 0:
                candidates.append(color)
        if not candidates:
            return None
        return random.choice(candidates)

    def _ensure_batch(self):
        # Ensure there is a running batch; if none, pick a random color that still needs boxes 
        # If current batch color no longer needs boxes, end it
        if self._batch_active and self._need_for_color(self._batch_color) <= 0:
            self._batch_active = False
            self._batch_color = None
            self._batch_remaining = 0
            if self._box_timer.isActive():
                self._box_timer.stop()

        if self._batch_active:
            if not self._box_timer.isActive():
                self._box_timer.start()
            return

        # Pick a new batch color that needs boxes
        nxt = self._pick_next_batch_color()
        if not nxt:
            if self._box_timer.isActive():
                self._box_timer.stop()
            return

        need = self._need_for_color(nxt)
        self._batch_color = nxt
        self._batch_remaining = need      # informational
        self._batch_active = need > 0

        if self._batch_active and not self._box_timer.isActive():
            self._box_timer.start()

        try:
            get_logger().log_robot("Packaging", f"new_batch color={self._batch_color} need={self._batch_remaining}")
        except Exception:
            pass

    def _drip_spawn_tick(self):
        # Spawn boxes for the current batch color; with probability=error_rate, spawn a different (visible) color. Also snapshot intended_color per box 
        if not self._batch_active or not self._batch_color:
            self._ensure_batch()
            return

        remain = self._need_for_color(self._batch_color)
        if remain <= 0:
            # End this batch and add a small gap before next batch.
            self._batch_active = False
            self._batch_color = None
            self._batch_remaining = 0
            if self._box_timer.isActive():
                self._box_timer.stop()
            QTimer.singleShot(self._batch_gap_ms, self._ensure_batch)
            return

        # Intended color for this spawned box
        intended_color = self._batch_color

        # Default: actual == intended
        spawn_color = intended_color

        # With probability error_rate, choose a different visible color (not intended)
        if self.worker and random.random() < float(self.worker.error_rate or 0.0):
            visible = [r["color"] for r in self._containers if r["widget"].isVisible()]
            wrong_choices = [c for c in visible if c != intended_color]
            if wrong_choices:
                spawn_color = random.choice(wrong_choices)

        # Put the box on the belt (actual_color)
        self.conveyor.spawn_box(color=spawn_color)

        # append intended_color aligned with the newly spawned box
        self._intended_colors.append(intended_color)

        # Informational decrement; actual "need" recalculated each tick
        self._batch_remaining = max(0, self._batch_remaining - 1)

        # If we've met the actual need, finish this batch and schedule the next after a small gap
        if self._need_for_color(self._batch_color) <= 0:
            self._batch_active = False
            self._batch_color = None
            self._batch_remaining = 0
            if self._box_timer.isActive():
                self._box_timer.stop()
            QTimer.singleShot(self._batch_gap_ms, self._ensure_batch)

    # Normalize color helper
    def _normalize_box_color(self, c):
        if isinstance(c, str):
            s = c.strip().lower()
            return s if s in ("red", "blue", "green", "purple", "orange", "teal") else None
        try:
            hexv = c.name().lower()
        except Exception:
            return None
        hex_map = {
            "#c82828": "red",
            "#2b4a91": "blue",
            "#1f7a3a": "green",
            "#6a1b9a": "purple",
            "#c15800": "orange",
            "#b8efe6": "teal",
        }
        return hex_map.get(hexv)

    # Worker hooks
    def spawn_box_from_worker(self, box_data=None):
        # Heartbeat; keep batches healthy
        self._ensure_batch()

    def _on_worker_fade(self, mode, at_count, capacity, secs):
        # With direct-to-color placement, we manage fades per-container locally.
        self._ensure_batch()

    # Animate + pack
    def _animate_flying_box(self, color, target_widget):
        if not target_widget:
            return
        box = QLabel(self.scene)
        box.setStyleSheet(
            f"background-color: {color.name()}; "
            f"border: 1px solid {color.darker(200).name()}; "
            "border-radius: 3px;"
        )
        box.resize(24, 24)
        box.show()
        box.lower()
        arm_pos = self.arm.mapTo(self.scene, self.arm.gripper_center())
        start_rect = QtCore.QRect(int(arm_pos.x() - 12), int(arm_pos.y() - 12), 24, 28)
        end_pos = target_widget.mapTo(self.scene, target_widget.rect().center())
        end_rect = QtCore.QRect(end_pos.x() - 12, end_pos.y() - 12, 24, 28)
        anim = QPropertyAnimation(box, b"geometry", self)
        anim.setDuration(500)
        anim.setStartValue(start_rect)
        anim.setEndValue(end_rect)
        anim.finished.connect(box.deleteLater)
        anim.start()

    # helpers to find box index in grip window, and keep lists in sync
    def _index_of_box_in_window(self):
        boxes = getattr(self.conveyor, "_boxes", None)
        if not boxes:
            return -1
        gx = self._grip_x()
        w = self._touch_window_px
        for i, x in enumerate(boxes):
            if (gx - w) <= x <= (gx + w):
                return i
        return -1

    def _actual_color_at_index(self, idx):
        cols = getattr(self.conveyor, "_box_colors", None)
        if not isinstance(cols, list) or idx < 0 or idx >= len(cols):
            return None
        return cols[idx]

    def _on_item_packed(self):
        # Place by intended color (snapshotted at spawn). Error if actual != intended 
        if not self._containers:
            return

        try:
            self.play_sound("robotic_arm")
        except Exception:
            pass

        # Held visuals (actual color)
        raw_packed = getattr(self.arm, "held_box_color", None)
        actual_color = self._normalize_box_color(raw_packed)

        # Intended must be snapshotted earlier (at pick)
        intended_color = self._held_intended_color

        # No intended? Do nothing (strict to spec — never fallback to actual/current batch)
        if intended_color is None:
            return

        # Find destination bin by intended color; it must be visible and not fading
        target_idx, target_rec = None, None
        for i, rec in enumerate(self._containers):
            if rec["widget"].isVisible() and rec.get("color") == intended_color and not rec.get("fading"):
                target_idx, target_rec = i, rec
                break

        # If intended bin isn't available (hidden or fading), skip placement entirely
        if target_rec is None:
            self._held_intended_color = None
            return

        # Update counts
        target_rec["count"] += 1
        self._update_label(target_rec)

        # Animate to intended bin
        target_widget = target_rec["widget"]
        if getattr(self.arm, "held_box_color", None):
            self._animate_flying_box(self.arm.held_box_color, target_widget)

        # ERROR CONDITION: actual != intended
        is_error = (actual_color != intended_color)
        try:
            get_logger().log_robot(
                "Packaging",
                f"pack {target_rec['count']}/{target_rec['capacity']} "
                f"box_actual={actual_color} -> bin_intended={intended_color} {'ERROR' if is_error else 'OK'}"
            )
        except Exception:
            pass

        if is_error:
            q = target_rec.setdefault("mis_queue", [])
            q.append(actual_color)           # record wrong actual color that landed here
            target_rec["mis_color"] = q[0]
            target_rec["mis_count"] = len(q)
            target_rec["error"] = True
            target_rec["fixed"] = False
            target_rec["err_start"] = time.time()
            try:
                self.play_sound("incorrect_chime")
            except Exception:
                pass
            self._apply_error_visuals()
            if self.worker:
                self.worker.record_pack(True)
        else:
            try:
                self.play_sound("correct_chime")
            except Exception:
                pass
            if self.worker:
                self.worker.record_pack(False)

        # Capacity / fade for THIS bin
        cap = int(target_rec.get("capacity", 0))
        if cap > 0 and target_rec["count"] >= cap and not target_rec.get("fading"):
            if target_idx == 0:
                self._begin_fade_and_shift_front()
            else:
                self._begin_fade_and_shift_other(target_idx)

        # Done with this box
        self._held_intended_color = None

        # Re-evaluate batches
        self._ensure_batch()

    # Requeue SAME color after fade
    def _requeue_same_color(self, rec, was_front=False):
        # Reset the same record in-place (do NOT move its position). Re-roll capacity each time 
        limit = getattr(self, "_limit_str", None) or getattr(self.worker, "limit", "4 - 6")
        rec["capacity"] = PackagingWorker.pick_capacity(limit)

        rec["count"] = 0
        rec["error"] = False
        rec["fixed"] = False
        rec["mis_color"] = None
        rec["mis_count"] = 0
        rec["mis_queue"] = []
        rec["err_start"] = None
        rec["fading"] = False
        rec["batch_spawned"] = False

        try:
            rec["anim"].stop()
        except Exception:
            pass
        rec["effect"].setOpacity(1.0)
        rec["widget"].border = rec.get("orig_border", rec["widget"].border)
        if rec.get("badge"):
            rec["badge"].hide()

        self._update_label(rec)
        rec["widget"].show()
        self._position_label(rec)
        self._position_badge(rec)
        self._apply_error_visuals()

        # After a bin resets, reassess batches
        self._ensure_batch()

    # Fade helpers
    def _begin_fade_and_shift_front(self):
        if not self._containers:
            return
        self._fade_and_remove_at_index(0)

    def _begin_fade_and_shift_other(self, idx: int):
        if not (0 <= idx < len(self._containers)):
            return
        if idx == 0:
            self._begin_fade_and_shift_front()
            return

        rec = self._containers[idx]
        if rec.get("fading"):
            return

        rec["fading"] = True
        eff = rec["effect"]; anim = rec["anim"]; w = rec["widget"]
        try: anim.stop()
        except Exception: pass
        eff.setOpacity(1.0)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)

        def _finished():
            w.hide()
            self._requeue_same_color(rec, was_front=False)

        try:
            anim.finished.disconnect()
        except Exception:
            pass
        anim.finished.connect(_finished)
        anim.start()

    def _fade_and_remove_at_index(self, idx):
        if idx < 0 or idx >= len(self._containers):
            return
        rec = self._containers[idx]
        w = rec["widget"]; eff = rec["effect"]; anim = rec["anim"]

        if idx == 0:
            # pause any batch if it happened to be this color; we'll re-evaluate
            if self._box_timer.isActive():
                self._box_timer.stop()
            self._selected_active = False
            self._selected_expected = None
            self._selected_source = None
            self._should_fade_current = False

        rec["fading"] = True
        try: anim.stop()
        except Exception: pass
        eff.setOpacity(1.0)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)

        def _finished():
            w.hide()
            self._requeue_same_color(rec, was_front=(idx == 0))

        try:
            anim.finished.disconnect()
        except Exception:
            pass
        anim.finished.connect(_finished)
        anim.start()

    # Cancel fade on click when errored
    def _cancel_fade(self, rec):
        # Stop an in-progress fade without triggering its finished handler 
        if not rec or not rec.get("fading"):
            return
        anim = rec.get("anim")
        eff = rec.get("effect")
        w = rec.get("widget")
        try:
            anim.finished.disconnect()
        except Exception:
            pass
        try:
            anim.stop()
        except Exception:
            pass
        try:
            eff.setOpacity(1.0)
        except Exception:
            pass
        rec["fading"] = False
        if w:
            w.show()
        self._apply_error_visuals()

    # Event filter
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            for rec in self._all.values():
                if obj is rec["widget"]:
                    self._position_label(rec)
                    self._position_badge(rec)
                    break
        if event.type() == QEvent.MouseButtonPress:
            # If clicking a bin that's fading AND has an error, cancel the fade and consume the click.
            for rec in self._containers:
                if obj is rec["widget"]:
                    if rec.get("fading") and rec.get("error"):
                        # 1-click: cancel fade AND immediately start the pick/ghost
                        self._cancel_fade(rec)
                        try:
                            get_logger().log_user("Packaging", "container", "click", "cancel_fade_on_error")
                        except Exception:
                            pass
                        self._smart_fix_pick_or_place(rec)
                        return True

                    # Otherwise, proceed with click-to-fix
                    self._smart_fix_pick_or_place(rec)
                    return True

        return super().eventFilter(obj, event)

    def _smart_fix_pick_or_place(self, clicked_rec):
        # Two-click 'pick then place':
        #   1) Click errored bin to pick first wrong colour (shows drag ghost)
        #   2) Click destination bin of that colour to move one unit
        def _ghost_qcolor(name: str) -> QColor:
            return (QColor("#c82828") if name == "red"
                    else QColor("#2b4a91") if name == "blue"
                    else QColor("#1f7a3a") if name == "green"
                    else QColor("#6a1b9a") if name == "purple"
                    else QColor("#c15800") if name == "orange"
                    else QColor("#b8efe6")) # teal

        # Start a selection if none active
        if not self._selected_active:
            q = clicked_rec.setdefault("mis_queue", [])
            if clicked_rec.get("error") and q:
                self._selected_active = True
                self._selected_expected = q[0]
                self._selected_source = clicked_rec
                self._apply_error_visuals()
                try:
                    self._start_drag_box(_ghost_qcolor(self._selected_expected))
                except Exception:
                    pass
                try:
                    get_logger().log_user("Packaging", "container", "pick",
                                          f"needs={self._selected_expected}")
                except Exception:
                    pass
            else:
                try:
                    get_logger().log_user("Packaging", "container", "click", "no error / empty queue")
                except Exception:
                    pass
            return

        # We have a selected wrong colour; place onto a bin
        expected = self._selected_expected
        source = self._selected_source
        if expected is None or source is None:
            # reset inconsistent state
            self._selected_active = False
            self._selected_expected = None
            self._selected_source = None
            self._end_drag_box()
            self._apply_error_visuals()
            return

        target = clicked_rec
        target_color = target.get("color")

        # Move one unit
        if source["count"] > 0:
            source["count"] -= 1
            self._update_label(source)
        target["count"] += 1
        self._update_label(target)

        # Consume one mis-queued item
        q = source.setdefault("mis_queue", [])
        if q:
            q.pop(0)
        source["mis_count"] = len(q)
        source["mis_color"] = q[0] if q else None
        source["error"] = bool(q)
        source["fixed"] = not q
        if not source["error"]:
            source["err_start"] = None

        # Feedback + metrics
        if target_color == expected:
            self._correct_corrections += 1
            try:
                self.play_sound("correct_chime")
            except Exception:
                pass
            try:
                get_logger().log_user("Packaging", f"container_{target_color}", "drop", "resolved_or_progress")
            except Exception:
                pass
        else:
            try:
                self.play_sound("incorrect_chime")
            except Exception:
                pass
            try:
                get_logger().log_user("Packaging", f"container_{target_color}", "drop",
                                      "incorrect placement (error consumed)")
            except Exception:
                pass

        self._total_corrections += 1

        # If target hits capacity, fade it
        cap_t = int(target.get("capacity", 0))
        if cap_t > 0 and target["count"] >= cap_t and not target.get("fading"):
            try:
                idx_t = self._containers.index(target)
            except ValueError:
                idx_t = -1
            if idx_t == 0:
                self._begin_fade_and_shift_front()
            elif idx_t > 0:
                self._begin_fade_and_shift_other(idx_t)

        # Clear selection and visuals
        self._selected_active = False
        self._selected_expected = None
        self._selected_source = None
        self._end_drag_box()
        self._apply_error_visuals()

        if self.worker:
            self.worker.rearm_fade()

    # Drag ghost helpers
    def _start_drag_box(self, color: QColor):
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
        if self._drag_timer.isActive():
            self._drag_timer.stop()
        if self._drag_label:
            self._drag_label.deleteLater()
            self._drag_label = None
        self._drag_color = None

    def _update_drag_ghost(self):
        if not self._drag_label:
            return
        from PyQt5 import QtGui
        global_pos = QtGui.QCursor.pos()
        scene_pos = self.scene.mapFromGlobal(global_pos)
        w, h = self._drag_label.width(), self._drag_label.height()
        self._drag_label.move(scene_pos.x() - w // 2, scene_pos.y() - h // 2)

    # Metrics pipe
    def _on_metrics_live(self, metrics):
        metrics['pack_correction_rate'] = (
            (self._correct_corrections / self._total_corrections) * 100
            if self._total_corrections > 0 else 0.0
        )
        metrics['pack_corrections'] = self._correct_corrections

        if hasattr(self, "metrics_manager") and self.metrics_manager:
            self.metrics_manager.update_metrics(metrics)

        oc = getattr(self, "observer_control", None)
        if oc:
            ts = oc.get_timestamp()
            logger = get_logger()
            logger.log_metric(ts, "packaging", "boxes packed", metrics.get("pack_total", 0))
            logger.log_metric(ts, "packaging", "errors", metrics.get("pack_errors", 0))
            logger.log_metric(ts, "packaging", "errors corrected", self._correct_corrections)

        client = getattr(self, "network_client", None)
        if client:
            client.send({"command": "metrics", "data": metrics})

    # Arm poses
    def _pose_home(self):    return (-90.0, 0.0)
    def _pose_prep(self):    return (-92.0, -12.0)
    def _pose_pick(self):    return (-110.0, -95.0)
    def _pose_lift(self):    return (-93.0, -10.0)

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


    # FSM plumbing
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
                try:
                    self.play_sound("robotic_arm")
                except Exception:
                    pass

                # SNAPSHOT actual + intended at pick
                idx = self._index_of_box_in_window()
                if idx != -1:
                    actual_c = self._actual_color_at_index(idx)
                    intended_c = None
                    if 0 <= idx < len(self._intended_colors):
                        intended_c = self._intended_colors[idx]
                    if actual_c is not None:
                        self.arm.held_box_color = actual_c
                        self.arm.held_box_visible = True
                        self.arm.update()
                    # store intended for later placement (never fallback)
                    self._held_intended_color = intended_c

                self._pick_state = "hold"
                self._start_seg(self._pose_pick(), 40)

            elif self._pick_state == "hold":
                self._pick_state = "lift"
                self._start_seg(self._pose_lift(), 120)

            elif self._pick_state == "lift":
                # Aim toward the intended bin’s direction (slot == intended color)
                slot = self._held_intended_color or self._batch_color
                self._pick_state = "present"
                self._start_seg(self._pose_present(slot), 200)

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

    # Belt/box helpers
    def _grip_x(self):
        return self.conveyor.width() * 0.44

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
            # keep intended list in sync
            if 0 <= hit_index < len(self._intended_colors):
                del self._intended_colors[hit_index]
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

    # Lifecycle
    def start(self, pace=None, error_rate=None, limit="4 - 6", bin_count=None):
        if not getattr(self, "enabled", True):
            return

        self._limit_str = limit

        self.conveyor.setBeltSpeed(120)
        self.conveyor.enable_motion(True)
        try:
            self.play_sound("conveyor")
        except Exception:
            pass

        if self._box_timer.isActive():
            self._box_timer.stop()

        spacing_map = {"slow": 3000, "medium": 2000, "fast": 1000}
        interval = spacing_map.get(pace, 500)
        self._box_timer.setInterval(interval)

        # Decide slot_order from bin_count, then setVisible
        bc = int(bin_count) if bin_count is not None else 6
        if bc >= 6:
            slot_order = ["red", "blue", "green", "purple", "orange", "teal"]
        elif bc == 4:
            slot_order = ["blue", "green", "purple", "orange"]
        elif bc == 2:
            slot_order = ["green", "purple"]
        else:
            slot_order = self._all_colors[:max(1, bc)]

        # Show/hide only (no re-creation), then update the ordered working list
        for color, rec in self._all.items():
            rec["widget"].setVisible(color in slot_order)
        self._containers = [self._all[c] for c in slot_order]

        # reset counts/caps for visible containers
        for rec in self._containers:
            rec["count"] = 0
            rec["capacity"] = PackagingWorker.pick_capacity(limit)
            rec["error"] = False
            rec["fixed"] = False
            rec["err_start"] = None
            rec["anim"].stop()
            rec["effect"].setOpacity(1.0)
            rec["fading"] = False
            rec["batch_spawned"] = False
            rec["widget"].border = rec.get("orig_border", rec["widget"].border)
            if rec.get("badge"):
                rec["badge"].hide()
            self._update_label(rec)

        # Reset metrics when new task is started
        if hasattr(self, "metrics_manager"):
            self.metrics_manager.reset_metrics()

        # Start / restart worker (pacing + metrics)
        if self.worker is None or not self.worker.isRunning():
            self.worker = PackagingWorker(pace=pace, error_rate=error_rate, bin_count=len(slot_order))
            self.worker.limit = limit
            self.worker.box_spawned.connect(self.spawn_box_from_worker)
            self.worker.metrics_ready.connect(self._on_metrics)
            self.worker.container_should_fade.connect(self._on_worker_fade)
            self.worker.metrics_live.connect(self._on_metrics_live)
            self.worker.start()

        self._should_fade_current = False

        if not self._flash_timer.isActive():
            self._flash_timer.start()

        self._now_ms = 0
        my_last = -10000
        self._last_touch_time_ms = my_last
        self._pick_state = "idle"
        self._pick_t = 0
        if not self._pick_timer.isActive():
            sh, el = self._pose_home()
            self._set_arm(sh, el)
            self._pick_timer.start()

        self._selected_active = False
        self._selected_expected = None
        self._selected_source = None

        # Clear any stale intended-colors memory
        self._intended_colors.clear()

        # Start the first batch (random color that needs boxes)
        self._ensure_batch()

        self._alarm_active = False
        try:
            self.audio.cancel_alarm_delay()
            self.audio.stop_alarm()
        except Exception:
            pass

        try:
            get_logger().log_user(
                "Packaging", "control", "start",
                f"pace={pace},error_rate={error_rate},limit={limit},bin_count={len(slot_order)}"
            )
        except Exception:
            pass

    def complete(self):
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
        self._selected_source = None

        self._batch_active = False
        self._batch_remaining = 0
        self._batch_color = None

        if hasattr(self, "conveyor") and hasattr(self.conveyor, "_boxes"):
            self.conveyor._boxes.clear()
        if hasattr(self, "conveyor") and hasattr(self.conveyor, "_box_colors"):
            self.conveyor._box_colors.clear()
        # clear intended list as well
        self._intended_colors.clear()

        self.conveyor.update()

        # Reset box counts to 0 on the labels
        for rec in self._containers:
            rec["count"] = 0
            self._update_label(rec)

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
        self._held_intended_color = None
        self.arm.update()

        # Reset correction counters
        self._total_corrections = 0
        self._correct_corrections = 0

        # reset counts/caps for visible containers
        for rec in self._containers:
            rec["widget"].border = rec.get("orig_border", rec["widget"].border)
            if rec.get("badge"):
                rec["badge"].hide()
            self._update_label(rec)

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

        self._selected_active = False
        self._selected_expected = None
        self._selected_source = None

        self._batch_active = False
        self._batch_remaining = 0
        self._batch_color = None

        if hasattr(self, "conveyor") and hasattr(self.conveyor, "_boxes"):
            self.conveyor._boxes.clear()
        if hasattr(self, "conveyor") and hasattr(self.conveyor, "_box_colors"):
            self.conveyor._box_colors.clear()
        # clear intended list as well
        self._intended_colors.clear()

        self.conveyor.update()

        # Reset box counts to 0 on the labels
        for rec in self._containers:
            rec["count"] = 0
            self._update_label(rec)

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
        self._held_intended_color = None
        self.arm.update()

        try:
            get_logger().log_user("Packaging", "control", "stop", "stopped by user")
        except Exception:
            pass

        if hasattr(self, "metrics_manager"):
            self.metrics_manager.reset_metrics()

        # Reset correction counters
        self._total_corrections = 0
        self._correct_corrections = 0

        # reset counts/caps for visible containers
        for rec in self._containers:
            rec["widget"].border = rec.get("orig_border", rec["widget"].border)
            if rec.get("badge"):
                rec["badge"].hide()
            self._update_label(rec)

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

    # Sound
    def play_sound(self, sound_name):
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
