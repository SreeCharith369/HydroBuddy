"""User settings: only options the app actually implements."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import time
from pathlib import Path
from typing import Any

from hydrobuddy.core import store

FILE_NAME = "settings.json"

# Allowed (min, max) for each numeric setting.
LIMITS = {
    "interval_minutes": (5, 240),
    "snooze_minutes": (1, 60),
    "daily_goal": (1, 30),
}


@dataclass(frozen=True)
class Settings:
    interval_minutes: int = 60
    snooze_minutes: int = 10
    daily_goal: int = 8
    day_start: str = "02:00"  # local time when a new hydration day begins

    @property
    def day_start_time(self) -> time:
        return time.fromisoformat(self.day_start)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Settings:
        """Build settings from untrusted data; bad values fall back to defaults."""

        defaults = cls()
        values: dict[str, Any] = {}
        for f in fields(cls):
            default = getattr(defaults, f.name)
            value = raw.get(f.name, default)
            if f.name in LIMITS:
                values[f.name] = _int_in_range(value, default, *LIMITS[f.name])
            elif f.name == "day_start":
                values[f.name] = _valid_time(value, default)
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _int_in_range(value: Any, default: int, low: int, high: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if low <= number <= high else default


def _valid_time(value: Any, default: str) -> str:
    """Accept 'H:MM' or 'HH:MM' and normalise to 'HH:MM'."""

    try:
        hour, minute = (int(part) for part in str(value).split(":"))
        return time(hour, minute).strftime("%H:%M")
    except ValueError:
        return default


def load_settings(folder: Path | None = None) -> Settings:
    data = store.load((folder or store.data_dir()) / FILE_NAME)
    return Settings.from_dict(data or {})


def save_settings(settings: Settings, folder: Path | None = None) -> None:
    store.save((folder or store.data_dir()) / FILE_NAME, settings.to_dict())
