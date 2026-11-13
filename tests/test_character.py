"""The animation data is sane, and every frame paints without errors."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter

from hydrobuddy.ui.character import VIEW_H, VIEW_W, character_icon, paint_character
from hydrobuddy.ui.character_anim import ANIMATIONS, HIDDEN_DY, Pose


def test_animations_chain_to_existing_animations():
    for animation in ANIMATIONS.values():
        assert animation.next is None or animation.next in ANIMATIONS
        assert animation.duration > 0


def test_he_starts_and_ends_out_of_sight():
    assert ANIMATIONS["appear"].pose_at(0).dy == HIDDEN_DY
    for name in ("leave", "leave_sad"):
        assert ANIMATIONS[name].pose_at(ANIMATIONS[name].duration).dy == HIDDEN_DY


def test_one_shots_hand_over_without_a_jump():
    # appear ends in the neutral pose that idle starts from
    assert ANIMATIONS["appear"].pose_at(1.0) == Pose()
    assert ANIMATIONS["idle"].pose_at(0) == Pose()


def test_idle_loops_seamlessly():
    idle = ANIMATIONS["idle"]
    start, end = idle.pose_at(0), idle.pose_at(idle.duration)
    assert abs(start.sy - end.sy) < 1e-9 and abs(start.arm_l - end.arm_l) < 1e-9


def test_glass_is_only_in_hand_while_celebrating():
    for name, animation in ANIMATIONS.items():
        for i in range(50):
            glass = animation.pose_at(animation.duration * i / 49).glass
            assert glass >= 0
            if name != "celebrate":
                assert glass == 0


def test_every_frame_paints(qapp):
    image = QImage(VIEW_W, VIEW_H, QImage.Format.Format_ARGB32)
    for animation in ANIMATIONS.values():
        for i in range(40):
            t = animation.duration * i / 39
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            paint_character(painter, animation.pose_at(t), animation.sparkles_at(t))
            painter.end()
    # the last frame painted is a 'leave' frame: he is hidden, so nothing was drawn
    assert image.pixelColor(VIEW_W // 2, VIEW_H - 10).alpha() == 0


def test_idle_frame_is_visible_and_background_is_transparent(qapp):
    image = QImage(VIEW_W, VIEW_H, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    paint_character(painter, ANIMATIONS["idle"].pose_at(0))
    painter.end()
    assert image.pixelColor(108, VIEW_H - 40).alpha() == 255  # body
    assert image.pixelColor(4, 4).alpha() == 0  # corner stays see-through


def test_tray_icon_renders(qapp):
    icon = character_icon(64)
    assert icon.width() == 64
    assert icon.toImage().pixelColor(32, 44).alpha() == 255
