"""Draws the water-drop character as smooth vector art and plays his animations.

Nothing here is a bitmap: every frame is painted with anti-aliased shapes, so
he stays crisp at any screen scale.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import QWidget

from hydrobuddy.ui.character_anim import ANIMATIONS, Animation, Pose

VIEW_W, VIEW_H = 230, 250  # the bottom edge of the view is the taskbar line
CX = 108.0  # horizontal centre of the character
R = 46.0  # radius of the round bottom
TIP = 124.0  # height of the tip above the feet

NAVY = QColor(27, 58, 107)
INK = QColor(22, 34, 66)
BODY_LIGHT = QColor(170, 232, 255)
BODY_DEEP = QColor(66, 172, 238)
BODY_FLAT = QColor(104, 200, 246)
SHADE = QColor(30, 110, 200, 70)
CHEEK = QColor(255, 120, 150, 120)
TONGUE = QColor(240, 100, 120)
WATER = QColor(34, 118, 222, 235)
WATER_TOP = QColor(150, 205, 255, 235)
ARM_LEN = 26.0
SIP_HAND = (21.0, -15.0)  # where the right hand holds the glass while drinking
GLASS = QColor(240, 250, 255, 205)
SPARK = QColor(255, 212, 64)
SPARK_EDGE = QColor(232, 150, 30)


def _body_path() -> QPainterPath:
    """Teardrop with the feet at (0, 0) and the tip at (0, -TIP)."""

    k = 0.5523 * R
    path = QPainterPath(QPointF(0, -TIP))
    path.cubicTo(QPointF(R * 0.30, -TIP * 0.74), QPointF(R, -R * 1.85), QPointF(R, -R))
    path.cubicTo(QPointF(R, -R + k), QPointF(k, 0), QPointF(0, 0))
    path.cubicTo(QPointF(-k, 0), QPointF(-R, -R + k), QPointF(-R, -R))
    path.cubicTo(QPointF(-R, -R * 1.85), QPointF(-R * 0.30, -TIP * 0.74), QPointF(0, -TIP))
    return path


def _glass_path() -> QPainterPath:
    """Tumbler, wider at the rim, with the grip point at (0, 0)."""

    path = QPainterPath(QPointF(-11, -24))
    path.lineTo(11, -24)
    path.lineTo(8.5, 5)
    path.quadTo(8, 8, 5, 8)
    path.lineTo(-5, 8)
    path.quadTo(-8, 8, -8.5, 5)
    path.closeSubpath()
    return path


def _star_path() -> QPainterPath:
    """Four-point sparkle with radius 1."""

    path = QPainterPath()
    for i in range(8):
        radius = 1.0 if i % 2 == 0 else 0.36
        angle = math.pi / 4 * i
        point = QPointF(math.sin(angle) * radius, -math.cos(angle) * radius)
        path.moveTo(point) if i == 0 else path.lineTo(point)
    path.closeSubpath()
    return path


_BODY = _body_path()
_GLASS = _glass_path()
_STAR = _star_path()


def _round_pen(color: QColor, width: float) -> QPen:
    return QPen(
        color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin
    )


def paint_character(
    p: QPainter, pose: Pose, sparkles: list[tuple[float, float, float]] | None = None
) -> None:
    """Paint one frame into a VIEW_W x VIEW_H area."""

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(CX, VIEW_H + pose.dy)  # origin = the character's feet

    def pt(x: float, y: float) -> QPointF:
        return QPointF(x * pose.sx, y * pose.sy)

    shape = QTransform.fromScale(pose.sx, pose.sy).map(_BODY)

    # The right arm goes in front of the body while it holds a glass or reaches across.
    hand_r = _right_hand(pt, pose)
    right_in_front = pose.glass > 0.02 or shape.contains(hand_r)

    _paint_hand(p, _paint_arm(p, pt(-(R - 6), -R * 0.88), _hand(pt, -1, pose.arm_l, ARM_LEN)))
    if not right_in_front:
        _paint_right_arm(p, pt, pose)

    # Body: soft gradient, a shaded edge, highlights, then the outline.
    gradient = QRadialGradient(pt(-R * 0.35, -R * 1.5), R * 2.3)
    gradient.setColorAt(0.0, BODY_LIGHT)
    gradient.setColorAt(1.0, BODY_DEEP)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(gradient)
    p.drawPath(shape)
    p.setBrush(SHADE)
    p.drawPath(shape.subtracted(shape.translated(-9, -7)))

    p.setBrush(QColor(255, 255, 255, 215))
    p.save()
    p.translate(pt(-R * 0.46, -R * 1.62))
    p.rotate(20)
    p.drawEllipse(QPointF(0, 0), 5.5 * pose.sx, 12 * pose.sy)
    p.restore()
    p.drawEllipse(pt(-R * 0.64, -R * 1.16), 3.2, 3.2)

    p.setPen(_round_pen(NAVY, 4))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(shape)

    _paint_face(p, pt, pose)
    if right_in_front:
        _paint_right_arm(p, pt, pose)
    p.restore()

    for x, y, size in sparkles or ():
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(x, y)
        p.scale(size, size)
        p.setPen(QPen(SPARK_EDGE, 0.14))
        p.setBrush(SPARK)
        p.drawPath(_STAR)
        p.restore()


def _hand(pt, side: int, angle: float, length: float) -> QPointF:
    shoulder = pt(side * (R - 6), -R * 0.88)
    a = math.radians(angle)
    return shoulder + QPointF(side * math.cos(a) * length, -math.sin(a) * length)


def _right_hand(pt, pose: Pose) -> QPointF:
    """The right hand: on its arm, or pulled towards the mouth while sipping."""

    hand = _hand(pt, +1, pose.arm_r, pose.arm_r_len)
    return hand + (pt(*SIP_HAND) - hand) * pose.sip


def _paint_arm(p: QPainter, shoulder: QPointF, hand: QPointF) -> QPointF:
    """A stubby outlined arm from shoulder to hand. Returns the hand position."""

    p.setPen(_round_pen(NAVY, 10))
    p.drawLine(shoulder, hand)
    p.setPen(_round_pen(BODY_FLAT, 4.5))
    p.drawLine(shoulder, hand)
    return hand


def _paint_hand(p: QPainter, hand: QPointF) -> None:
    p.setPen(_round_pen(NAVY, 2.6))
    p.setBrush(BODY_FLAT)
    p.drawEllipse(hand, 6.2, 6.2)


def _paint_right_arm(p: QPainter, pt, pose: Pose) -> None:
    hand = _paint_arm(p, pt(R - 6, -R * 0.88), _right_hand(pt, pose))
    if pose.glass > 0.02:
        p.save()
        p.translate(hand)
        p.rotate(pose.tilt)
        p.scale(pose.glass, pose.glass)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(GLASS)
        p.drawPath(_GLASS)
        if pose.water > 0.01:
            p.save()
            p.setClipPath(_GLASS, Qt.ClipOperation.IntersectClip)
            p.rotate(-pose.tilt)  # the water surface stays level as the glass tips
            level = 9 - 29 * min(pose.water, 1.0)
            p.fillRect(QRectF(-40, level, 80, 80), WATER)
            p.fillRect(QRectF(-40, level, 80, 2.2), WATER_TOP)
            p.restore()
        p.setPen(_round_pen(NAVY, 2.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(_GLASS)
        p.setPen(_round_pen(QColor(255, 255, 255, 190), 2))
        p.drawLine(QPointF(-6.6, -19), QPointF(-5.4, -4))
        p.restore()
    _paint_hand(p, hand)


def _paint_face(p: QPainter, pt, pose: Pose) -> None:
    eye_y = -R * 1.15
    sad = pose.eyes == "sad"

    if not sad:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(CHEEK)
        for side in (-1, 1):
            p.drawEllipse(pt(side * 29, -R * 0.92), 7.5, 4.5)

    for side in (-1, 1):
        c = pt(side * 17, eye_y)
        if pose.eyes == "happy":  # smiling arcs
            arc = QPainterPath(c + QPointF(-7, 3))
            arc.quadTo(c + QPointF(0, -9), c + QPointF(7, 3))
            p.setPen(_round_pen(INK, 3.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(arc)
        elif pose.eye_open < 0.18:  # closed
            lid = QPainterPath(c + QPointF(-7, 0))
            lid.quadTo(c + QPointF(0, 4), c + QPointF(7, 0))
            p.setPen(_round_pen(INK, 3.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(lid)
        else:
            ry = (6.5 if sad else 8.0) * min(pose.eye_open, 1.3)
            if sad:
                c += QPointF(0, 2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(INK)
            p.drawEllipse(c, 6.0, ry)
            if ry > 4:
                p.setBrush(QColor(255, 255, 255))
                p.drawEllipse(c + QPointF(-2.0, -ry * 0.4), 2.4, 2.4)
        if sad:  # worried brows, higher in the middle
            p.setPen(_round_pen(INK, 3))
            p.drawLine(c + QPointF(side * 9, -11), c + QPointF(-side * 6, -16))

    m = pt(0, -R * 0.72)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_round_pen(INK, 3.2))
    if pose.mouth == "smile":
        smile = QPainterPath(m + QPointF(-9, -3))
        smile.quadTo(m + QPointF(0, 8), m + QPointF(9, -3))
        p.drawPath(smile)
    elif pose.mouth == "frown":
        frown = QPainterPath(m + QPointF(-8, 4))
        frown.quadTo(m + QPointF(0, -6), m + QPointF(8, 4))
        p.drawPath(frown)
    elif pose.mouth == "sip":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(INK)
        p.drawEllipse(m + QPointF(3, 0), 3.6, 4.2)
    elif pose.mouth == "open":
        mouth = QPainterPath(m + QPointF(-10, -4))
        mouth.lineTo(m + QPointF(10, -4))
        mouth.cubicTo(m + QPointF(10, 6), m + QPointF(5, 11), m + QPointF(0, 11))
        mouth.cubicTo(m + QPointF(-5, 11), m + QPointF(-10, 6), m + QPointF(-10, -4))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(INK)
        p.drawPath(mouth)
        p.save()
        p.setClipPath(mouth, Qt.ClipOperation.IntersectClip)
        p.setBrush(TONGUE)
        p.drawEllipse(m + QPointF(0, 11), 6.5, 5.0)
        p.restore()
        p.setPen(_round_pen(INK, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(mouth)

    if 0 <= pose.tear < 1:
        drop = pt(-17, eye_y) + QPointF(-1, 12 + pose.tear * 30)
        fade = 1.0 if pose.tear < 0.8 else (1 - pose.tear) / 0.2
        p.setOpacity(fade)
        p.setPen(_round_pen(NAVY, 1.6))
        p.setBrush(QColor(205, 240, 255))
        p.drawEllipse(drop, 3.4, 4.6)
        p.setOpacity(1.0)


def character_icon(size: int = 64) -> QPixmap:
    """The character's neutral pose as a small pixmap (used for the tray icon)."""

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    scale = size / 150
    p.translate(size / 2, size * 0.96)
    p.scale(scale, scale)
    p.translate(-CX, -VIEW_H)
    paint_character(p, Pose())
    p.end()
    return pixmap


class CharacterView(QWidget):
    """Plays one animation at a time and reports when a one-shot finishes."""

    finished = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(VIEW_W, VIEW_H)
        self._animation: Animation | None = None
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self.speed = 1.0  # tests raise this to run animations faster

    @property
    def current(self) -> str | None:
        """Name of the animation playing now, if any."""

        return self._animation.name if self._animation else None

    def _elapsed(self) -> float:
        return self._clock.elapsed() / 1000 * self.speed

    def play(self, name: str) -> None:
        self._animation = ANIMATIONS[name]
        self._clock.start()
        self._timer.start()
        self.update()

    def stop(self) -> None:
        self._timer.stop()
        self._animation = None
        self.update()

    def _tick(self) -> None:
        animation = self._animation
        if animation is None:
            return
        if self._elapsed() >= animation.duration:
            if animation.loop:
                self._clock.start()
            else:
                if animation.next:
                    self.play(animation.next)
                else:
                    self.stop()
                self.finished.emit(animation.name)
        self.update()

    def paintEvent(self, _event) -> None:
        animation = self._animation
        if animation is None:
            return
        t = min(self._elapsed(), animation.duration)
        paint_character(QPainter(self), animation.pose_at(t), animation.sparkles_at(t))
