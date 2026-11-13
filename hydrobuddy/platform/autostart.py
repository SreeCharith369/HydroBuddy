"""Start HydroBuddy when the user signs in to Windows (per-user Run key, no admin needed)."""

from __future__ import annotations

import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "HydroBuddy"


def launch_command() -> str:
    """The command Windows should run at sign-in."""

    if getattr(sys, "frozen", False):  # packaged .exe
        return f'"{sys.executable}"'
    python = Path(sys.executable)
    windowless = python.with_name("pythonw.exe")  # no console window
    script = Path(__file__).resolve().parents[2] / "run.pyw"
    return f'"{windowless if windowless.exists() else python}" "{script}"'


def registered_command(key_path: str = RUN_KEY) -> str | None:
    """The command currently registered, or None if autostart is off."""

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _kind = winreg.QueryValueEx(key, VALUE_NAME)
        return str(value)
    except FileNotFoundError:
        return None


def is_enabled(key_path: str = RUN_KEY) -> bool:
    return registered_command(key_path) is not None


def set_enabled(enabled: bool, key_path: str = RUN_KEY) -> None:
    import winreg

    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass


def refresh(key_path: str = RUN_KEY) -> bool:
    """If autostart is on but points at an old location (e.g. the app moved), fix it.

    Returns True if the entry was rewritten. Never turns autostart on by itself.
    """

    current = registered_command(key_path)
    if current is None or current == launch_command():
        return False
    set_enabled(True, key_path)
    return True
