"""Is the user in the middle of something that a popup would interrupt?

Two independent signals, because neither is reliable on every Windows build:

1. Windows' own answer (SHQueryUserNotificationState), the signal Windows uses
   to hold back its notifications. On some systems it returns an undocumented
   0, so it is only trusted for the values it documents.
2. A direct check: does the window in front cover its whole monitor? Is the
   screen locked (the input desktop can't be opened)?
"""

from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)

# QUERY_USER_NOTIFICATION_STATE values
NOT_PRESENT = 1  # screensaver running, screen locked, or another user is active
BUSY = 2  # a fullscreen app is in front
D3D_FULLSCREEN = 3  # a fullscreen game (Direct3D exclusive mode)
PRESENTATION = 4  # presentation mode
ACCEPTS_NOTIFICATIONS = 5
QUIET_TIME = 6  # Windows' quiet period right after first sign-in
APP = 7  # a Windows Store app is fullscreen

FULLSCREEN_STATES = {BUSY, D3D_FULLSCREEN, PRESENTATION, APP}

_WS_CAPTION = 0x00C00000  # title bar

# Windows that cover the screen but are not "an app in fullscreen".
_SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}


def notification_state() -> int:
    """Return Windows' notification state (0 or ACCEPTS_NOTIFICATIONS if unknown)."""

    if sys.platform != "win32":
        return ACCEPTS_NOTIFICATIONS
    import ctypes

    state = ctypes.c_int(0)
    try:
        result = ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
    except (AttributeError, OSError):
        return ACCEPTS_NOTIFICATIONS
    return state.value if result == 0 else ACCEPTS_NOTIFICATIONS


def foreground_is_fullscreen() -> bool:
    """Whether the window in front exactly covers its monitor (videos, games, slides)."""

    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False
    name = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, name, 64)
    if name.value in _SHELL_CLASSES:
        return False
    # A maximized window with a title bar is ordinary work, even when it covers the
    # whole monitor (which happens when the taskbar is set to auto-hide).
    user32.GetWindowLongW.restype = ctypes.c_long
    style = user32.GetWindowLongW(hwnd, -16)  # GWL_STYLE
    if user32.IsZoomed(hwnd) and style & _WS_CAPTION == _WS_CAPTION:
        return False

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    window = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(window)):
        return False
    monitor = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return False
    m = info.rcMonitor
    return (
        window.left <= m.left
        and window.top <= m.top
        and window.right >= m.right
        and window.bottom >= m.bottom
    )


def screen_locked() -> bool:
    """Whether the workstation is locked (the user's desktop isn't the input desktop)."""

    if sys.platform != "win32":
        return False
    import ctypes

    user32 = ctypes.windll.user32
    desktop = user32.OpenInputDesktop(0, False, 0x0100)  # DESKTOP_SWITCHDESKTOP
    if not desktop:
        return True
    user32.CloseDesktop(desktop)
    return False


def is_away() -> bool:
    """Screen locked or screensaver on: nobody is there to see a reminder."""

    return notification_state() == NOT_PRESENT or screen_locked()


def is_fullscreen() -> bool:
    """A fullscreen app, game, video or presentation is in front."""

    return notification_state() in FULLSCREEN_STATES or foreground_is_fullscreen()
