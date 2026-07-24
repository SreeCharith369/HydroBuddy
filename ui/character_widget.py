"""Character display placeholder for the reminder shell."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from ui import theme


class CharacterWidget(QFrame):
    """Reserved character area for future animation playback."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("characterWidget")
        self.setFixedSize(
            theme.ANIMATION_PLACEHOLDER_WIDTH,
            theme.ANIMATION_PLACEHOLDER_HEIGHT,
        )

        label = QLabel("Character")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName("characterLabel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
