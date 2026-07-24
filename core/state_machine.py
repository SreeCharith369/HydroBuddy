"""Reminder state machine for HydroBuddy."""

from enum import Enum

from utils.logger import logger


class ApplicationState(Enum):
    """Named states for the reminder flow."""

    IDLE = "idle"
    REMINDER_APPEARING = "reminder_appearing"
    WAITING_FOR_USER = "waiting_for_user"
    PROCESSING_DONE = "processing_done"
    PROCESSING_LATER = "processing_later"
    PROCESSING_IGNORE = "processing_ignore"
    EXITING = "exiting"


class ReminderStateMachine:
    """Small deterministic state machine for reminder interactions."""

    _VALID_TRANSITIONS: dict[ApplicationState, set[ApplicationState]] = {
        ApplicationState.IDLE: {
            ApplicationState.REMINDER_APPEARING,
            ApplicationState.EXITING,
        },
        ApplicationState.REMINDER_APPEARING: {
            ApplicationState.WAITING_FOR_USER,
            ApplicationState.EXITING,
        },
        ApplicationState.WAITING_FOR_USER: {
            ApplicationState.PROCESSING_DONE,
            ApplicationState.PROCESSING_LATER,
            ApplicationState.PROCESSING_IGNORE,
            ApplicationState.EXITING,
        },
        ApplicationState.PROCESSING_DONE: {ApplicationState.EXITING},
        ApplicationState.PROCESSING_LATER: {ApplicationState.EXITING},
        ApplicationState.PROCESSING_IGNORE: {ApplicationState.EXITING},
        ApplicationState.EXITING: {ApplicationState.IDLE},
    }

    def __init__(self) -> None:
        self._state = ApplicationState.IDLE
        logger.info("Application state initialized: %s", self._state.value)

    @property
    def state(self) -> ApplicationState:
        """Return the current reminder state."""

        return self._state

    def can_transition_to(self, next_state: ApplicationState) -> bool:
        """Return whether the requested state transition is allowed."""

        return next_state in self._VALID_TRANSITIONS[self._state]

    def transition_to(self, next_state: ApplicationState) -> bool:
        """Move to `next_state` when the transition is valid."""

        if not self.can_transition_to(next_state):
            logger.warning(
                "Invalid state transition prevented: %s -> %s",
                self._state.value,
                next_state.value,
            )
            return False

        previous_state = self._state
        self._state = next_state
        logger.info(
            "State transition: %s -> %s",
            previous_state.value,
            next_state.value,
        )
        return True
