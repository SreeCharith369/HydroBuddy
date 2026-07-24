"""Application event names for HydroBuddy.

Events describe future communication between core modules and UI modules. This
file intentionally does not define an event dispatcher or event handling logic.
"""

from enum import Enum


class ApplicationEvent(Enum):
    """Named events reserved for future app coordination."""

    REMINDER_TRIGGERED = "ReminderTriggered"
    WATER_DRANK = "WaterDrank"
    SNOOZED = "Snoozed"
    ANIMATION_FINISHED = "AnimationFinished"
    REMINDER_DISMISSED = "ReminderDismissed"
    SETTINGS_CHANGED = "SettingsChanged"
    DAY_RESET = "DayReset"
