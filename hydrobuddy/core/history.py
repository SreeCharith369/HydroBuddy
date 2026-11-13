"""Per-day hydration records: log a glass, undo, streaks, recent days."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from hydrobuddy.core import store
from hydrobuddy.core.day import day_key

FILE_NAME = "history.json"


@dataclass(frozen=True)
class DayRecord:
    day: date
    glasses: int
    goal: int

    @property
    def met_goal(self) -> bool:
        return self.glasses >= self.goal


class History:
    """In-memory history; ``to_dict``/``from_dict`` handle persistence."""

    def __init__(self, records: dict[date, DayRecord] | None = None) -> None:
        self._records: dict[date, DayRecord] = dict(records or {})

    # --- queries ------------------------------------------------------------
    def record(self, day: date, goal: int) -> DayRecord:
        """Return the record for ``day`` (zero glasses if nothing logged)."""

        return self._records.get(day, DayRecord(day, 0, goal))

    def today(self, now: datetime, day_start: time, goal: int) -> DayRecord:
        rec = self.record(day_key(now, day_start), goal)
        return DayRecord(rec.day, rec.glasses, goal)  # today always uses the current goal

    def recent(self, now: datetime, day_start: time, goal: int, days: int = 7) -> list[DayRecord]:
        """Oldest-first list of the last ``days`` days, with gaps filled as zero."""

        end = day_key(now, day_start)
        out = [self.record(end - timedelta(days=offset), goal) for offset in range(days - 1, 0, -1)]
        out.append(self.today(now, day_start, goal))
        return out

    def streak(self, now: datetime, day_start: time, goal: int) -> int:
        """Consecutive days meeting the goal, ending today (or yesterday if today isn't done)."""

        day = day_key(now, day_start)
        if not self.today(now, day_start, goal).met_goal:
            day -= timedelta(days=1)
        count = 0
        while self.record(day, goal).met_goal:
            count += 1
            day -= timedelta(days=1)
        return count

    # --- changes ------------------------------------------------------------
    def log_glass(self, now: datetime, day_start: time, goal: int) -> DayRecord:
        current = self.today(now, day_start, goal)
        updated = DayRecord(current.day, current.glasses + 1, goal)
        self._records[updated.day] = updated
        return updated

    def undo_glass(self, now: datetime, day_start: time, goal: int) -> DayRecord:
        current = self.today(now, day_start, goal)
        updated = DayRecord(current.day, max(0, current.glasses - 1), goal)
        self._records[updated.day] = updated
        return updated

    def prune(self, keep_from: date) -> int:
        """Drop records older than ``keep_from``; return how many were removed."""

        old = [day for day in self._records if day < keep_from]
        for day in old:
            del self._records[day]
        return len(old)

    # --- persistence --------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "days": {
                rec.day.isoformat(): {"glasses": rec.glasses, "goal": rec.goal}
                for rec in sorted(self._records.values(), key=lambda r: r.day)
            }
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> History:
        records: dict[date, DayRecord] = {}
        days = raw.get("days", {})
        if not isinstance(days, dict):
            return cls()
        for key, value in days.items():
            try:
                day = date.fromisoformat(key)
                glasses = max(0, int(value["glasses"]))
                goal = max(1, int(value["goal"]))
            except (TypeError, ValueError, KeyError):
                continue  # skip one bad day, keep the rest
            records[day] = DayRecord(day, glasses, goal)
        return cls(records)


def load_history(folder: Path | None = None) -> History:
    data = store.load((folder or store.data_dir()) / FILE_NAME)
    return History.from_dict(data or {})


def save_history(history: History, folder: Path | None = None) -> None:
    store.save((folder or store.data_dir()) / FILE_NAME, history.to_dict())
