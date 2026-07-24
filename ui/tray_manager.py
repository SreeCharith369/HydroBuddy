"""Windows system tray manager for the HydroBuddy shell."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from ui import theme
from utils.resources import resource_path


class TrayManager:
    """Owns the system tray icon and shell actions."""

    def __init__(
        self,
        app: QApplication,
        on_show_reminder: Callable[[], None],
        on_hide_reminder: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        self._app = app
        self._tray_icon = QSystemTrayIcon(self._load_icon(), app)
        self._tray_icon.setToolTip("HydroBuddy")

        menu = QMenu()
        self.show_action = QAction("Show Reminder", menu)
        self.hide_action = QAction("Hide Reminder", menu)
        self.settings_action = QAction("Settings", menu)
        self.exit_action = QAction("Exit", menu)

        self.show_action.triggered.connect(on_show_reminder)
        self.hide_action.triggered.connect(on_hide_reminder)
        self.settings_action.triggered.connect(on_open_settings)
        self.exit_action.triggered.connect(on_exit)

        menu.addAction(self.show_action)
        menu.addAction(self.hide_action)
        menu.addSeparator()
        menu.addAction(self.settings_action)
        menu.addSeparator()
        menu.addAction(self.exit_action)

        self._tray_icon.setContextMenu(menu)

    def show(self) -> None:
        """Show the tray icon."""

        self._tray_icon.show()

    def hide(self) -> None:
        """Hide the tray icon."""

        self._tray_icon.hide()

    def _load_icon(self) -> QIcon:
        icon = QIcon(str(resource_path("assets/icons/icon.ico")))
        if not icon.isNull():
            return icon

        fallback = self._app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        if not fallback.isNull():
            return fallback

        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(theme.COLOR_BUTTON_PRIMARY))
        painter = QPainter(pixmap)
        painter.setPen(QColor(theme.COLOR_BUTTON_PRIMARY_TEXT))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "H")
        painter.end()
        return QIcon(pixmap)
