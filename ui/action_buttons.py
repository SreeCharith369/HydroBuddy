"""Reminder action buttons for the shell."""

from collections.abc import Callable

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QWidget

from ui import theme


class ActionButtons(QWidget):
    """Button group for placeholder reminder actions."""

    def __init__(
        self,
        on_water_drank: Callable[[], None],
        on_snooze: Callable[[], None],
    ) -> None:
        super().__init__()
        self.water_button = QPushButton("Done")
        self.water_button.setObjectName("primaryActionButton")
        self.water_button.setFixedSize(theme.BUTTON_WIDTH, theme.BUTTON_HEIGHT)
        self.water_button.clicked.connect(on_water_drank)

        self.snooze_button = QPushButton("Later")
        self.snooze_button.setObjectName("secondaryActionButton")
        self.snooze_button.setFixedSize(theme.BUTTON_WIDTH, theme.BUTTON_HEIGHT)
        self.snooze_button.clicked.connect(on_snooze)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.BUTTON_GAP)
        layout.addWidget(self.water_button)
        layout.addWidget(self.snooze_button)
