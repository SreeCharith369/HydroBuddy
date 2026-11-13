"""Rotating log file in the user's data folder."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(folder: Path) -> None:
    log_dir = folder / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "hydrobuddy.log", maxBytes=500_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger("hydrobuddy")
    root.setLevel(logging.INFO)
    root.addHandler(handler)
