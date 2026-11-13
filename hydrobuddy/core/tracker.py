"""The app's brain: settings + history + scheduler, saved to disk on every change.

Because every change is written immediately (and atomically), a shutdown,
restart or crash at any moment loses nothing. On the next launch the tracker
picks up today's count and the pending reminder exactly where they were.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from hydrobuddy.core import store
from hydrobuddy.core.day import day_key, next_day_start
from hydrobuddy.core.history import DayRecord, load_history, save_history
from hydrobuddy.core.scheduler import Scheduler
from hydrobuddy.core.settings import Settings, load_settings, save_settings

log = logging.getLogger(__name__)

STATE_FILE = "state.json"
RETENTION_DAYS = 92  # about three months of daily records


class Tracker:
    def __init__(self, folder: Path | None = None) -> None:
        self.folder = folder or store.data_dir()
        self.settings = load_settings(self.folder)
        self.history = load_history(self.folder)
        saved = store.load(self.folder / STATE_FILE) or {}
        self.scheduler = Scheduler.create(
            self.settings.interval_minutes, self.settings.snooze_minutes
        ).restore(saved)

    # --- lifecycle ------------------------------------------------------------
    def start(self, now: datetime) -> None:
        """Call once at launch: resume the schedule and drop records older than 3 months."""

        self.scheduler = self.scheduler.start(now)
        self._save_state()
        if self._prune(now):
            save_history(self.history, self.folder)

    # --- queries --------------------------------------------------------------
    def today(self, now: datetime) -> DayRecord:
        return self.history.today(now, self.settings.day_start_time, self.settings.daily_goal)

    def recent(self, now: datetime, days: int = RETENTION_DAYS) -> list[DayRecord]:
        return self.history.recent(
            now, self.settings.day_start_time, self.settings.daily_goal, days
        )

    def streak(self, now: datetime) -> int:
        return self.history.streak(now, self.settings.day_start_time, self.settings.daily_goal)

    def is_due(self, now: datetime) -> bool:
        return self.scheduler.is_due(now)

    def is_paused(self, now: datetime) -> bool:
        return self.scheduler.is_paused(now)

    # --- drinking -------------------------------------------------------------
    def drink(self, now: datetime) -> DayRecord:
        """Log one glass and restart the reminder interval."""

        record = self.history.log_glass(now, self.settings.day_start_time, self.settings.daily_goal)
        self._prune(now)
        save_history(self.history, self.folder)
        self.scheduler = self.scheduler.on_done(now)
        self._save_state()
        log.info("Glass logged: %s/%s on %s", record.glasses, record.goal, record.day)
        return record

    def undo(self, now: datetime) -> DayRecord:
        record = self.history.undo_glass(
            now, self.settings.day_start_time, self.settings.daily_goal
        )
        save_history(self.history, self.folder)
        log.info("Glass removed: %s/%s on %s", record.glasses, record.goal, record.day)
        return record

    # --- reminders ------------------------------------------------------------
    def reminder_shown(self, now: datetime) -> None:
        self.scheduler = self.scheduler.mark_shown(now)

    def snooze(self, now: datetime) -> None:
        self.scheduler = self.scheduler.on_snooze(now)
        self._save_state()

    def skip(self, now: datetime) -> None:
        self.scheduler = self.scheduler.on_skip(now)
        self._save_state()

    def pause_for(self, now: datetime, minutes: int) -> None:
        self.scheduler = self.scheduler.pause(now + timedelta(minutes=minutes))
        self._save_state()

    def pause_until_tomorrow(self, now: datetime) -> None:
        self.scheduler = self.scheduler.pause(next_day_start(now, self.settings.day_start_time))
        self._save_state()

    def resume(self, now: datetime) -> None:
        self.scheduler = self.scheduler.resume(now)
        self._save_state()

    # --- settings -------------------------------------------------------------
    def update_settings(self, settings: Settings, now: datetime) -> None:
        self.settings = settings
        save_settings(settings, self.folder)
        self.scheduler = self.scheduler.with_settings(
            settings.interval_minutes, settings.snooze_minutes, now
        )
        self._save_state()
        log.info("Settings saved: %s", settings.to_dict())

    # --- internals ------------------------------------------------------------
    def _prune(self, now: datetime) -> int:
        today = day_key(now, self.settings.day_start_time)
        return self.history.prune(today - timedelta(days=RETENTION_DAYS - 1))

    def _save_state(self) -> None:
        store.save(self.folder / STATE_FILE, self.scheduler.to_dict())
