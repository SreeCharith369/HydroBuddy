"""Settings dialog. Every option here changes real behaviour."""

from __future__ import annotations

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from hydrobuddy.core.settings import LIMITS, Settings


def _spin(name: str, value: int, suffix: str) -> QSpinBox:
    box = QSpinBox()
    box.setRange(*LIMITS[name])
    box.setValue(value)
    box.setSuffix(suffix)
    return box


def _time(value: str) -> QTimeEdit:
    edit = QTimeEdit(QTime.fromString(value, "HH:mm"))
    edit.setDisplayFormat("HH:mm")
    return edit


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("color: gray;")
    label.setWordWrap(True)
    return label


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, autostart: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("HydroBuddy settings")
        self.setMinimumWidth(380)

        self.interval = _spin("interval_minutes", settings.interval_minutes, " minutes")
        self.snooze = _spin("snooze_minutes", settings.snooze_minutes, " minutes")
        self.goal = _spin("daily_goal", settings.daily_goal, " glasses")
        self.day_start = _time(settings.day_start)

        self.quiet = QCheckBox("Quiet hours from")
        self.quiet.setChecked(settings.quiet_hours)
        self.quiet_start = _time(settings.quiet_start)
        self.quiet_end = _time(settings.quiet_end)
        self.quiet.toggled.connect(self._sync_quiet)
        self._sync_quiet(settings.quiet_hours)
        quiet_row = QHBoxLayout()
        quiet_row.addWidget(self.quiet)
        quiet_row.addWidget(self.quiet_start)
        quiet_row.addWidget(QLabel("to"))
        quiet_row.addWidget(self.quiet_end)
        quiet_row.addStretch()

        self.fullscreen = QCheckBox("Wait while a fullscreen app, game or slideshow is open")
        self.fullscreen.setChecked(settings.skip_when_fullscreen)
        self.autostart = QCheckBox("Start HydroBuddy when I sign in to Windows")
        self.autostart.setChecked(autostart)

        form = QFormLayout()
        form.addRow("Remind me every", self.interval)
        form.addRow("Snooze for", self.snooze)
        form.addRow("Daily goal", self.goal)
        form.addRow("New day starts at", self.day_start)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(_hint("Your glass count resets when a new day starts."))
        layout.addSpacing(8)
        layout.addLayout(quiet_row)
        layout.addWidget(self.fullscreen)
        layout.addWidget(self.autostart)
        layout.addSpacing(8)
        layout.addWidget(buttons)

    def _sync_quiet(self, enabled: bool) -> None:
        self.quiet_start.setEnabled(enabled)
        self.quiet_end.setEnabled(enabled)

    def settings(self) -> Settings:
        return Settings(
            interval_minutes=self.interval.value(),
            snooze_minutes=self.snooze.value(),
            daily_goal=self.goal.value(),
            day_start=self.day_start.time().toString("HH:mm"),
            quiet_hours=self.quiet.isChecked(),
            quiet_start=self.quiet_start.time().toString("HH:mm"),
            quiet_end=self.quiet_end.time().toString("HH:mm"),
            skip_when_fullscreen=self.fullscreen.isChecked(),
        )

    def autostart_enabled(self) -> bool:
        return self.autostart.isChecked()
