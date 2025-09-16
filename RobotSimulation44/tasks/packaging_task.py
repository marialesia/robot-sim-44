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
            c = random.choice(["red", "blue", "green"])
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
            else:  # green
                w.border = QColor("#1f7a3a")
                w.fill_top = QColor("#d9f7e6")
                w.fill_bottom = QColor("#bff0d3")
                w.rib = QColor(31, 122, 58, 110)

        _style_container(self.container)  # use BaseTask's default as the first

        # ---- Layout: keep conveyor + arm; replace single container with a row of 4 ----
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

        # --- Row holding 4 containers (leftmost is the active packing target) ---
        self._row = QWidget()
        self._row_layout = QHBoxLayout(self._row)
        self._row_layout.setContentsMargins(0, 0, 0, 0)
        self._row_layout.setSpacing(12)

        # Build container records list
        self._containers = []

        def _make_badge(parent_w):
            b = QLabel("!", parent_w)
            b.setFixedSize(20, 20)
            b.setAlignment(Qt.AlignCenter)
            b.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            b.hide()
            return b

        def _new_container(widget=None):
            w = widget or StorageContainerWidget()
            _style_container(w)
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
            self._position_badge(rec)
            return rec

        first_rec = _new_container(self.container)
        self._containers.append(first_rec)
        self._row_layout.addWidget(first_rec["widget"])

        for _ in range(3):
            rec = _new_container()
            self._containers.append(rec)
            self._row_layout.addWidget(rec["widget"])

        self.grid.addWidget(self._row, 1, 0, 1, 2, Qt.AlignRight | Qt.AlignBottom)

        # ===== Spawner / worker =====
        self.worker = None
        self._box_timer = QTimer(self)

        # ===== Minimal arm 'pick-present-return' cycle =====
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

        self._flash_on = False
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(350)
        self._flash_timer.timeout.connect(self._on_flash_tick)

        self.arm.update()
        self.conveyor.update()
        for rec in self._containers:
            rec["widget"].update()
            self._position_label(rec)

    # ---------- Helpers ----------
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
        y = 2
        b.move(max(0, x), max(0, y))

    def _update_label(self, rec):
        rec["label"].setText(f"{rec['count']}/{rec['capacity']}")
        self._position_label(rec)

    # ---------- Error visuals ----------
    def _apply_error_visuals(self):
        for rec in self._containers:
            w = rec["widget"]
            badge = rec.get("badge")
            if rec.get("fixed"):
                if badge:
                    badge.hide()
                w.border = QColor("#2ecc71")
                w.update()
                continue

            if rec.get("error"):
                w.border = QColor("#e74c3c") if self._flash_on else rec.get("orig_border", w.border)
                w.update()
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
                if badge:
                    badge.hide()
                w.border = rec.get("orig_border", w.border)
                w.update()

    def _on_flash_tick(self):
        self._flash_on = not self._flash_on
        self._apply_error_visuals()

    # ---------- Worker callbacks ----------
    def _on_worker_fade(self, mode, at_count, capacity, secs):
        self._should_fade_current = True
        if self._containers:
            rec = self._containers[0]
            rec["error"] = (mode in ("underfill", "overfill"))
            rec["fixed"] = False
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
        if not self._containers:
            return
        active = self._containers[0]
        if active["fading"]:
            return
        active["count"] += 1
        self._update_label(active)
        msg = f"Packaging Task: Packed {active['count']}/{active['capacity']}"
        print(msg)
        try:
            get_logger().log_robot("Packaging", f"pack {active['count']}/{active['capacity']}")
        except Exception:
            pass
        if self.worker:
            self.worker.record_pack()
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
            def _finished():
                w.hide()
                self._row_layout.removeWidget(w)
                try:
                    self._containers.pop(0)
                except Exception:
                    pass
                if self.worker and self.worker.isRunning():
                    new_cap = PackagingWorker.pick_capacity()
                    new_rec = self._create_new_container(initial_cap=new_cap)
                else:
                    new_rec = self._create_new_container(initial_cap=None)
                self._containers.append(new_rec)
                self._row_layout.addWidget(new_rec["widget"])
                for rec2 in self._containers:
                    self._position_label(rec2)
                    self._position_badge(rec2)
                if self.worker and self._containers:
                    leftmost = self._containers[0]
                    self.worker.begin_container(leftmost["capacity"])
                    try:
                        get_logger().log_robot(
                            "Packaging",
                            f"begin_container capacity={leftmost['capacity']}"
                        )
                    except Exception:
                        pass
                self._apply_error_visuals()
                try:
                    get_logger().log_robot(
                        "Packaging",
                        f"shift_completed new_right_capacity={new_rec['capacity']}"
                    )
                except Exception:
                    pass
            try:
                anim.finished.disconnect()
            except Exception:
                pass
            anim.finished.connect(_finished)
            anim.start()

    def _create_new_container(self, initial_cap=None):
        w = StorageContainerWidget()
        c = random.choice(["red", "blue", "green"])
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
        else:  # green
            w.border = QColor("#1f7a3a")
            w.fill_top = QColor("#d9f7e6")
            w.fill_bottom = QColor("#bff0d3")
            w.rib = QColor(31, 122, 58, 110)

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
    def spawn_box_from_worker(self, box_data):
        color = box_data.get("color") or random.choice(["red", "blue", "green"])
        try:
            get_logger().log_robot("Packaging", f"spawn_box color={color}")
        except Exception:
            pass
        self.conveyor.spawn_box(color=color)

    # ---------- Lifecycle ----------
    def start(self, pace=None, error_rate=None):
        self.conveyor.setBeltSpeed(120)
        self.conveyor.enable_motion(True)

        if self._box_timer.isActive():
            self._box_timer.stop()

        if not self.worker or not self.worker.isRunning():
            self.worker = PackagingWorker(pace=pace, error_rate=error_rate)
            self.worker.box_spawned.connect(self.spawn_box_from_worker)
            self.worker.metrics_ready.connect(self._on_metrics)
            self.worker.container_should_fade.connect(self._on_worker_fade)
            self.worker.metrics_live.connect(self._on_metrics_live)
            self.worker.start()

        for rec in self._containers:
            rec["count"] = 0
            rec["capacity"] = PackagingWorker.pick_capacity()
            rec["error"] = False
            rec["fixed"] = False
            rec["anim"].stop()
            rec["effect"].setOpacity(1.0)
            rec["widget"].show()
            rec["fading"] = False
            rec["widget"].border = rec.get("orig_border", rec["widget"].border)
            if rec.get("badge"):
                rec["badge"].hide()
            self._update_label(rec)

        if self._containers:
            leftmost = self._containers[0]
            self.worker.begin_container(leftmost["capacity"])
            try:
                get_logger().log_robot("Packaging", f"begin_container capacity={leftmost['capacity']}")
            except Exception:
                pass
        self._should_fade_current = False

        if not self._flash_timer.isActive():
            self._flash_timer.start()

        self._now_ms = 0
        self._last_touch_time_ms = -10000
        self._pick_state = "idle"
        self._pick_t = 0
        if not self._pick_timer.isActive():
            sh, el = self._pose_home()
            self._set_arm(sh, el)
            self._pick_timer.start()

        try:
            get_logger().log_user("Packaging", "control", "start", f"pace={pace},error_rate={error_rate}")
        except Exception:
            pass

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

        sh, el = self._pose_home()
        self._set_arm(sh, el)
        self.arm.held_box_visible = False
        self.arm.update()

        try:
            get_logger().log_user("Packaging", "control", "stop", "stopped by user")
        except Exception:
            pass

    def _on_metrics(self, metrics):
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

    # ---------- Helpers ----------
    def _grip_x(self):
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
        cutoff_x = detect_x + self._despawn_offset_px

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
        cols = getattr(self.conveyor, "_box_colors", None)
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
        if not rec.get("error"):
            try:
                get_logger().log_user("Packaging", "container", "click", "no error to fix")
            except Exception:
                pass
            return

        cap = rec.get("capacity", 0)
        if cap > 0:
            rec["count"] = cap
            self._update_label(rec)

        rec["error"] = False
        rec["fixed"] = True
        self._mark_fixed_visual(rec)
        if rec.get("badge"):
            rec["badge"].hide()

        try:
            get_logger().log_user("Packaging", "container", "smart_fix", f"set to {cap}/{cap}")
        except Exception:
            pass

        self._apply_error_visuals()

    def _mark_fixed_visual(self, rec):
        w = rec["widget"]
        w.border = QColor("#2ecc71")
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
                    self._smart_fix(rec)
                    return True

        return super().eventFilter(obj, event)

    def _on_metrics_live(self, metrics):
        if hasattr(self, "metrics_manager") and self.metrics_manager:
            self.metrics_manager.update_metrics(metrics)
        else:
            print("Live metrics:", metrics)
