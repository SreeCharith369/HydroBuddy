"""Reminder-flow coordinator for HydroBuddy."""

from __future__ import annotations

from collections.abc import Callable

from core import constants
from core.reminder_scheduler import ReminderScheduler, ReminderTimerKind
from core.state_machine import ApplicationState, ReminderStateMachine
from utils.logger import logger


class ReminderManager:
    """Coordinates reminder timing, state transitions, and UI callbacks."""

    def __init__(
        self,
        show_reminder: Callable[[], None],
        hide_reminder: Callable[[], None],
        on_hydration_increment: Callable[[], None] | None = None,
        reminder_interval_minutes: int = constants.DEFAULT_REMINDER_INTERVAL,
    ) -> None:
        self._show_reminder = show_reminder
        self._hide_reminder = hide_reminder
        self._on_hydration_increment = on_hydration_increment or (lambda: None)
        self._reminder_interval_minutes = reminder_interval_minutes
        self._state_machine = ReminderStateMachine()
        self._scheduler = ReminderScheduler(self._handle_timer_expired)
        self._is_shutdown = False

    @property
    def state(self) -> ApplicationState:
        """Return the current reminder state."""

        return self._state_machine.state

    @property
    def scheduler(self) -> ReminderScheduler:
        """Return the scheduler for diagnostics and future tests."""

        return self._scheduler

    def start(self) -> None:
        """Start the reminder engine."""

        self._run_safely("start reminder manager", self._start)

    def show_reminder_now(self) -> None:
        """Trigger the reminder flow immediately."""

        self._run_safely("show reminder now", self._show_reminder_now)

    def handle_done(self) -> None:
        """Handle the user confirming that they drank water."""

        self._run_safely("handle done", self._handle_done)

    def handle_later(self) -> None:
        """Handle the user asking to be reminded later."""

        self._run_safely("handle later", self._handle_later)

    def hide_current_reminder(self) -> None:
        """Hide the active reminder and restart the normal reminder timer."""

        self._run_safely("hide current reminder", self._hide_current_reminder)

    def shutdown(self) -> None:
        """Clean up reminder resources before application exit."""

        self._run_safely("shutdown reminder manager", self._shutdown)

    def enter_animation_started(self) -> None:
        """Placeholder for the future enter animation."""

        logger.info("Placeholder enter animation started")

    def drink_animation_started(self) -> None:
        """Placeholder for the future drink animation."""

        logger.info("Placeholder drink animation started")

    def disappointed_animation_started(self) -> None:
        """Placeholder for the future disappointed animation."""

        logger.info("Placeholder disappointed animation started")

    def exit_animation_started(self) -> None:
        """Placeholder for the future exit animation."""

        logger.info("Placeholder exit animation started")

    def _start(self) -> None:
        if self._is_shutdown:
            logger.warning("Reminder manager start ignored after shutdown")
            return

        self._scheduler.reset_reminder_timer(self._reminder_interval_minutes)
        logger.info("Reminder manager started")

    def _show_reminder_now(self) -> None:
        if self._is_shutdown:
            logger.warning("Manual reminder ignored after shutdown")
            return

        if self.state is not ApplicationState.IDLE:
            logger.warning("Manual reminder ignored while state=%s", self.state.value)
            return

        self._scheduler.cancel()
        self._begin_reminder_flow()

    def _handle_done(self) -> None:
        if self.state is not ApplicationState.WAITING_FOR_USER:
            logger.warning("Done ignored while state=%s", self.state.value)
            return

        logger.info("Done pressed")
        self._scheduler.cancel()
        if not self._state_machine.transition_to(ApplicationState.PROCESSING_DONE):
            return

        try:
            self._on_hydration_increment()
        except Exception:
            logger.exception("Error during placeholder hydration increment")
        logger.info("Placeholder hydration increment triggered")
        self.drink_animation_started()
        self._finish_reminder(schedule_snooze=False)

    def _handle_later(self) -> None:
        if self.state is not ApplicationState.WAITING_FOR_USER:
            logger.warning("Later ignored while state=%s", self.state.value)
            return

        logger.info("Later pressed")
        self._scheduler.cancel()
        if not self._state_machine.transition_to(ApplicationState.PROCESSING_LATER):
            return

        self._finish_reminder(schedule_snooze=True)

    def _hide_current_reminder(self) -> None:
        if self.state is ApplicationState.IDLE:
            self._hide_window()
            logger.info("Manual hide requested while reminder was idle")
            return

        self._scheduler.cancel()
        if self.state in {
            ApplicationState.REMINDER_APPEARING,
            ApplicationState.WAITING_FOR_USER,
        }:
            self._state_machine.transition_to(ApplicationState.EXITING)
        elif self.state is not ApplicationState.EXITING:
            logger.warning("Manual hide requested while state=%s", self.state.value)
            return

        self.exit_animation_started()
        self._hide_window()
        self._scheduler.reset_reminder_timer(self._reminder_interval_minutes)
        self._state_machine.transition_to(ApplicationState.IDLE)

    def _shutdown(self) -> None:
        self._is_shutdown = True
        self._scheduler.cleanup()

        if self.state is not ApplicationState.IDLE:
            self._state_machine.transition_to(ApplicationState.EXITING)
        self._hide_window()
        logger.info("Reminder manager shut down")

    def _handle_timer_expired(self, kind: ReminderTimerKind) -> None:
        if self._is_shutdown:
            logger.warning("Timer timeout ignored after shutdown: %s", kind.value)
            return

        if kind in {ReminderTimerKind.REMINDER, ReminderTimerKind.SNOOZE}:
            self._begin_reminder_flow()
            return

        if kind is ReminderTimerKind.IGNORE_TIMEOUT:
            self._handle_ignore_timeout()

    def _begin_reminder_flow(self) -> None:
        if self.state is not ApplicationState.IDLE:
            logger.warning("Reminder trigger ignored while state=%s", self.state.value)
            return

        if not self._state_machine.transition_to(ApplicationState.REMINDER_APPEARING):
            return

        if not self._show_window():
            if self._state_machine.transition_to(ApplicationState.EXITING):
                self._scheduler.reset_reminder_timer(self._reminder_interval_minutes)
                self._state_machine.transition_to(ApplicationState.IDLE)
            return

        self.enter_animation_started()
        if self._state_machine.transition_to(ApplicationState.WAITING_FOR_USER):
            self._scheduler.schedule_ignore_timeout()

    def _handle_ignore_timeout(self) -> None:
        if self.state is not ApplicationState.WAITING_FOR_USER:
            logger.warning("Ignore timeout ignored while state=%s", self.state.value)
            return

        logger.info("Ignore timeout reached")
        if not self._state_machine.transition_to(ApplicationState.PROCESSING_IGNORE):
            return

        self.disappointed_animation_started()
        self._finish_reminder(schedule_snooze=True)

    def _finish_reminder(self, schedule_snooze: bool) -> None:
        if not self._state_machine.transition_to(ApplicationState.EXITING):
            return

        self.exit_animation_started()
        self._hide_window()

        if schedule_snooze:
            self._scheduler.schedule_snooze(constants.DEFAULT_SNOOZE_INTERVAL)
        else:
            self._scheduler.reset_reminder_timer(self._reminder_interval_minutes)

        self._state_machine.transition_to(ApplicationState.IDLE)

    def _show_window(self) -> bool:
        try:
            self._show_reminder()
            logger.info("Reminder shown")
            return True
        except Exception:
            logger.exception("Error while showing reminder")
            return False

    def _hide_window(self) -> None:
        try:
            self._hide_reminder()
            logger.info("Reminder hidden")
        except Exception:
            logger.exception("Error while hiding reminder")

    @staticmethod
    def _run_safely(action: str, callback: Callable[[], None]) -> None:
        try:
            callback()
        except Exception:
            logger.exception("Unexpected error during %s", action)
