"""Safe JSON storage in the user's data folder.

- Writes are atomic: data goes to a temp file, then replaces the real file.
- The previous good version is kept as ``<name>.bak``.
- A corrupt file is renamed ``<name>.corrupt`` (never silently thrown away),
  and the backup is used instead.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

APP_NAME = "HydroBuddy"


def data_dir() -> Path:
    """Return (and create) the folder where user data lives."""

    override = os.environ.get("HYDROBUDDY_DATA_DIR")
    if override:
        path = Path(override)
    else:
        base = os.environ.get("APPDATA") or str(Path.home() / ".config")
        path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object in {path.name}")
    return data


def load(path: Path) -> dict[str, Any] | None:
    """Load a JSON object; fall back to the backup; return None if neither works."""

    backup = path.with_name(path.name + ".bak")
    if path.exists():
        try:
            return _read(path)
        except (OSError, ValueError) as error:  # JSONDecodeError is a ValueError
            corrupt = path.with_name(path.name + ".corrupt")
            log.warning("Corrupt %s (%s); moved to %s", path.name, error, corrupt.name)
            os.replace(path, corrupt)

    if backup.exists():
        try:
            data = _read(backup)
            log.warning("Recovered %s from backup", path.name)
            return data
        except (OSError, ValueError) as error:
            log.warning("Backup for %s is also unreadable (%s)", path.name, error)

    return None


def save(path: Path, data: dict[str, Any]) -> None:
    """Atomically write a JSON object, keeping the previous version as a backup."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        if path.exists():
            os.replace(path, path.with_name(path.name + ".bak"))
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
