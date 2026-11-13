"""Live demo: the water-drop character pops up over your real desktop.

He rises from behind the taskbar (bottom-right), a speech bubble appears,
and you click Done (he drinks and cheers) or Snooze (he's sad). Then he
sinks back down and the demo exits.

Run:  .venv/Scripts/python tools/demo_popup.py
      .venv/Scripts/python tools/demo_popup.py --loop        # keep replaying
      .venv/Scripts/python tools/demo_popup.py --capture DIR # self-test screenshots
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

ROOT = Path(__file__).resolve().parents[1]
CHAR_DIR = ROOT / "hydrobuddy" / "assets" / "character"

NAVY = QColor(27, 58, 107)
BUBBLE_W, BUBBLE_H = 250, 132
GAP = 4
MARGIN_RIGHT = 24


class Sprites:
    """Loads the sprite strips described by character.json."""

    def __init__(self, folder: Path) -> None:
        self.meta = json.loads((folder / "character.json").read_text(encoding="utf-8"))
        fw, fh = self.meta["frame_size"]
        scale = self.meta["scale"]
        self.size = (fw * scale, fh * scale)
        self.frames: dict[str, list[QPixmap]] = {}
        for name, info in self.meta["states"].items():
            strip = QImage(str(folder / info["file"]))
            self.frames[name] = [
                QPixmap.fromImage(
                    strip.copy(i * fw, 0, fw, fh).scaled(
                        fw * scale, fh * scale, mode=Qt.TransformationMode.FastTransformation
                    )
                )
                for i in range(info["frames"])
            ]


class CharacterView(QWidget):
    """Plays one state at a time; calls on_finished(state) for one-shots."""

    def __init__(self, sprites: Sprites, on_finished) -> None:
        super().__init__()
        self.sprites = sprites
        self.on_finished = on_finished
        self.setFixedSize(*sprites.size)
        self.state = "leave"
        self.index = len(sprites.frames["leave"]) - 1  # start hidden
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def play(self, state: str) -> None:
        self.state, self.index = state, 0
        self.timer.start(int(1000 / self.sprites.meta["states"][state]["fps"]))
        self.update()

    def _tick(self) -> None:
        info = self.sprites.meta["states"][self.state]
        if self.index + 1 < info["frames"]:
            self.index += 1
        elif info["loop"]:
            self.index = 0
        else:
            self.timer.stop()
            finished = self.state
            if info["next"]:
                self.play(info["next"])
            self.on_finished(finished)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.sprites.frames[self.state][self.index])


class SpeechBubble(QWidget):
    """Rounded bubble with a tail pointing at the character."""

    def __init__(self, on_done, on_snooze) -> None:
        super().__init__()
        self.setFixedSize(BUBBLE_W, BUBBLE_H)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.message.setStyleSheet("color: #1b3a6b;")
        self.progress_label = QLabel("5 of 8 glasses today")
        self.progress_label.setFont(QFont("Segoe UI", 9))
        self.progress_label.setStyleSheet("color: #4a6a95;")
        self.bar = QProgressBar()
        self.bar.setRange(0, 8)
        self.bar.setValue(5)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        self.bar.setStyleSheet(
            "QProgressBar{background:#dceefa;border:none;border-radius:4px;}"
            "QProgressBar::chunk{background:#3fa3e0;border-radius:4px;}"
        )
        self.done_btn = QPushButton("Done ✓")
        self.snooze_btn = QPushButton("Snooze")
        for btn, primary in ((self.done_btn, True), (self.snooze_btn, False)):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            btn.setStyleSheet(
                "QPushButton{background:%s;color:%s;border:2px solid #1b3a6b;"
                "border-radius:10px;padding:4px 14px;}"
                "QPushButton:hover{background:%s;}"
                % (("#3fa3e0", "white", "#2f8fcc") if primary else ("white", "#1b3a6b", "#eef6fc"))
            )
        self.done_btn.clicked.connect(on_done)
        self.snooze_btn.clicked.connect(on_snooze)

        buttons = QHBoxLayout()
        buttons.addWidget(self.done_btn)
        buttons.addWidget(self.snooze_btn)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 26, 12)  # right margin leaves room for the tail
        layout.setSpacing(6)
        layout.addWidget(self.message)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.bar)
        layout.addLayout(buttons)

        self.effect = QGraphicsOpacityEffect(self)
        self.effect.setOpacity(0.0)
        self.setGraphicsEffect(self.effect)
        self.fade = QPropertyAnimation(self.effect, b"opacity", self)
        self.fade.setDuration(220)

    def show_animated(self) -> None:
        self.show()
        self.fade.stop()
        self.fade.setStartValue(self.effect.opacity())
        self.fade.setEndValue(1.0)
        self.fade.setEasingCurve(QEasingCurve.Type.OutBack)
        self.fade.start()

    def hide_animated(self) -> None:
        self.fade.stop()
        self.fade.setStartValue(self.effect.opacity())
        self.fade.setEndValue(0.0)
        self.fade.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade.start()

    def set_buttons_visible(self, visible: bool) -> None:
        self.done_btn.setVisible(visible)
        self.snooze_btn.setVisible(visible)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRectF(2, 2, self.width() - 16, self.height() - 4)
        path = QPainterPath()
        path.addRoundedRect(body, 16, 16)
        tail = QPainterPath()
        ty = 40
        tail.moveTo(body.right() - 2, ty)
        tail.lineTo(self.width() - 2, ty + 10)
        tail.lineTo(body.right() - 2, ty + 20)
        tail.closeSubpath()
        path = path.united(tail)
        p.setPen(QPen(NAVY, 2.5))
        p.setBrush(QColor(255, 255, 255, 250))
        p.drawPath(path)


class Buddy(QWidget):
    def __init__(self, loop: bool, capture_dir: Path | None) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.loop = loop
        self.capture_dir = capture_dir
        self.busy = False  # True once Done/Snooze is handled for this popup

        sprites = Sprites(CHAR_DIR)
        cw, ch = sprites.size
        self.setFixedSize(BUBBLE_W + GAP + cw, ch)

        self.bubble = SpeechBubble(self._done, self._snooze)
        self.bubble.setParent(self)
        self.bubble.move(0, 18)
        self.bubble.hide()
        self.character = CharacterView(sprites, self._on_finished)
        self.character.setParent(self)
        self.character.move(BUBBLE_W + GAP, 0)

        self.ignore_timer = QTimer(self, singleShot=True)
        self.ignore_timer.timeout.connect(self._snooze)

        # Sit exactly on top of the taskbar so the sprite's bottom edge = taskbar line.
        area = QApplication.primaryScreen().availableGeometry()
        self.move(
            QPoint(
                area.right() + 1 - self.width() - MARGIN_RIGHT, area.bottom() + 1 - self.height()
            )
        )

    def start(self) -> None:
        self.bubble.message.setText("Water break! Grab a glass 💧")
        self.bubble.progress_label.setText("5 of 8 glasses today")
        self.bubble.bar.setValue(5)
        self.bubble.set_buttons_visible(True)
        self.busy = False
        self.show()
        self.character.play("appear")

    def _on_finished(self, state: str) -> None:
        if state == "appear":
            self.bubble.show_animated()
            self.ignore_timer.start(30_000)  # ignored for 30 s -> sad
        elif state in ("celebrate", "sad"):
            self.bubble.hide_animated()
        elif state == "leave":
            if self.loop:
                QTimer.singleShot(1500, self.start)
            else:
                QTimer.singleShot(300, QApplication.quit)

    def _done(self) -> None:
        if self.busy:
            return
        self.busy = True
        self.ignore_timer.stop()
        self.bubble.message.setText("Nice! Small sip, big win 🎉")
        self.bubble.progress_label.setText("6 of 8 glasses today")
        self.bubble.bar.setValue(6)
        self.bubble.set_buttons_visible(False)
        self.character.play("celebrate")

    def _snooze(self) -> None:
        if self.busy:
            return
        self.busy = True
        self.ignore_timer.stop()
        self.bubble.message.setText("Okay… I'll come back in 10 minutes.")
        self.bubble.set_buttons_visible(False)
        self.character.play("sad")

    # --- self-test support -------------------------------------------------
    def schedule_captures(self) -> None:
        shots = [(450, "1_rising"), (1600, "2_bubble"), (2420, "3_drinking"), (2950, "4_cheer")]
        for ms, name in shots:
            QTimer.singleShot(ms, lambda n=name: self._grab(n))
        QTimer.singleShot(2000, self._done)

    def _grab(self, name: str) -> None:
        g = self.geometry()
        pad = 60
        shot = QApplication.primaryScreen().grabWindow(
            0, g.x() - pad, g.y() - pad, g.width() + pad * 2, g.height() + pad * 2
        )
        shot.save(str(self.capture_dir / f"{name}.png"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--capture", type=Path)
    args = parser.parse_args()

    app = QApplication(sys.argv)
    buddy = Buddy(loop=args.loop, capture_dir=args.capture)
    buddy.start()
    if args.capture:
        args.capture.mkdir(parents=True, exist_ok=True)
        buddy.schedule_captures()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
