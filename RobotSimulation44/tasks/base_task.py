# tasks/base_task.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy, QFrame, QGridLayout
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer, pyqtProperty


# --- Conveyor ---------------------------------------------------------------

class ConveyorBeltWidget(QWidget):
    """
    Realistic conveyor with rollers, belt gradient, treads, and rails.
    Now includes a lightweight, non-blocking tread animation + small red boxes.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # fill horizontally

        # Per-instance palette
        self.roller_pen  = QColor(40, 40, 40)
        self.roller_fill = QColor(70, 70, 72)
        self.belt_top    = QColor(45, 45, 47)
        self.belt_mid    = QColor(30, 30, 32)
        self.belt_bot    = QColor(50, 50, 52)
        self.rail        = QColor(120, 120, 122)
        self.tread       = QColor(90, 90, 92, 180)

        # --- animation state ---
        self._belt_speed = 0.0      # pixels/second; + = move RIGHT
        self._tread_phase = 0.0     # accumulates over time
        self._belt_timer = QTimer(self)
        self._belt_timer.timeout.connect(self._tick_belt)

        # --- moving boxes ---
        self._boxes = []            # list of x positions (float)
        self._box_inset = 12        # keep boxes inside belt edges
        self._box_size = 14         # square box size in px
        self._box_color = QColor(200, 40, 40)

    # Public API --------------------------------------------------------------
    def enable_motion(self, enable: bool):
        """Start/stop the belt tread & box animation timer."""
        if enable and not self._belt_timer.isActive():
            self._belt_timer.start(16)  # ~60 FPS
        elif not enable and self._belt_timer.isActive():
            self._belt_timer.stop()

    @pyqtProperty(float)
    def beltSpeed(self):
        return self._belt_speed

    def setBeltSpeed(self, v: float):
        self._belt_speed = float(v)

    def spawn_box(self):
        """Spawn a small red box at the left edge of the belt."""
        # Place just inside the left margin + inset
        x0 = 12 + self._box_inset
        self._boxes.append(float(x0))
        self.update()

    # Internals ---------------------------------------------------------------
    def _tick_belt(self):
        dt = 0.016
        self._tread_phase = (self._tread_phase + self._belt_speed * dt) % 1000.0

        # advance boxes
        if self._boxes:
            dx = self._belt_speed * dt
            w = self.width()
            right_limit = w - 12 - self._box_inset - self._box_size
            next_boxes = []
            for x in self._boxes:
                x2 = x + dx
                if x2 <= right_limit:
                    next_boxes.append(x2)
            self._boxes = next_boxes

        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin = 12

        # End rollers
        roller_r = max(16, int(h*0.18))
        p.setPen(QPen(self.roller_pen, 2))
        p.setBrush(QBrush(self.roller_fill))
        p.drawEllipse(QPointF(margin + roller_r, h/2), roller_r, roller_r)
        p.drawEllipse(QPointF(w - margin - roller_r, h/2), roller_r, roller_r)

        # Belt body
        belt_height = max(28, int(h*0.38))
        belt_top = (h - belt_height) / 2
        grad = QLinearGradient(0, belt_top, 0, belt_top + belt_height)
        grad.setColorAt(0.0, self.belt_top)
        grad.setColorAt(0.5, self.belt_mid)
        grad.setColorAt(1.0, self.belt_bot)
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(20,20,20), 2))
        p.drawRoundedRect(QRectF(margin, belt_top, w - 2*margin, belt_height), 8, 8)

        # Treads (animated)
        p.setPen(QPen(self.tread, 1.2))
        step = 12
        phase = self._tread_phase % step
        # Inset so lines don't hang over the rounded ends
        start_x = int(margin + 16 + phase - step)  # 16 = 6 + slant(10)
        for x in range(start_x, int(w - margin), step):
            p.drawLine(x, belt_top + 4, x - 10, belt_top + belt_height - 4)

        # Boxes (draw on belt, under rails)
        if self._boxes:
            p.setPen(QPen(QColor(60, 0, 0), 1))
            p.setBrush(QBrush(self._box_color))
            box_h = min(self._box_size, max(8, belt_height - 8))
            box_w = box_h
            y = belt_top + (belt_height - box_h)/2
            for x in self._boxes:
                p.drawRoundedRect(QRectF(x, y, box_w, box_h), 3, 3)

        # Rails + bolts (on top)
        rail_pen = QPen(self.rail, 2); p.setPen(rail_pen)
        p.setBrush(Qt.NoBrush)
        p.drawLine(margin + 4, belt_top - 6, w - margin - 4, belt_top - 6)
        p.drawLine(margin + 4, belt_top + belt_height + 6, w - margin - 4, belt_top + belt_height + 6)
        p.setBrush(QBrush(QColor(160,160,165))); p.setPen(Qt.NoPen)
        bolt_step = 28
        for x in range(int(margin + 10), int(w - margin - 10), bolt_step):
            p.drawEllipse(QPointF(x, belt_top - 6), 1.8, 1.8)
            p.drawEllipse(QPointF(x, belt_top + belt_height + 6), 1.8, 1.8)




# --- Robot Arm --------------------------------------------------------------

class RobotArmWidget(QWidget):
    """
    Stylized 3-DOF industrial arm (base, upper arm, forearm, gripper),
    facing away (upward). Per-instance pose/colours so each task can override.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Pose (can be overridden per task)
        self.shoulder_angle = -90.0
        self.elbow_angle = -12.0

        # Palette (can be overridden per task)
        self.c_arm = QColor(70, 120, 180)
        self.c_arm_dark = QColor(50, 90, 135)
        self.c_joint = QColor(230, 230, 235)
        self.c_base = QColor(60, 60, 65)

    def _joint(self, p, r_outer=16, r_inner=8):
        p.setPen(QPen(QColor(40, 40, 45), 2))
        p.setBrush(QBrush(self.c_joint)); p.drawEllipse(QPointF(0, 0), r_outer, r_outer)
        p.setBrush(QBrush(QColor(190, 190, 195))); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(0, 0), r_inner, r_inner)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height(); m = 10

        # Base & tower
        base_h = max(12, int(h * 0.08))
        base_w = max(120, int(w * 0.38))
        base_rect = QRectF((w - base_w) / 2.0, h - base_h - 6, base_w, base_h)
        tower_h = max(40, int(h * 0.35))
        tower_w = max(28, int(base_w * 0.22))
        tower_rect = QRectF(base_rect.center().x() - tower_w / 2.0,
                            h - base_h - tower_h, tower_w, tower_h)
        p.setBrush(QBrush(self.c_base))
        p.setPen(QPen(QColor(30, 30, 32), 2))
        p.drawRoundedRect(base_rect, base_h/2.5, base_h/2.5)
        p.setBrush(QBrush(self.c_base.darker(110)))
        p.drawRoundedRect(tower_rect, 6, 6)

        # Kinematics
        origin = QPointF(tower_rect.center().x(), tower_rect.top())
        avail_up = max(30.0, origin.y() - m)
        arm_t = max(8.0, min(w, h) * 0.06)
        L1, L2 = max(30.0, avail_up * 0.55), max(24.0, avail_up * 0.35)
        cap_r = arm_t * 0.55

        p.save(); p.translate(origin)
        self._joint(p, r_outer=max(12.0, arm_t*0.9), r_inner=max(5.0, arm_t*0.45))

        p.save()
        p.rotate(self.shoulder_angle)
        p.setBrush(QBrush(self.c_arm)); p.setPen(QPen(self.c_arm_dark, 2))
        p.drawRoundedRect(QRectF(0, -arm_t/2, L1, arm_t), arm_t/2.5, arm_t/2.5)

        p.translate(L1, 0); self._joint(p, r_outer=max(10.0, arm_t*0.8), r_inner=max(4.0, arm_t*0.4))
        p.rotate(self.elbow_angle)
        p.setBrush(QBrush(self.c_arm)); p.setPen(QPen(self.c_arm_dark, 2))
        p.drawRoundedRect(QRectF(0, -arm_t/2 + 1, L2, arm_t - 2), arm_t/2.7, arm_t/2.7)

        p.translate(L2, 0); self._joint(p, r_outer=max(8.0, arm_t*0.65), r_inner=max(3.0, arm_t*0.33))
        p.setPen(QPen(self.c_arm_dark, 2)); p.setBrush(QBrush(self.c_arm))
        fL, fW = max(16.0, arm_t*0.9), max(4.0, arm_t*0.35)
        p.save(); p.rotate(18);  p.drawRoundedRect(QRectF(0, -fW/2, fL, fW), fW/1.6, fW/1.6); p.restore()
        p.save(); p.rotate(-18); p.drawRoundedRect(QRectF(0, -fW/2, fL, fW), fW/1.6, fW/1.6); p.restore()

        p.setBrush(QBrush(self.c_joint)); p.setPen(QPen(QColor(80, 82, 90), 1.5))
        p.drawEllipse(QPointF(0, 0), cap_r, cap_r)
        p.restore(); p.restore()


