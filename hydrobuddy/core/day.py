"""The 'hydration day' boundary (default 02:00, so late nights count as yesterday)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta


def day_key(now: datetime, day_start: time) -> date:
    """Return which hydration day ``now`` belongs to.

    Uses local wall-clock time, so a DST jump (e.g. 02:00 -> 03:00) simply
    moves straight past the boundary; nothing is skipped or counted twice.
    """

    if now.time() < day_start:
        return now.date() - timedelta(days=1)
    return now.date()


def next_day_start(now: datetime, day_start: time) -> datetime:
    """Return the next moment a new hydration day begins."""

    today = datetime.combine(now.date(), day_start)
    return today if now < today else today + timedelta(days=1)
