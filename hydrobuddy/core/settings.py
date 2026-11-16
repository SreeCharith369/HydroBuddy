"""User settings: only options the app actually implements."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime, time
from pathlib import Path
from typing import Any

from hydrobuddy.core import store

FILE_NAME = "settings.json"

# Allowed (min, max) for each numeric setting.
LIMITS = {
    "interval_minutes": (5, 240),
    "snooze_minutes": (1, 60),
    "daily_goal": (1, 30),
    "done_cooldown_seconds": (0, 120),
    "snooze_cooldown_seconds": (0, 60),
}
TIME_FIELDS = ("day_start", "quiet_start", "quiet_end")
BOOL_FIELDS = ("quiet_hours", "skip_when_fullscreen", "block_screen")


@dataclass(frozen=True)
class Settings:
    interval_minutes: int = 60
    snooze_minutes: int = 10
    daily_goal: int = 8
    day_start: str = "02:00"  # local time when a new hydration day begins
    quiet_hours: bool = False  # no reminders between quiet_start and quiet_end
    quiet_start: str = "23:00"
    quiet_end: str = "08:00"
    skip_when_fullscreen: bool = True  # wait while a fullscreen app, game or slideshow runs
    done_cooldown_seconds: int = 30  # Done stays locked this long: time to actually drink
    snooze_cooldown_seconds: int = 7  # Snooze stays locked this long
    block_screen: bool = False  # dim the whole screen and block clicks until answered

    @property
    def day_start_time(self) -> time:
        return time.fromisoformat(self.day_start)

    def in_quiet_hours(self, now: datetime) -> bool:
        """Whether ``now`` falls in the quiet window (which may wrap past midnight)."""

        if not self.quiet_hours:
            return False
        start, end, current = (
            time.fromisoformat(self.quiet_start),
            time.fromisoformat(self.quiet_end),
            now.time(),
        )
        if start == end:
            return False
        if start < end:
            return start <= current < end
        return current >= start or current < end

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
            elif f.name in TIME_FIELDS:
                values[f.name] = _valid_time(value, default)
            elif f.name in BOOL_FIELDS:
                values[f.name] = value if isinstance(value, bool) else default
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
