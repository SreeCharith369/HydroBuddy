"""Settings window for the HydroBuddy shell."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
)

from core.settings_manager import load_settings, save_settings
from ui import theme
from utils.logger import logger


class SettingsWindow(QDialog):
    """Simple settings editor backed by `data/settings.json`."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HydroBuddy Settings")
        self.setFixedWidth(theme.SETTINGS_WIDTH)
        self.setModal(False)

        self.reminder_interval = QSpinBox()
        self.reminder_interval.setRange(1, 720)
        self.reminder_interval.setSuffix(" min")
        self.reminder_interval.setFixedWidth(theme.SETTINGS_FIELD_WIDTH)

        self.snooze_interval = QSpinBox()
        self.snooze_interval.setRange(1, 120)
        self.snooze_interval.setSuffix(" min")
        self.snooze_interval.setFixedWidth(theme.SETTINGS_FIELD_WIDTH)

        self.daily_goal = QSpinBox()
        self.daily_goal.setRange(1, 50)
        self.daily_goal.setSuffix(" glasses")
        self.daily_goal.setFixedWidth(theme.SETTINGS_FIELD_WIDTH)

        self.daily_reset_time = QTimeEdit()
        self.daily_reset_time.setDisplayFormat("HH:mm")
        self.daily_reset_time.setFixedWidth(theme.SETTINGS_FIELD_WIDTH)

        self.start_with_windows = QCheckBox("Start with Windows")
        self.pause_during_fullscreen = QCheckBox("Pause during fullscreen apps")

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(theme.SPACING_LARGE)
        form.setVerticalSpacing(theme.SPACING_MEDIUM)
        form.addRow("Reminder Interval", self.reminder_interval)
        form.addRow("Snooze Interval", self.snooze_interval)
        form.addRow("Daily Goal", self.daily_goal)
        form.addRow("Daily Reset Time", self.daily_reset_time)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)

        title = QLabel("Settings")
        title.setObjectName("settingsTitle")

        checkboxes = QVBoxLayout()
        checkboxes.setSpacing(theme.SPACING_SMALL)
        checkboxes.addWidget(self.start_with_windows)
        checkboxes.addWidget(self.pause_during_fullscreen)

        content = QVBoxLayout(self)
        content.setContentsMargins(
            theme.SPACING_XLARGE,
            theme.SPACING_XLARGE,
            theme.SPACING_XLARGE,
            theme.SPACING_LARGE,
        )
        content.setSpacing(theme.SPACING_LARGE)
        content.addWidget(title)
        content.addLayout(form)
        content.addLayout(checkboxes)
        content.addWidget(buttons)

        self.setStyleSheet(self._style_sheet())
        self.reload()

    def reload(self) -> None:
        """Reload settings from disk into the editor fields."""

        settings = load_settings()
        self.reminder_interval.setValue(int(settings["reminder_interval"]))
        self.snooze_interval.setValue(int(settings["snooze_interval"]))
        self.daily_goal.setValue(int(settings["daily_goal"]))
        reset_time = QTime.fromString(str(settings["daily_reset_time"]), "HH:mm")
        self.daily_reset_time.setTime(reset_time if reset_time.isValid() else QTime(2, 0))
        self.start_with_windows.setChecked(bool(settings["start_with_windows"]))
        self.pause_during_fullscreen.setChecked(
            bool(settings["pause_during_fullscreen"])
        )

    def save(self) -> None:
        """Save edited settings to disk."""

        current = load_settings()
        current.update(
            {
                "reminder_interval": self.reminder_interval.value(),
                "snooze_interval": self.snooze_interval.value(),
                "daily_goal": self.daily_goal.value(),
                "daily_reset_time": self.daily_reset_time.time().toString("HH:mm"),
                "start_with_windows": self.start_with_windows.isChecked(),
                "pause_during_fullscreen": self.pause_during_fullscreen.isChecked(),
            }
        )
        save_settings(current)
        logger.info("Settings saved")
        self.accept()

    @staticmethod
    def _style_sheet() -> str:
        return f"""
            QDialog {{
                background: {theme.COLOR_SETTINGS_BACKGROUND};
                color: {theme.COLOR_SETTINGS_TEXT};
                font-family: "{theme.FONT_FAMILY}";
                font-size: {theme.FONT_SIZE_NORMAL}pt;
            }}
            QLabel, QCheckBox {{
                color: {theme.COLOR_SETTINGS_TEXT};
            }}
            #settingsTitle {{
                font-size: {theme.FONT_SIZE_TITLE}pt;
                font-weight: 700;
            }}
            QSpinBox, QTimeEdit, QComboBox {{
                background: {theme.COLOR_SETTINGS_FIELD_BACKGROUND};
                color: {theme.COLOR_SETTINGS_FIELD_TEXT};
                border: 1px solid {theme.COLOR_SETTINGS_FIELD_BORDER};
                border-radius: {theme.CORNER_RADIUS_SMALL}px;
                padding: {theme.SPACING_SMALL}px;
            }}
            QSpinBox::up-button, QSpinBox::down-button,
            QTimeEdit::up-button, QTimeEdit::down-button {{
                background: {theme.COLOR_SETTINGS_BUTTON_BACKGROUND};
                border-left: 1px solid {theme.COLOR_SETTINGS_FIELD_BORDER};
                width: 18px;
            }}
            QCheckBox::indicator {{
                background: {theme.COLOR_SETTINGS_CHECK_INDICATOR};
                border: 1px solid {theme.COLOR_SETTINGS_FIELD_BORDER};
                border-radius: 3px;
                width: 14px;
                height: 14px;
            }}
            QCheckBox::indicator:checked {{
                background: {theme.COLOR_BUTTON_PRIMARY};
                border: 1px solid {theme.COLOR_BUTTON_PRIMARY};
            }}
            QPushButton {{
                background: {theme.COLOR_SETTINGS_BUTTON_BACKGROUND};
                color: {theme.COLOR_SETTINGS_BUTTON_TEXT};
                border: 1px solid {theme.COLOR_SETTINGS_BUTTON_BORDER};
                border-radius: {theme.CORNER_RADIUS_SMALL}px;
                padding: {theme.SPACING_SMALL}px {theme.SPACING_MEDIUM}px;
            }}
            QPushButton:pressed {{
                background: {theme.COLOR_SETTINGS_BUTTON_PRESSED};
            }}
        """
