"""The reminder popup: the character rises from the taskbar and a speech bubble appears.

The window is frameless and fully transparent around the character and the
bubble, so the user's own screen shows through.
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hydrobuddy.core.history import DayRecord
from hydrobuddy.ui.character import NAVY, VIEW_H, VIEW_W, CharacterView

BUBBLE_W, BUBBLE_H = 256, 136
MARGIN_RIGHT = 20
IGNORE_SECONDS = 60  # no answer for this long counts as ignored

_BUTTON_STYLE = (
    "QPushButton{background:%s;color:%s;border:2px solid #1b3a6b;"
    "border-radius:11px;padding:5px 14px;}"
    "QPushButton:hover{background:%s;}"
)


class SpeechBubble(QWidget):
    done_clicked = Signal()
    snooze_clicked = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(BUBBLE_W, BUBBLE_H)

        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.message.setStyleSheet("color:#1b3a6b;")
        self.progress_label = QLabel()
        self.progress_label.setFont(QFont("Segoe UI", 9))
        self.progress_label.setStyleSheet("color:#4a6a95;")
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        self.bar.setStyleSheet(
            "QProgressBar{background:#dceefa;border:none;border-radius:4px;}"
            "QProgressBar::chunk{background:#3fa3e0;border-radius:4px;}"
        )
        self.done_button = QPushButton("Done ✓")
        self.done_button.setStyleSheet(_BUTTON_STYLE % ("#3fa3e0", "white", "#2f8fcc"))
        self.snooze_button = QPushButton("Snooze")
        self.snooze_button.setStyleSheet(_BUTTON_STYLE % ("white", "#1b3a6b", "#eef6fc"))
        for button in (self.done_button, self.snooze_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.done_button.clicked.connect(self.done_clicked)
        self.snooze_button.clicked.connect(self.snooze_clicked)

        buttons = QHBoxLayout()
        buttons.addWidget(self.done_button)
        buttons.addWidget(self.snooze_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 28, 12)  # the right margin leaves room for the tail
        layout.setSpacing(6)
        layout.addWidget(self.message)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.bar)
        layout.addLayout(buttons)

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        self._fade = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade.setDuration(220)
        self._fade.finished.connect(self._after_fade)
        self.hide()

    def set_content(self, message: str, record: DayRecord, buttons: bool) -> None:
        self.message.setText(message)
        self.progress_label.setText(f"{record.glasses} of {record.goal} glasses today")
        self.bar.setRange(0, record.goal)
        self.bar.setValue(min(record.glasses, record.goal))
        self.done_button.setVisible(buttons)
        self.snooze_button.setVisible(buttons)

    def set_message(self, message: str) -> None:
        self.message.setText(message)
        self.done_button.hide()
        self.snooze_button.hide()

    def fade_in(self) -> None:
        self.show()
        self._fade_to(1.0, QEasingCurve.Type.OutCubic)

    def fade_out(self) -> None:
        self._fade_to(0.0, QEasingCurve.Type.InCubic)

    def _fade_to(self, opacity: float, curve: QEasingCurve.Type) -> None:
        self._fade.stop()
        self._fade.setStartValue(self._effect.opacity())
        self._fade.setEndValue(opacity)
        self._fade.setEasingCurve(curve)
        self._fade.start()

    def reset(self) -> None:
        self._fade.stop()
        self._effect.setOpacity(0.0)
        self.hide()

    def _after_fade(self) -> None:
        if self._effect.opacity() < 0.01:
            self.hide()  # so invisible buttons can't be clicked

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRectF(2, 2, self.width() - 18, self.height() - 4)
        path = QPainterPath()
        path.addRoundedRect(body, 18, 18)
        tail = QPainterPath()
        tail.moveTo(body.right() - 2, 44)
        tail.lineTo(self.width() - 2, 55)
        tail.lineTo(body.right() - 2, 66)
        tail.closeSubpath()
        p.setPen(QPen(NAVY, 2.5))
        p.setBrush(QColor(255, 255, 255, 252))
        p.drawPath(path.united(tail))


class Phase(Enum):
    HIDDEN = "hidden"
    ARRIVING = "arriving"  # rising from the taskbar
    WAITING = "waiting"  # Done / Snooze are live
    CELEBRATING = "celebrating"
    SAD = "sad"
    LEAVING = "leaving"


class ReminderPopup(QWidget):
    """Shows a reminder (or a quick cheer) and reports what the user chose.

    Phases: HIDDEN -> ARRIVING -> WAITING -> CELEBRATING or SAD -> LEAVING -> HIDDEN.
    A cheer that arrives while he is ARRIVING is played as soon as he lands; one
    that arrives while he is SAD or LEAVING is played again right after he leaves.
    """

    done = Signal()  # the user clicked Done
    snoozed = Signal()  # the user clicked Snooze
    ignored = Signal()  # nobody answered in time
    closed = Signal()  # the character has left and the window is hidden

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(BUBBLE_W + VIEW_W - 12, VIEW_H)

        self.bubble = SpeechBubble(self)
        self.bubble.move(0, 26)
        self.character = CharacterView(self)
        self.character.move(BUBBLE_W - 12, 0)
        self.bubble.raise_()

        self.bubble.done_clicked.connect(self._on_done)
        self.bubble.snooze_clicked.connect(self._on_snooze)
        self.character.finished.connect(self._on_animation_finished)

        self._ignore_timer = QTimer(self)
        self._ignore_timer.setSingleShot(True)
        self._ignore_timer.timeout.connect(self._on_ignored)

        self.ignore_seconds = IGNORE_SECONDS
        self.phase = Phase.HIDDEN
        self._cheer_on_arrival = False
        self._pending_cheer: tuple[str, DayRecord] | None = None

    @property
    def active(self) -> bool:
        return self.phase is not Phase.HIDDEN

    # --- what the app can ask for ---------------------------------------------
    def remind(self, message: str, record: DayRecord) -> bool:
        """Pop up and ask the user to drink. Returns False if he is already on screen."""

        if self.active:
            return False
        self.bubble.set_content(message, record, buttons=True)
        self._cheer_on_arrival = False
        self._enter()
        return True

    def cheer(self, message: str, record: DayRecord) -> None:
        """Celebrate a glass: answers a reminder, or pops up briefly on its own."""

        if self.phase in (Phase.SAD, Phase.LEAVING):
            self._pending_cheer = (message, record)  # replay once he has left
            return
        self._ignore_timer.stop()
        self.bubble.set_content(message, record, buttons=False)
        if self.phase is Phase.HIDDEN:
            self._cheer_on_arrival = True
            self._enter()
        elif self.phase is Phase.ARRIVING:
            self._cheer_on_arrival = True  # celebrate as soon as he lands
        elif self.phase is Phase.WAITING:
            self._celebrate()
        # CELEBRATING: already cheering; the bubble now shows the new count

    def sadden(self, message: str) -> None:
        """React to a snooze or to being ignored, then leave."""

        if self.phase is not Phase.WAITING:
            return
        self._ignore_timer.stop()
        self.bubble.set_message(message)
        self.phase = Phase.SAD
        self.character.play("sad")

    def dismiss(self) -> None:
        """Hide immediately (used when the app quits)."""

        self._ignore_timer.stop()
        self._pending_cheer = None
        self.character.stop()
        self._finish()

    # --- internals ------------------------------------------------------------
    def _enter(self) -> None:
        self.phase = Phase.ARRIVING
        area = QGuiApplication.primaryScreen().availableGeometry()
        # The window's bottom edge sits exactly on the taskbar line.
        self.move(area.right() + 1 - self.width() - MARGIN_RIGHT, area.bottom() + 1 - self.height())
        self.show()
        self.character.play("appear")

    def _celebrate(self) -> None:
        self.phase = Phase.CELEBRATING
        self.character.play("celebrate")

    def _on_animation_finished(self, name: str) -> None:
        if name == "appear":
            self.bubble.fade_in()
            if self._cheer_on_arrival:
                self._celebrate()
            else:
                self.phase = Phase.WAITING
                self._ignore_timer.start(int(self.ignore_seconds * 1000))
        elif name in ("celebrate", "sad"):
            self.phase = Phase.LEAVING
            self.bubble.fade_out()
        elif name in ("leave", "leave_sad"):
            self._finish()

    def _finish(self) -> None:
        self.phase = Phase.HIDDEN
        self.bubble.reset()
        self.hide()
        self.closed.emit()
        if self._pending_cheer is not None:
            message, record = self._pending_cheer
            self._pending_cheer = None
            self.cheer(message, record)

    def _on_done(self) -> None:
        if self.phase is Phase.WAITING:
            self.done.emit()

    def _on_snooze(self) -> None:
        if self.phase is Phase.WAITING:
            self.snoozed.emit()

    def _on_ignored(self) -> None:
        if self.phase is Phase.WAITING:
            self.ignored.emit()
