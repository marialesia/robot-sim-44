# tasks/base_task.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient, QPainterPath
from PyQt5.QtCore import Qt, QPointF, QRectF

# --- Conveyor ---------------------------------------------------------------

class ConveyorBeltWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # fill horizontally

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin = 12

        # End rollers
        roller_r = max(16, int(h*0.18))
        p.setPen(QPen(QColor(40, 40, 40), 2))
        p.setBrush(QBrush(QColor(70, 70, 72)))
        p.drawEllipse(QPointF(margin + roller_r, h/2), roller_r, roller_r)
        p.drawEllipse(QPointF(w - margin - roller_r, h/2), roller_r, roller_r)

        # Belt
        belt_height = max(28, int(h*0.38))
        belt_top = (h - belt_height) / 2
        grad = QLinearGradient(0, belt_top, 0, belt_top + belt_height)
        grad.setColorAt(0.0, QColor(45,45,47))
        grad.setColorAt(0.5, QColor(30,30,32))
        grad.setColorAt(1.0, QColor(50,50,52))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(20,20,20), 2))
        p.drawRoundedRect(QRectF(margin, belt_top, w - 2*margin, belt_height), 8, 8)

        # Tread
        p.setPen(QPen(QColor(90, 90, 92, 180), 1.2))
        step = 12
        for x in range(int(margin + 6), int(w - margin), step):
            p.drawLine(x, belt_top + 4, x - 10, belt_top + belt_height - 4)

        # Rails + bolts
        rail_pen = QPen(QColor(120,120,122), 2); p.setPen(rail_pen)
        p.drawLine(margin + 4, belt_top - 6, w - margin - 4, belt_top - 6)
        p.drawLine(margin + 4, belt_top + belt_height + 6, w - margin - 4, belt_top + belt_height + 6)
        p.setBrush(QBrush(QColor(160,160,165))); p.setPen(Qt.NoPen)
        bolt_step = 28
        for x in range(int(margin + 10), int(w - margin - 10), bolt_step):
            p.drawEllipse(QPointF(x, belt_top - 6), 1.8, 1.8)
            p.drawEllipse(QPointF(x, belt_top + belt_height + 6), 1.8, 1.8)


