"""Top-level application controller for the HydroBuddy shell."""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from core import constants
from core.reminder_manager import ReminderManager
from core.settings_manager import load_settings
from core.tracker import load_progress
from ui.reminder_window import ReminderWindow
from ui.settings_window import SettingsWindow
from ui.tray_manager import TrayManager
from utils.logger import configure_logging, logger
from utils.resources import resource_path


class AppController:
    """Coordinates the runnable shell and top-level managers."""

    def __init__(self) -> None:
        self.settings = load_settings()
        self.log = configure_logging()
        self.log.info("Application started")

        resource_path("assets/icons/icon.ico")

        self.app = QApplication(sys.argv)
        self.app.setApplicationName("HydroBuddy")
        self.app.setQuitOnLastWindowClosed(False)

        self.progress = load_progress()
        self.reminder_window = ReminderWindow(
            self.progress,
            on_water_drank=self._handle_water_clicked,
            on_snooze=self._handle_snooze_clicked,
        )
        self.reminder_manager = ReminderManager(
            show_reminder=self.reminder_window.show_with_fade,
            hide_reminder=self.reminder_window.hide_with_fade,
            on_hydration_increment=self._increment_hydration_placeholder,
            reminder_interval_minutes=constants.DEFAULT_REMINDER_INTERVAL,
        )
        self.settings_window = SettingsWindow()
        self.tray_manager = TrayManager(
            self.app,
            on_show_reminder=self.show_reminder,
            on_hide_reminder=self.hide_reminder,
            on_open_settings=self.open_settings,
            on_exit=self.exit_application,
        )

    def run(self) -> int:
        """Start the Qt event loop."""

        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available")

        self.tray_manager.show()
        self.reminder_manager.start()
        return self.app.exec()

    def show_reminder(self) -> None:
        """Show the reminder window manually from the tray."""

        self.reminder_manager.show_reminder_now()

    def hide_reminder(self) -> None:
        """Hide the reminder window manually from the tray."""

        self.reminder_manager.hide_current_reminder()

    def open_settings(self) -> None:
        """Open the settings dialog."""

        self.settings_window.reload()
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()
        logger.info("Settings opened")

    def exit_application(self) -> None:
        """Gracefully exit the shell."""

        logger.info("Application exited")
        self.reminder_manager.shutdown()
        self.tray_manager.hide()
        self.reminder_window.close()
        self.settings_window.close()
        QTimer.singleShot(0, self.app.quit)

    def _handle_water_clicked(self) -> None:
        self.reminder_manager.handle_done()

    def _handle_snooze_clicked(self) -> None:
        self.reminder_manager.handle_later()

    def _increment_hydration_placeholder(self) -> None:
        glasses = int(self.progress.get("glasses", 0)) + 1
        self.progress["glasses"] = glasses
        logger.info("Hydration count incremented in memory: glasses=%s", glasses)


def run_app() -> int:
    """Create and run the HydroBuddy shell."""

    controller = AppController()
    return controller.run()
