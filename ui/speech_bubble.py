"""Speech bubble component for the reminder shell."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from ui import theme


class SpeechBubble(QFrame):
    """Rounded speech bubble with updateable title and subtitle text."""

    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__()
        self.setObjectName("speechBubble")
        self.setFixedWidth(theme.SPEECH_BUBBLE_WIDTH)
        self.setMinimumHeight(theme.SPEECH_BUBBLE_MIN_HEIGHT)

        self._title_label = QLabel()
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setWordWrap(True)
        self._title_label.setObjectName("speechTitle")

        self._subtitle_label = QLabel()
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle_label.setObjectName("speechSubtitle")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            theme.BUBBLE_PADDING_HORIZONTAL,
            theme.BUBBLE_PADDING_VERTICAL,
            theme.BUBBLE_PADDING_HORIZONTAL,
            theme.BUBBLE_PADDING_VERTICAL,
        )
        layout.setSpacing(theme.SPACING_SMALL)
        layout.addWidget(self._title_label)
        layout.addWidget(self._subtitle_label)

        self.set_title(title)
        self.set_subtitle(subtitle)

    def set_title(self, title: str) -> None:
        """Update the speech bubble title."""

        self._title_label.setText(title)

    def set_subtitle(self, subtitle: str) -> None:
        """Update the speech bubble subtitle."""

        self._subtitle_label.setText(subtitle)
