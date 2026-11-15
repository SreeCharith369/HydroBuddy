"""Starting the real app: a double-click must work, and a failure must never be silent."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import hydrobuddy.__main__ as entry
from hydrobuddy.platform import autostart

ROOT = Path(__file__).resolve().parents[1]
RUN_PYW = ROOT / "run.pyw"
SYSTEM_PYTHON = Path(sys.base_prefix) / "python.exe"  # what Windows uses for a double-click

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")


def _has_pyside(python: Path) -> bool:
    return (
        subprocess.run([str(python), "-c", "import PySide6"], capture_output=True).returncode == 0
    )


def _wait_for_log(folder: Path, text: str, seconds: float = 20) -> str:
    log = folder / "logs" / "hydrobuddy.log"
    deadline = time.time() + seconds
    while time.time() < deadline:
        if log.exists() and text in log.read_text(encoding="utf-8"):
            return log.read_text(encoding="utf-8")
        time.sleep(0.2)
    raise AssertionError(f"{text!r} never appeared in {log}")


@pytest.mark.skipif(
    not SYSTEM_PYTHON.exists() or sys.prefix == sys.base_prefix or _has_pyside(SYSTEM_PYTHON),
    reason="needs a system Python without PySide6 and a venv with it",
)
def test_double_click_with_the_wrong_python_still_starts_the_app(isolated_data_dir):
    """Double-clicking run.pyw uses the system Python, which lacks the app's libraries."""

    env = {**os.environ, "HYDROBUDDY_DATA_DIR": str(isolated_data_dir)}
    env.pop("VIRTUAL_ENV", None)
    launched = subprocess.run([str(SYSTEM_PYTHON), str(RUN_PYW)], env=env, capture_output=True)
    assert launched.returncode == 0, launched.stderr.decode()
    try:
        _wait_for_log(isolated_data_dir, "HydroBuddy started")  # it handed over to .venv
    finally:
        subprocess.run([sys.executable, "-m", "hydrobuddy", "--quit"], env=env, cwd=ROOT)
    _wait_for_log(isolated_data_dir, "HydroBuddy quit")


def test_quit_flag_with_nothing_running_is_harmless(isolated_data_dir):
    env = {**os.environ, "HYDROBUDDY_DATA_DIR": str(isolated_data_dir)}
    done = subprocess.run(
        [sys.executable, "-m", "hydrobuddy", "--quit"], env=env, cwd=ROOT, timeout=30
    )
    assert done.returncode == 0


def test_a_startup_failure_is_shown_and_logged_not_silent(monkeypatch, caplog):
    shown = []

    def broken(_argv):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(entry, "_run", broken)
    monkeypatch.setattr(entry, "_show_error", shown.append)
    assert entry.main() == 1
    assert len(shown) == 1 and "disk on fire" in shown[0]
    assert "HydroBuddy could not start" in caplog.text


def test_autostart_command_marks_itself_so_the_app_starts_quietly():
    assert autostart.launch_command().endswith(autostart.AUTOSTART_FLAG)
