"""The reminder popup: the character rises from the taskbar and a speech bubble appears.

The window is frameless and fully transparent around the character and the
bubble, so the user's own screen shows through.
"""

from __future__ import annotations

import math
from enum import Enum

from PySide6.QtCore import (
    QEasingCurve,
    QElapsedTimer,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
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
from hydrobuddy.ui.overlay import ScreenBlocker

BUBBLE_W, BUBBLE_H = 256, 136
MARGIN_RIGHT = 20
IGNORE_SECONDS = 60  # no answer for this long after Done unlocks counts as ignored
BLOCK_TITLE = "Water break 💧"
BLOCK_SUBTITLE = "Take a moment, grab your glass and drink. The buttons unlock shortly."

_BUTTON_STYLE = (
    "QPushButton{background:%s;color:%s;border:2px solid #1b3a6b;"
    "border-radius:11px;padding:5px 10px;}"
    "QPushButton:hover{background:%s;}"
    "QPushButton:disabled{background:#e6ebf1;color:#8794a6;border-color:#b3bfce;}"
)
DONE_TEXT, SNOOZE_TEXT = "Done ✓", "Snooze"


class SpeechBubble(QWidget):
    done_clicked = Signal()
    snooze_clicked = Signal()
    done_unlocked = Signal()  # the Done button's cooldown has finished

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
        self.done_button = QPushButton(DONE_TEXT)
        self.done_button.setStyleSheet(_BUTTON_STYLE % ("#3fa3e0", "white", "#2f8fcc"))
        self.snooze_button = QPushButton(SNOOZE_TEXT)
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

        # Cooldown: each button stays locked, showing a countdown, for its own time.
        self._cooldown_clock = QElapsedTimer()
        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setInterval(100)
        self._cooldown_timer.timeout.connect(self._update_cooldown)
        self._done_wait = self._snooze_wait = 0.0
        self.hide()

    def set_content(self, message: str, record: DayRecord, buttons: bool) -> None:
        self.message.setText(message)
        self.progress_label.setText(f"{record.glasses} of {record.goal} glasses today")
        self.bar.setRange(0, record.goal)
        self.bar.setValue(min(record.glasses, record.goal))
        self.stop_cooldown()
        self.done_button.setVisible(buttons)
        self.snooze_button.setVisible(buttons)

    def set_message(self, message: str) -> None:
        self.message.setText(message)
        self.stop_cooldown()
        self.done_button.hide()
        self.snooze_button.hide()

    # --- cooldown ---------------------------------------------------------------
    @property
    def done_ready(self) -> bool:
        return self.done_button.isEnabled()

    @property
    def snooze_ready(self) -> bool:
        return self.snooze_button.isEnabled()

    def start_cooldown(self, done_seconds: float, snooze_seconds: float) -> None:
        """Lock both buttons; each unlocks after its own number of seconds."""

        self._done_wait, self._snooze_wait = done_seconds, snooze_seconds
        self.done_button.setEnabled(False)
        self.snooze_button.setEnabled(False)
        self._cooldown_clock.start()
        self._cooldown_timer.start()
        self._update_cooldown()

    def stop_cooldown(self) -> None:
        """Forget any cooldown and put the buttons back to their normal, unlocked look."""

        self._cooldown_timer.stop()
        for button, text in ((self.done_button, DONE_TEXT), (self.snooze_button, SNOOZE_TEXT)):
            button.setEnabled(True)
            button.setText(text)

    def _update_cooldown(self) -> None:
        elapsed = self._cooldown_clock.elapsed() / 1000
        for button, text, countdown_name, wait in (
            (self.done_button, DONE_TEXT, "Done", self._done_wait),
            (self.snooze_button, SNOOZE_TEXT, "Snooze", self._snooze_wait),
        ):
            if button.isEnabled():
                continue
            remaining = wait - elapsed
            if remaining > 0:
                button.setText(f"{countdown_name} ({math.ceil(remaining)})")
                continue
            button.setEnabled(True)
            button.setText(text)
            if button is self.done_button:
                self.done_unlocked.emit()
        if self.done_ready and self.snooze_ready:
            self._cooldown_timer.stop()

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
        self.stop_cooldown()
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

    A reminder can carry a cooldown (Done and Snooze stay locked for a while, so
    there is time to actually drink) and can block the whole screen until answered.
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
        self.bubble.done_unlocked.connect(self._start_ignore_timer)

        self.blocker = ScreenBlocker()
        self.blocker.on_timeout = self._start_ignore_timer  # fall back to a normal reminder
        self.cooldown_scale = 1.0  # tests shrink this to run cooldowns faster
        self._done_cooldown = self._snooze_cooldown = 0.0

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
    def remind(
        self,
        message: str,
        record: DayRecord,
        done_cooldown: float = 0.0,
        snooze_cooldown: float = 0.0,
        block_screen: bool = False,
    ) -> bool:
        """Pop up and ask the user to drink. Returns False if he is already on screen.

        ``done_cooldown`` / ``snooze_cooldown``: seconds each button stays locked.
        ``block_screen``: dim every screen and swallow clicks until answered.
        """

        if self.active:
            return False
        self.bubble.set_content(message, record, buttons=True)
        self._cheer_on_arrival = False
        self._done_cooldown, self._snooze_cooldown = done_cooldown, snooze_cooldown
        self._enter(block_screen)
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
        self.blocker.release()
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
    def _enter(self, block_screen: bool = False) -> None:
        self.phase = Phase.ARRIVING
        if block_screen:
            self.blocker.block(
                BLOCK_TITLE,
                BLOCK_SUBTITLE,
                still_needed=lambda: self.phase in (Phase.ARRIVING, Phase.WAITING),
            )
        area = QGuiApplication.primaryScreen().availableGeometry()
        # The window's bottom edge sits exactly on the taskbar line.
        self.move(area.right() + 1 - self.width() - MARGIN_RIGHT, area.bottom() + 1 - self.height())
        self.show()
        self.raise_()  # above the screen block, if there is one
        self.character.play("appear")

    def _celebrate(self) -> None:
        self.blocker.release()
        self.phase = Phase.CELEBRATING
        self.character.play("celebrate")

    def _start_ignore_timer(self) -> None:
        """Start counting towards "ignored": only once Done works and nothing is blocked."""

        if self.phase is Phase.WAITING and self.bubble.done_ready and not self.blocker.active:
            self._ignore_timer.start(int(self.ignore_seconds * 1000))

    def _on_animation_finished(self, name: str) -> None:
        if name == "appear":
            self.bubble.fade_in()
            if self._cheer_on_arrival:
                self._celebrate()
            else:
                self.phase = Phase.WAITING
                self.bubble.start_cooldown(
                    self._done_cooldown * self.cooldown_scale,
                    self._snooze_cooldown * self.cooldown_scale,
                )
        elif name in ("celebrate", "sad"):
            self.phase = Phase.LEAVING
            self.bubble.fade_out()
        elif name in ("leave", "leave_sad"):
            self._finish()

    def _finish(self) -> None:
        self.phase = Phase.HIDDEN
        self.blocker.release()
        self.bubble.reset()
        self.hide()
        self.closed.emit()
        if self._pending_cheer is not None:
            message, record = self._pending_cheer
            self._pending_cheer = None
            self.cheer(message, record)

    def _on_done(self) -> None:
        if self.phase is Phase.WAITING and self.bubble.done_ready:
            self.done.emit()

    def _on_snooze(self) -> None:
        if self.phase is Phase.WAITING and self.bubble.snooze_ready:
            self.snoozed.emit()

    def _on_ignored(self) -> None:
        if self.phase is Phase.WAITING:
            self.ignored.emit()
