"""Wires the tracker to the tray icon, the reminder popup and the dialogs."""

from __future__ import annotations

import logging
import random
from typing import Protocol

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from hydrobuddy.core.clock import Clock, SystemClock
from hydrobuddy.core.settings import Settings
from hydrobuddy.core.tracker import Tracker
from hydrobuddy.platform import autostart, focus
from hydrobuddy.ui.character import character_icon
from hydrobuddy.ui.history_window import HistoryWindow
from hydrobuddy.ui.popup import ReminderPopup
from hydrobuddy.ui.settings_dialog import SettingsDialog

log = logging.getLogger(__name__)

TICK_MS = 15_000  # how often to check the clock; reminders are timestamp-based

REMINDERS = (
    "Water break! Grab a glass 💧",
    "Time for a sip 💧",
    "Your glass is calling 💧",
    "Pause for some water 💧",
    "Drink some water with me 💧",
    "Quick hydration check 💧",
)
CHEERS = (
    "Nice! Small sip, big win 🎉",
    "Great job! 🎉",
    "Your body says thanks 🎉",
    "One glass closer 🎉",
    "Refreshing! 🎉",
)
GOAL_REACHED = "Goal reached! Amazing 🏆"


class FocusCheck(Protocol):
    """What the app asks before interrupting (``hydrobuddy.platform.focus`` fits)."""

    def is_away(self) -> bool: ...

    def is_fullscreen(self) -> bool: ...


class AppController(QObject):
    def __init__(
        self,
        app: QApplication,
        tracker: Tracker | None = None,
        clock: Clock | None = None,
        focus_check: FocusCheck = focus,
        tick_ms: int = TICK_MS,
    ) -> None:
        super().__init__()
        self.app = app
        self.clock = clock or SystemClock()
        self.focus = focus_check
        self.tracker = tracker or Tracker()
        self.tracker.start(self.clock.now())

        self.popup = ReminderPopup()
        self.popup.done.connect(self.log_glass)
        self.popup.snoozed.connect(self._on_snoozed)
        self.popup.ignored.connect(self._on_ignored)
        self.history_window = HistoryWindow()

        self.tray = QSystemTrayIcon(QIcon(character_icon(64)), self)
        self.menu = self._build_menu()
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(tick_ms)
        self.tick()
        log.info("HydroBuddy started; next reminder at %s", self.tracker.scheduler.next_due)

    # --- tray menu --------------------------------------------------------------
    def _build_menu(self) -> QMenu:
        menu = QMenu()
        self.status_action = QAction(menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        self.next_action = QAction(menu)
        self.next_action.setEnabled(False)
        menu.addAction(self.next_action)
        menu.addSeparator()
        menu.addAction("Log a glass", self.log_glass)
        self.undo_action = menu.addAction("Undo last glass", self.undo_glass)
        menu.addAction("Remind me now", self.show_reminder)
        menu.addSeparator()

        self.pause_menu = menu.addMenu("Pause reminders")
        for label, minutes in (("30 minutes", 30), ("1 hour", 60), ("2 hours", 120)):
            self.pause_menu.addAction(f"For {label}", lambda m=minutes: self.pause(m))
        self.pause_menu.addAction("Until tomorrow", self.pause_until_tomorrow)
        self.resume_action = menu.addAction("Resume reminders", self.resume)

        menu.addSeparator()
        menu.addAction("History…", self.show_history)
        menu.addAction("Settings…", self.show_settings)
        menu.addSeparator()
        menu.addAction("Quit HydroBuddy", self.quit)
        menu.aboutToShow.connect(self.refresh)
        return menu

    def refresh(self) -> None:
        """Update the tray tooltip and menu text (also how the count rolls over at 2 AM)."""

        now = self.clock.now()
        today = self.tracker.today(now)
        status = f"{today.glasses} of {today.goal} glasses today"
        paused = self.tracker.is_paused(now)
        next_due = self.tracker.scheduler.next_due
        if paused:
            next_text = f"Paused until {self.tracker.scheduler.paused_until:%H:%M}"
        elif self.tracker.settings.in_quiet_hours(now):
            next_text = f"Quiet hours until {self.tracker.settings.quiet_end}"
        elif next_due is not None and next_due > now:
            next_text = f"Next reminder at {next_due:%H:%M}"
        else:
            next_text = "Reminder due now"
        self.status_action.setText(status)
        self.next_action.setText(next_text)
        self.tray.setToolTip(f"HydroBuddy\n{status}\n{next_text}")
        self.undo_action.setEnabled(today.glasses > 0)
        self.pause_menu.menuAction().setVisible(not paused)
        self.resume_action.setVisible(paused)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # left click
            self.show_history()

    # --- the clock ----------------------------------------------------------------
    def tick(self) -> None:
        now = self.clock.now()
        self.refresh()
        if not self.tracker.is_due(now) or self.popup.active:
            return
        if self.focus.is_away():
            return  # screen locked: wait until the user is back
        settings = self.tracker.settings
        if settings.skip_when_fullscreen and self.focus.is_fullscreen():
            return  # don't interrupt a game, video or presentation; try again next tick
        if settings.in_quiet_hours(now):
            return
        self.show_reminder()

    # --- reminders ----------------------------------------------------------------
    def show_reminder(self) -> None:
        now = self.clock.now()
        if self.popup.remind(random.choice(REMINDERS), self.tracker.today(now)):
            self.tracker.reminder_shown(now)
            log.info("Reminder shown")

    def _on_snoozed(self) -> None:
        self.tracker.snooze(self.clock.now())
        minutes = self.tracker.settings.snooze_minutes
        self.popup.sadden(f"Okay… I'll be back in {minutes} minutes.")
        log.info("Reminder snoozed")

    def _on_ignored(self) -> None:
        self.tracker.skip(self.clock.now())
        self.popup.sadden("Busy? I'll check on you later.")
        log.info("Reminder ignored")

    # --- actions ------------------------------------------------------------------
    def log_glass(self) -> None:
        record = self.tracker.drink(self.clock.now())
        just_reached = record.glasses == record.goal
        self.popup.cheer(GOAL_REACHED if just_reached else random.choice(CHEERS), record)
        self.refresh()

    def undo_glass(self) -> None:
        self.tracker.undo(self.clock.now())
        self.refresh()

    def pause(self, minutes: int) -> None:
        self.tracker.pause_for(self.clock.now(), minutes)
        self.refresh()

    def pause_until_tomorrow(self) -> None:
        self.tracker.pause_until_tomorrow(self.clock.now())
        self.refresh()

    def resume(self) -> None:
        self.tracker.resume(self.clock.now())
        self.refresh()

    def show_history(self) -> None:
        now = self.clock.now()
        self.history_window.show_records(self.tracker.recent(now), self.tracker.streak(now))

    def show_settings(self) -> None:
        dialog = SettingsDialog(self.tracker.settings, autostart.is_enabled())
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            self.apply_settings(dialog.settings(), dialog.autostart_enabled())

    def apply_settings(self, settings: Settings, start_with_windows: bool) -> None:
        self.tracker.update_settings(settings, self.clock.now())
        if start_with_windows != autostart.is_enabled():
            autostart.set_enabled(start_with_windows)
            log.info("Start with Windows: %s", start_with_windows)
        self.refresh()

    def quit(self) -> None:
        log.info("HydroBuddy quit")
        self.timer.stop()
        self.popup.dismiss()
        self.history_window.close()
        self.tray.hide()
        self.app.quit()
