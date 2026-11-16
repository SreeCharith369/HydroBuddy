"""Entry point:  python -m hydrobuddy"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from hydrobuddy.app import AppController
from hydrobuddy.core import store
from hydrobuddy.logs import setup_logging
from hydrobuddy.platform import autostart
from hydrobuddy.platform.single_instance import SingleInstance

log = logging.getLogger("hydrobuddy")

QUIT_FLAG = "--quit"


def _log_uncaught(kind, error, trace) -> None:
    """Without a console nobody sees a traceback, so put it in the log."""

    log.critical("Unexpected error", exc_info=(kind, error, trace))


def _show_error(text: str) -> None:
    """A plain Windows message box; works even if Qt itself is what failed."""

    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, "HydroBuddy", 0x10)  # MB_ICONERROR


def _run(argv: list[str]) -> int:
    app = QApplication(argv)
    app.setApplicationName("HydroBuddy")
    app.setQuitOnLastWindowClosed(False)  # closing Settings/History must not quit the tray app

    folder = store.data_dir()
    setup_logging(folder)
    sys.excepthook = _log_uncaught

    instance = SingleInstance(folder)
    if QUIT_FLAG in argv:  # "HydroBuddy.exe --quit" closes the running copy
        instance.send("quit")
        return 0
    if not instance.acquire():
        log.info("Already running; asked it to show itself")
        return 0

    log.info(
        "Launched%s: %s",
        " by Windows sign-in" if autostart.AUTOSTART_FLAG in argv else "",
        sys.executable if getattr(sys, "frozen", False) else Path(__file__).resolve().parent,
    )
    try:
        if autostart.refresh():
            log.info("Start-with-Windows entry updated to %s", autostart.launch_command())
    except OSError:
        log.exception("Could not check the start-with-Windows entry")

    controller = AppController(app)
    instance.activated.connect(controller.show_history)
    instance.quit_requested.connect(controller.quit)
    if autostart.AUTOSTART_FLAG not in argv:
        controller.announce()  # a tray app shows no window, so say that it started
    return app.exec()


def main() -> int:
    """Run the app. A failure to start is logged and shown, never silent."""

    try:
        return _run(sys.argv)
    except Exception as error:
        log.critical("HydroBuddy could not start", exc_info=True)
        _show_error(
            f"HydroBuddy could not start:\n\n{type(error).__name__}: {error}\n\n"
            "Details are in %APPDATA%\\HydroBuddy\\logs\\hydrobuddy.log"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