# --- Storage Container -------------------------------------------------------

class StorageContainerWidget(QWidget):
    """
    Simple container box: rounded rect + subtle lid seam + a few ribs.
    Per-instance palette so each task can override.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Palette (override per task)
        self.border = QColor("#2a7a4b")
        self.fill_top = QColor("#d9f7e6")
        self.fill_bottom = QColor("#bff0d3")
        self.rib = QColor(42, 122, 75, 120)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m = max(10, int(min(w, h) * 0.08))
        r = QRectF(m, m, w - 2*m, h - 2*m)
        radius = max(8.0, min(w, h) * 0.06)

        grad = QLinearGradient(r.left(), r.top(), r.left(), r.bottom())
        grad.setColorAt(0.0, self.fill_top); grad.setColorAt(1.0, self.fill_bottom)
        p.setBrush(QBrush(grad)); p.setPen(QPen(self.border, 2))
        p.drawRoundedRect(r, radius, radius)

        seam_y = r.top() + r.height() * 0.22
        p.setPen(QPen(self.border.darker(115), 1.2))
        p.drawLine(r.left() + 8, seam_y, r.right() - 8, seam_y)

        p.setPen(QPen(self.rib, 2))
        rib_top = seam_y + r.height() * 0.06; rib_bottom = r.bottom() - 8
        for t in (0.30, 0.50, 0.70):
            x = r.left() + r.width() * t
            p.drawLine(x, rib_top, x, rib_bottom)


# --- Scene container ---------------------------------------------------------

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy, QFrame, QGridLayout
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient
from PyQt5.QtCore import Qt, QPointF, QRectF

class BaseTask(QWidget):
    """
    One task’s scene with three widgets (conveyor, arm, container).
    Uses a QGridLayout so subclasses can reposition each widget per task.

    Exposes:
      - self.scene (QFrame)
      - self.grid  (QGridLayout)
      - self.conveyor, self.arm, self.container
      - set_positions(conveyor=..., arm=..., container=..., ...)
    """
    def __init__(self, task_name="Task"):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        title = QLabel(f"{task_name}")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:16px; font-weight:bold; padding:4px 0;")
        outer.addWidget(title)

        # Scene frame for visual separation (unchanged look)
        self.scene = QFrame()
        self.scene.setObjectName("warehouseScene")
        self.scene.setStyleSheet(
            "#warehouseScene { "
            "border: 2px solid #444; border-radius: 8px; "
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f7f7f9, stop:1 #e6e6ea); }"
        )
        
        self.scene.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scene.setMinimumSize(600, 400)
        self.scene.setMaximumSize(1200, 400) 
        outer.addWidget(self.scene)

        # ---- Grid layout for flexible placement ----
        self.grid = QGridLayout(self.scene)
        self.grid.setContentsMargins(20, 20, 20, 20)
        self.grid.setSpacing(18)

        # Widgets (same instances exposed to subclasses)
        self.conveyor = ConveyorBeltWidget()
        self.conveyor.setMinimumHeight(120)
        self.conveyor.setMaximumHeight(160)
        self.conveyor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.arm = RobotArmWidget()
        self.container = StorageContainerWidget()

        # Default placement (same as before visually)
        self.grid.addWidget(self.conveyor, 0, 0, 1, 2, Qt.AlignTop)
        self.grid.addWidget(self.arm,      1, 0, 1, 1, Qt.AlignLeft   | Qt.AlignBottom)
        self.grid.addWidget(self.container,1, 1, 1, 1, Qt.AlignRight  | Qt.AlignBottom)

        # Stretch so columns share width / bottom row takes slack
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.grid.setRowStretch(0, 0)
        self.grid.setRowStretch(1, 1)

    # --------- Per-task placement API  ----------
    def set_positions(
        self,
        conveyor=None,   # dict: {row, col, rowSpan=1, colSpan=1, align=Qt.Align...}
        arm=None,        # dict: ^
        container=None,  # dict: ^
        row_stretch=None,  # list of ints
        col_stretch=None,  # list of ints
        spacing=None,      # int
        margins=None       # tuple(l,t,r,b)
    ):
        def _place(widget, spec):
            if not spec:
                return
            try:
                self.grid.removeWidget(widget)
            except Exception:
                pass
            r  = spec.get("row", 0)
            c  = spec.get("col", 0)
            rs = spec.get("rowSpan", 1)
            cs = spec.get("colSpan", 1)
            al = spec.get("align", Qt.AlignCenter)
            self.grid.addWidget(widget, r, c, rs, cs, al)
            widget.updateGeometry()

        _place(self.conveyor, conveyor)
        _place(self.arm, arm)
        _place(self.container, container)

        if isinstance(col_stretch, (list, tuple)):
            for i, s in enumerate(col_stretch):
                self.grid.setColumnStretch(i, int(s))
        if isinstance(row_stretch, (list, tuple)):
            for i, s in enumerate(row_stretch):
                self.grid.setRowStretch(i, int(s))
        if isinstance(spacing, int):
            self.grid.setSpacing(spacing)
        if isinstance(margins, (list, tuple)) and len(margins) == 4:
            l, t, r, b = margins
            self.grid.setContentsMargins(int(l), int(t), int(r), int(b))

