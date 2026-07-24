"""Progress loading for the HydroBuddy shell.

This milestone reads progress for display only. It does not update hydration
counts or perform daily reset behavior.
"""

from __future__ import annotations

from typing import Any

from core.constants import DEFAULT_DAILY_GOAL
from core.storage import load_json
from utils.resources import resource_path

PROGRESS_PATH = resource_path("data/progress.json")


def load_progress() -> dict[str, Any]:
    """Load progress values for display in the reminder window."""

    progress = {"date": "", "glasses": 0, "goal": DEFAULT_DAILY_GOAL}
    progress.update(load_json(PROGRESS_PATH))
    return progress
