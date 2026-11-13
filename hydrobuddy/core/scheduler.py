"""When to show the next reminder.

The scheduler stores *timestamps*, not running timers. The UI polls
``is_due(now)`` every ~30 s. Because it compares against the wall clock,
sleep, hibernate and app restarts can't break it, and a long sleep produces
exactly one reminder, not a burst.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class Scheduler:
    interval: timedelta
    snooze: timedelta
    next_due: datetime | None = None
    paused_until: datetime | None = None
    showing: bool = False  # a reminder is currently on screen

    @classmethod
    def create(cls, interval_minutes: int, snooze_minutes: int) -> Scheduler:
        return cls(timedelta(minutes=interval_minutes), timedelta(minutes=snooze_minutes))

    # --- queries ------------------------------------------------------------
    def is_due(self, now: datetime) -> bool:
        if self.showing or self.next_due is None:
            return False
        if self.paused_until is not None and now < self.paused_until:
            return False
        return now >= self.next_due

    def is_paused(self, now: datetime) -> bool:
        return self.paused_until is not None and now < self.paused_until

    # --- transitions (each returns a new Scheduler) --------------------------
    def start(self, now: datetime) -> Scheduler:
        """Begin scheduling. Keeps a saved ``next_due`` so restarts don't reset the clock.

        If the saved reminder is already overdue (e.g. the PC was off), wait one
        snooze period instead of popping up the instant Windows starts.
        """

        if self.next_due is None:
            return replace(self, next_due=now + self.interval, showing=False)
        if self.next_due < now:
            return replace(self, next_due=now + self.snooze, showing=False)
        return replace(self, showing=False)

    def mark_shown(self, now: datetime) -> Scheduler:
        return replace(self, showing=True)

    def on_done(self, now: datetime) -> Scheduler:
        return replace(self, showing=False, next_due=now + self.interval)

    def on_snooze(self, now: datetime) -> Scheduler:
        return replace(self, showing=False, next_due=now + self.snooze)

    def on_skip(self, now: datetime) -> Scheduler:
        """Skipped or ignored: try again after a full interval."""

        return replace(self, showing=False, next_due=now + self.interval)

    def pause(self, until: datetime) -> Scheduler:
        return replace(self, paused_until=until)

    def resume(self, now: datetime) -> Scheduler:
        """End a pause. If a reminder became due while paused, wait one snooze, not zero."""

        next_due = self.next_due
        if next_due is None or next_due < now:
            next_due = now + self.snooze
        return replace(self, paused_until=None, next_due=next_due)

    def with_settings(self, interval_minutes: int, snooze_minutes: int, now: datetime) -> Scheduler:
        """Apply new intervals. A shorter interval pulls the next reminder in."""

        interval = timedelta(minutes=interval_minutes)
        next_due = self.next_due
        if next_due is not None and next_due > now + interval:
            next_due = now + interval
        return replace(
            self, interval=interval, snooze=timedelta(minutes=snooze_minutes), next_due=next_due
        )

    # --- persistence --------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "next_due": self.next_due.isoformat() if self.next_due else None,
            "paused_until": self.paused_until.isoformat() if self.paused_until else None,
        }

    def restore(self, raw: dict[str, Any]) -> Scheduler:
        """Restore saved timestamps onto a scheduler built from current settings."""

        return replace(
            self,
            next_due=_parse(raw.get("next_due")),
            paused_until=_parse(raw.get("paused_until")),
        )


def _parse(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
