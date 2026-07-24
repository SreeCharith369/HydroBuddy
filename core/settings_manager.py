"""Settings manager for the HydroBuddy shell."""

from __future__ import annotations

from typing import Any

from core import constants
from core.storage import load_json, save_json
from utils.resources import resource_path

SETTINGS_PATH = resource_path("data/settings.json")

DEFAULT_SETTINGS: dict[str, Any] = {
    "reminder_interval": constants.DEFAULT_REMINDER_INTERVAL,
    "snooze_interval": constants.DEFAULT_SNOOZE_INTERVAL,
    "daily_goal": constants.DEFAULT_DAILY_GOAL,
    "daily_reset_time": constants.DEFAULT_RESET_TIME,
    "start_with_windows": constants.DEFAULT_START_WITH_WINDOWS,
    "pause_during_fullscreen": constants.DEFAULT_PAUSE_DURING_FULLSCREEN,
    "primary_monitor_only": constants.DEFAULT_PRIMARY_MONITOR_ONLY,
    "silent_mode": constants.DEFAULT_SILENT_MODE,
}


def load_settings() -> dict[str, Any]:
    """Load settings and fill any missing keys from defaults."""

    settings = DEFAULT_SETTINGS.copy()
    settings.update(load_json(SETTINGS_PATH))
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    """Persist settings for the current shell."""

    normalized = DEFAULT_SETTINGS.copy()
    normalized.update(settings)
    save_json(SETTINGS_PATH, normalized)
