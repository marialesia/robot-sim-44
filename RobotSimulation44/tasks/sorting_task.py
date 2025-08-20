# tasks/sorting_task.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer
from .base_task import BaseTask, StorageContainerWidget

class SortingTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Sorting")

        # ---- Robot arm visuals ----
        self.arm.shoulder_angle = -95
        self.arm.elbow_angle = -5
        self.arm.c_arm = QColor("#3f88ff")
        self.arm.c_arm_dark = QColor("#2f6cc9")

        # ---- Containers: Blue (middle) uses the built-in self.container ----
        # Blue (middle)
        self.container.border = QColor("#2b4a91")
        self.container.fill_top = QColor("#dbe8ff")
        self.container.fill_bottom = QColor("#c7daff")
        self.container.rib = QColor(43, 74, 145, 120)

        # Red (left)
        self.container_left = StorageContainerWidget()
        self.container_left.border = QColor("#8c1f15")
        self.container_left.fill_top = QColor("#ffd6d1")
        self.container_left.fill_bottom = QColor("#ffb8b0")
        self.container_left.rib = QColor(140, 31, 21, 120)

        # Green (right)
        self.container_right = StorageContainerWidget()
        self.container_right.border = QColor("#1f7a3a")
        self.container_right.fill_top = QColor("#d9f7e6")
        self.container_right.fill_bottom = QColor("#bff0d3")
        self.container_right.rib = QColor(31, 122, 58, 120)

        # ---- Layout: Conveyor (row 0), Arm (row 1, spanning 3 cols),
        #              Three containers (row 3: red, blue, green) ----
        self.set_positions(
            conveyor=dict(row=0, col=0, colSpan=3, align=Qt.AlignTop),
            arm=dict(row=0, col=0, colSpan=3, align=Qt.AlignHCenter | Qt.AlignBottom),
            container=dict(row=3, col=1, align=Qt.AlignHCenter | Qt.AlignTop),  # Blue in the middle
            col_stretch=[1, 1, 1],
            row_stretch=[0, 0, 1],
            spacing=18
        )

        # Add Red (left) and Green (right) on the same row under the arm
        self.grid.addWidget(self.container_left,  3, 0, 1, 1, Qt.AlignLeft  | Qt.AlignTop)
        self.grid.addWidget(self.container_right, 3, 2, 1, 1, Qt.AlignRight | Qt.AlignTop)

        # Repaint
        self.arm.update()
        self.conveyor.update()
        self.container_left.update()
        self.container.update()
        self.container_right.update()

        # ===== Existing box spawner (created but not started until Start) =====
        self._box_timer = QTimer(self)
        self._box_timer.timeout.connect(self.conveyor.spawn_box)

        # ===== Arm "pick" animation (timer-driven; no base_task changes) =====
        self._pick_timer = QTimer(self)
        self._pick_timer.setInterval(16)  # ~60 FPS
        self._pick_timer.timeout.connect(self._tick_pick)

        # FSM state
        self._pick_state = "idle"
        self._pick_t = 0
        self._pick_duration = 0
        self._pick_from = (self.arm.shoulder_angle, self.arm.elbow_angle)
        self._pick_to = (self.arm.shoulder_angle, self.arm.elbow_angle)

    # ===== Called by your existing GUI =====
    def start(self):
        # belt motion
        self.conveyor.setBeltSpeed(120)   # left -> right
        self.conveyor.enable_motion(True)

        # start spawning boxes periodically
        if not self._box_timer.isActive():
            self._box_timer.start(800)    # one box every 0.8s

        # start arm pick cycle
        if not self._pick_timer.isActive():
            # reset to home and begin cycle
            sh, el = self._pose_home()
            self._set_arm(sh, el)
            self._pick_state = "idle"
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

    # ---------- Arm pick cycle (approach -> descend -> hold -> lift -> return) ----------
    def _pose_home(self):
        # your initial pose
        return (-95.0, -5.0)

    def _pose_prep(self):
        # slight move over belt before descending
        return (-92.0, -12.0)

    def _pose_pick(self):
        # descend to "grip" height over belt
        return (-100.0, -30.0)

    def _pose_lift(self):
        # lift a bit as if carrying
        return (-93.0, -10.0)

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
        # kick off a cycle if idle
        if self._pick_state == "idle":
            self._pick_state = "to_prep"
            self._start_seg(self._pose_prep(), 400)
            return

        # advance interpolation
        self._pick_t += self._pick_timer.interval()
        t = min(1.0, self._pick_t / float(self._pick_duration))
        s0, e0 = self._pick_from
        s1, e1 = self._pick_to
        s = s0 + (s1 - s0) * t
        e = e0 + (e1 - e0) * t
        self._set_arm(s, e)

        # segment complete -> next state
        if t >= 1.0:
            if self._pick_state == "to_prep":
                self._pick_state = "descend"
                self._start_seg(self._pose_pick(), 350)
            elif self._pick_state == "descend":
                self._pick_state = "hold"
                # hold at pick pose briefly (from == to keeps arm still)
                self._start_seg(self._pose_pick(), 220)
            elif self._pick_state == "hold":
                self._pick_state = "lift"
                self._start_seg(self._pose_lift(), 350)
            elif self._pick_state == "lift":
                self._pick_state = "return"
                self._start_seg(self._pose_home(), 500)
            elif self._pick_state == "return":
                # brief idle before next pick
                self._pick_state = "idle_pause"
                self._start_seg(self._pose_home(), 300)
            elif self._pick_state == "idle_pause":
                self._pick_state = "idle"
