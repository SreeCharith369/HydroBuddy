"""Transparent reminder window for the HydroBuddy shell."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from ui import theme
from ui.action_buttons import ActionButtons
from ui.character_widget import CharacterWidget
from ui.speech_bubble import SpeechBubble


class ReminderWindow(QWidget):
    """Frameless reminder shell positioned near the primary monitor corner."""

    def __init__(
        self,
        progress: dict,
        on_water_drank: Callable[[], None],
        on_snooze: Callable[[], None],
    ) -> None:
        super().__init__()
        self._fade_animation: QPropertyAnimation | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT)
        self.setWindowOpacity(0.0)

        glasses = int(progress.get("glasses", 0))
        goal = int(progress.get("goal", 12))

        self._panel = QFrame()
        self._panel.setObjectName("reminderPanel")

        self.speech_bubble = SpeechBubble(
            title="Time to drink water!",
            subtitle=f"Today: {glasses} / {goal} glasses",
        )
        self.character_widget = CharacterWidget()
        self.action_buttons = ActionButtons(on_water_drank, on_snooze)

        panel_layout = QVBoxLayout(self._panel)
        panel_layout.setContentsMargins(
            theme.SPACING_LARGE,
            theme.SPACING_LARGE,
            theme.SPACING_LARGE,
            theme.SPACING_LARGE,
        )
        panel_layout.setSpacing(theme.SPACING_MEDIUM)
        panel_layout.addWidget(self.speech_bubble, alignment=Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(
            self.character_widget,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        panel_layout.addWidget(self.action_buttons, alignment=Qt.AlignmentFlag.AlignCenter)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self._panel)

        self.setStyleSheet(self._style_sheet())

    def position_bottom_right(self) -> None:
        """Move the window to the bottom-right of the primary monitor."""

        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return

        geometry = screen.availableGeometry()
        x = geometry.right() - self.width() - theme.WINDOW_MARGIN + 1
        y = geometry.bottom() - self.height() - theme.WINDOW_MARGIN + 1
        self.move(x, y)

    def show_with_fade(self) -> None:
        """Show the window with a short opacity animation."""

        self.position_bottom_right()
        self.show()
        self.raise_()
        self.activateWindow()
        self._animate_opacity(0.0, 1.0)

    def hide_with_fade(self) -> None:
        """Hide the window after a short opacity animation."""

        if not self.isVisible():
            return

        animation = self._animate_opacity(self.windowOpacity(), 0.0)
        animation.finished.connect(self.hide)

    def _animate_opacity(self, start: float, end: float) -> QPropertyAnimation:
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(theme.FADE_DURATION_MS)
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_animation = animation
        animation.start()
        return animation

    @staticmethod
    def _style_sheet() -> str:
        return f"""
            #reminderPanel {{
                background: {theme.COLOR_WINDOW_BACKGROUND};
                border: 1px solid {theme.COLOR_WINDOW_BORDER};
                border-radius: {theme.CORNER_RADIUS_LARGE}px;
            }}
            #speechBubble {{
                background: {theme.COLOR_SPEECH_BUBBLE};
                border: 1px solid {theme.COLOR_SPEECH_BORDER};
                border-radius: {theme.CORNER_RADIUS_LARGE}px;
            }}
            #speechTitle {{
                color: {theme.COLOR_SPEECH_TITLE};
                font-family: "{theme.FONT_FAMILY}";
                font-size: {theme.FONT_SIZE_TITLE}pt;
                font-weight: 700;
            }}
            #speechSubtitle {{
                color: {theme.COLOR_SPEECH_SUBTITLE};
                font-family: "{theme.FONT_FAMILY}";
                font-size: {theme.FONT_SIZE_NORMAL}pt;
            }}
            #characterWidget {{
                background: {theme.COLOR_CHARACTER_BACKGROUND};
                border: 1px dashed {theme.COLOR_CHARACTER_BORDER};
                border-radius: {theme.CORNER_RADIUS_MEDIUM}px;
            }}
            #characterLabel {{
                color: {theme.COLOR_CHARACTER_TEXT};
                font-family: "{theme.FONT_FAMILY}";
                font-size: {theme.FONT_SIZE_LARGE}pt;
                font-weight: 600;
            }}
            QPushButton {{
                border-radius: {theme.CORNER_RADIUS_SMALL}px;
                font-family: "{theme.FONT_FAMILY}";
                font-size: {theme.FONT_SIZE_NORMAL}pt;
                font-weight: 600;
            }}
            #primaryActionButton {{
                background: {theme.COLOR_BUTTON_PRIMARY};
                color: {theme.COLOR_BUTTON_PRIMARY_TEXT};
                border: 1px solid {theme.COLOR_BUTTON_PRIMARY};
            }}
            #secondaryActionButton {{
                background: {theme.COLOR_BUTTON_SECONDARY};
                color: {theme.COLOR_BUTTON_SECONDARY_TEXT};
                border: 1px solid {theme.COLOR_BUTTON_BORDER};
            }}
        """