class RobotArmWidget(QWidget):
    """
    Stylized 3-DOF industrial arm (base, upper arm, forearm, gripper), facing away (upward).
    Scales proportions to fit the widget so nothing is clipped.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Pose (facing away/up). Tweak these if you want a different tilt.
        self.shoulder_angle = -90   # up
        self.elbow_angle = -12      # slight bend

        # Colors
        self.c_arm = QColor(70, 120, 180)          # steel blue
        self.c_arm_dark = QColor(50, 90, 135)
        self.c_joint = QColor(230, 230, 235)
        self.c_base = QColor(60, 60, 65)

    def _draw_joint(self, p, r_outer=16, r_inner=8):
        p.setPen(QPen(QColor(40, 40, 45), 2))
        p.setBrush(QBrush(self.c_joint))
        p.drawEllipse(QPointF(0, 0), r_outer, r_outer)
        p.setBrush(QBrush(QColor(190, 190, 195)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(0, 0), r_inner, r_inner)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m = 10  # top margin so the arm has headroom

        # ----- Base & tower (proportional to widget size) --------------------
        base_h = max(12, int(h * 0.08))
        base_rect = QRectF(10, h - base_h - 6, w - 20, base_h)

        tower_h = max(40, int(h * 0.35))
        tower_w = max(28, int(w * 0.16))
        tower_x = max(20, int(w * 0.10))
        tower_rect = QRectF(tower_x, h - base_h - tower_h, tower_w, tower_h)

        p.setBrush(QBrush(self.c_base))
        p.setPen(QPen(QColor(30, 30, 32), 2))
        p.drawRoundedRect(base_rect, 6, 6)

        p.setBrush(QBrush(self.c_base.darker(110)))
        p.setPen(QPen(QColor(30, 30, 32), 2))
        p.drawRoundedRect(tower_rect, 6, 6)

        # ----- Arm kinematics (fit to available vertical space) --------------
        origin = QPointF(tower_rect.center().x(), tower_rect.top())
        avail_up = max(30.0, origin.y() - m)  # vertical space above the shoulder
        arm_thick = max(8.0, min(w, h) * 0.06)

        # Split available space between segments so the hand stays inside
        upper_len = max(30.0, avail_up * 0.55)
        fore_len  = max(24.0, avail_up * 0.35)
        cap_r     = arm_thick * 0.55

        p.save()
        p.translate(origin)

        # Shoulder joint
        self._draw_joint(p, r_outer=max(12.0, arm_thick*0.9), r_inner=max(5.0, arm_thick*0.45))

        # Upper arm (rotated upward)
        p.save()
        p.rotate(self.shoulder_angle)
        p.setBrush(QBrush(self.c_arm))
        p.setPen(QPen(self.c_arm_dark, 2))
        p.drawRoundedRect(QRectF(0, -arm_thick/2, upper_len, arm_thick),
                          arm_thick/2.5, arm_thick/2.5)

        # Elbow joint
        p.translate(upper_len, 0)
        self._draw_joint(p, r_outer=max(10.0, arm_thick*0.8), r_inner=max(4.0, arm_thick*0.4))

        # Forearm
        p.rotate(self.elbow_angle)
        p.setBrush(QBrush(self.c_arm))
        p.setPen(QPen(self.c_arm_dark, 2))
        p.drawRoundedRect(QRectF(0, -arm_thick/2 + 1, fore_len, arm_thick - 2),
                          arm_thick/2.7, arm_thick/2.7)

        # Wrist + gripper
        p.translate(fore_len, 0)
        self._draw_joint(p, r_outer=max(8.0, arm_thick*0.65), r_inner=max(3.0, arm_thick*0.33))

        p.setPen(QPen(self.c_arm_dark, 2))
        p.setBrush(QBrush(self.c_arm))
        finger_len, finger_w = max(16.0, arm_thick*0.9), max(4.0, arm_thick*0.35)

        p.save()
        p.rotate(18)
        p.drawRoundedRect(QRectF(0, -finger_w/2, finger_len, finger_w), finger_w/1.6, finger_w/1.6)
        p.restore()

        p.save()
        p.rotate(-18)
        p.drawRoundedRect(QRectF(0, -finger_w/2, finger_len, finger_w), finger_w/1.6, finger_w/1.6)
        p.restore()

        # End-effector cap (visual)
        p.setBrush(QBrush(self.c_joint))
        p.setPen(QPen(QColor(80, 82, 90), 1.5))
        p.drawEllipse(QPointF(0, 0), cap_r, cap_r)

        p.restore()   # end shoulder/arm context
        p.restore()   # end translate(origin)


# --- Storage Container -------------------------------------------------------

class StorageContainerWidget(QWidget):
    """
    Simple container box: rounded rect + subtle lid seam and a few ribs.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Palette (easy to tweak)
        self.border = QColor("#2a7a4b")
        self.fill_top = QColor("#d9f7e6")
        self.fill_bottom = QColor("#bff0d3")
        self.rib = QColor(42, 122, 75, 120)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        m = max(10, int(min(w, h) * 0.08))     # margin
        r = QRectF(m, m, w - 2*m, h - 2*m)
        radius = max(8.0, min(w, h) * 0.06)

        # Fill (subtle vertical gradient)
        grad = QLinearGradient(r.left(), r.top(), r.left(), r.bottom())
        grad.setColorAt(0.0, self.fill_top)
        grad.setColorAt(1.0, self.fill_bottom)
        p.setBrush(QBrush(grad))
        p.setPen(QPen(self.border, 2))
        p.drawRoundedRect(r, radius, radius)

        # Lid seam (light horizontal line near top)
        seam_y = r.top() + r.height() * 0.22
        p.setPen(QPen(self.border.darker(115), 1.2))
        p.drawLine(r.left() + 8, seam_y, r.right() - 8, seam_y)

        # A few vertical ribs (very subtle)
        p.setPen(QPen(self.rib, 2))
        rib_top = seam_y + r.height() * 0.06
        rib_bottom = r.bottom() - 8
        for t in (0.30, 0.50, 0.70):
            x = r.left() + r.width() * t
            p.drawLine(x, rib_top, x, rib_bottom)





# --- Scene container ---------------------------------------------------------

class BaseTask(QWidget):
    def __init__(self, task_name="Task"):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_label = QLabel(f"{task_name} Workspace")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size:18px; font-weight:bold; padding:6px 0;")
        layout.addWidget(title_label)

        scene = QWidget()
        scene.setObjectName("warehouseScene")
        scene.setStyleSheet(
            "#warehouseScene { "
            "border: 2px solid #444; border-radius: 8px; "
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f7f7f9, stop:1 #e6e6ea); }"
        )
        scene.setFixedHeight(420)

        # Top-level: vertical → conveyor on top (full width), arm/container below
        scene_v = QVBoxLayout(scene)
        scene_v.setContentsMargins(20, 20, 20, 20)
        scene_v.setSpacing(18)

        conveyor = ConveyorBeltWidget()
        conveyor.setMinimumHeight(120)
        conveyor.setMaximumHeight(160)
        conveyor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        scene_v.addWidget(conveyor)  # spans all the way left ↔ right

        # Bottom row: arm (left, bottom-aligned) … space … container (right)
        bottom = QHBoxLayout()
        bottom.setSpacing(30)
        arm = RobotArmWidget()
        container = StorageContainerWidget()
        bottom.addWidget(arm, 0, Qt.AlignLeft | Qt.AlignBottom)
        bottom.addStretch(1)
        bottom.addWidget(container, 0, Qt.AlignRight | Qt.AlignBottom)
        scene_v.addLayout(bottom)

        layout.addWidget(scene)
