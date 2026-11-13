"""Time source, so tests can control 'now'."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """Local wall-clock time (naive, the way the user reads their clock)."""

    def now(self) -> datetime:
        return datetime.now()
