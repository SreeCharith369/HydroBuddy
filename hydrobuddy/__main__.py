"""Entry point:  python -m hydrobuddy"""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from hydrobuddy.app import AppController
from hydrobuddy.core import store
from hydrobuddy.logs import setup_logging
from hydrobuddy.platform import autostart
from hydrobuddy.platform.single_instance import SingleInstance

log = logging.getLogger("hydrobuddy")


def _log_uncaught(kind, error, trace) -> None:
    """Without a console nobody sees a traceback, so put it in the log."""

    log.critical("Unexpected error", exc_info=(kind, error, trace))


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("HydroBuddy")
    app.setQuitOnLastWindowClosed(False)  # closing Settings/History must not quit the tray app

    folder = store.data_dir()
    setup_logging(folder)
    sys.excepthook = _log_uncaught

    instance = SingleInstance(folder)
    if not instance.acquire():
        log.info("Already running; asked it to show itself")
        return 0

    try:
        if autostart.refresh():
            log.info("Start-with-Windows entry updated to %s", autostart.launch_command())
    except OSError:
        log.exception("Could not check the start-with-Windows entry")

    controller = AppController(app)
    instance.activated.connect(controller.show_history)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
