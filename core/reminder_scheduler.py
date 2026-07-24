"""Reminder timer scheduling for HydroBuddy."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from PySide6.QtCore import QObject, QTimer

from core import constants
from utils.logger import logger


class ReminderTimerKind(Enum):
    """Kinds of reminder-related timer events."""

    REMINDER = "reminder"
    SNOOZE = "snooze"
    IGNORE_TIMEOUT = "ignore_timeout"


class ReminderScheduler(QObject):
    """Owns the single Qt timer used by the reminder system."""

    def __init__(self, on_timeout: Callable[[ReminderTimerKind], None]) -> None:
        super().__init__()
        self._on_timeout = on_timeout
        self._active_kind: ReminderTimerKind | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._handle_timeout)

    @property
    def active_kind(self) -> ReminderTimerKind | None:
        """Return the currently scheduled timer kind, if any."""

        return self._active_kind

    @property
    def is_active(self) -> bool:
        """Return whether the scheduler currently has a running timer."""

        return self._timer.isActive()

    def schedule_reminder(
        self,
        minutes: int = constants.DEFAULT_REMINDER_INTERVAL,
    ) -> None:
        """Schedule the next normal reminder."""

        self._start(ReminderTimerKind.REMINDER, self._minutes_to_ms(minutes))

    def reset_reminder_timer(
        self,
        minutes: int = constants.DEFAULT_REMINDER_INTERVAL,
    ) -> None:
        """Cancel any timer and immediately start a fresh reminder interval."""

        self.schedule_reminder(minutes)

    def schedule_snooze(
        self,
        minutes: int = constants.DEFAULT_SNOOZE_INTERVAL,
    ) -> None:
        """Schedule the fixed snooze reminder."""

        self._start(ReminderTimerKind.SNOOZE, self._minutes_to_ms(minutes))

    def schedule_ignore_timeout(
        self,
        seconds: int = constants.IGNORE_TIMEOUT_SECONDS,
    ) -> None:
        """Schedule the timeout that means the user ignored the reminder."""

        self._start(ReminderTimerKind.IGNORE_TIMEOUT, seconds * 1000)

    def cancel(self) -> None:
        """Cancel the active timer, if one exists."""

        if self._timer.isActive():
            self._timer.stop()
            logger.info("Reminder timer cancelled: %s", self._active_kind_value())
        self._active_kind = None

    def cleanup(self) -> None:
        """Stop the timer and detach the callback during shutdown."""

        self.cancel()
        try:
            self._timer.timeout.disconnect(self._handle_timeout)
        except (RuntimeError, TypeError):
            pass
        self._on_timeout = lambda _kind: None
        logger.info("Reminder scheduler cleaned up")

    def _start(self, kind: ReminderTimerKind, milliseconds: int) -> None:
        if milliseconds <= 0:
            raise ValueError("Timer duration must be greater than zero")

        if self._timer.isActive():
            self._timer.stop()
            logger.info("Reminder timer cancelled: %s", self._active_kind_value())

        self._active_kind = kind
        self._timer.start(milliseconds)
        logger.info(
            "Reminder scheduled: kind=%s duration_ms=%s",
            kind.value,
            milliseconds,
        )

    def _handle_timeout(self) -> None:
        kind = self._active_kind
        self._active_kind = None

        if kind is None:
            logger.warning("Reminder timer expired without an active timer kind")
            return

        logger.info("Reminder timer expired: %s", kind.value)
        try:
            self._on_timeout(kind)
        except Exception:
            logger.exception("Error while handling reminder timer timeout")

    def _active_kind_value(self) -> str:
        return self._active_kind.value if self._active_kind is not None else "none"

    @staticmethod
    def _minutes_to_ms(minutes: int) -> int:
        if minutes <= 0:
            raise ValueError("Timer duration must be greater than zero")
        return minutes * 60 * 1000
