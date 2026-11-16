"""Optional screen block: dims every screen and swallows clicks until the reminder is answered.

Each monitor gets a dark, see-through window that sits above everything except
the reminder popup. It catches mouse clicks and key presses so nothing behind it
can be used. It can't stop system shortcuts such as Alt+Tab or Ctrl+Alt+Del, and
doesn't try to: those stay available as a way out.

Safety nets, so a bug can never leave the screen locked:
  * a watchdog lifts the block as soon as ``still_needed()`` says no;
  * the block lifts by itself after ``max_seconds``.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

BLOCK_MAX_SECONDS = 300  # never hold the screen longer than this
SHADE = QColor(6, 14, 30, 205)  # the dimming over the whole screen
CARD = QColor(16, 34, 66)  # the solid panel behind the message


class _Shade(QWidget):
    """One dimming window covering one monitor."""

    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.title, self.subtitle = title, subtitle
        self.closing = False
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(260)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    def appear(self) -> None:
        self.setWindowOpacity(0.0)
        self.show()
        self._fade.start()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), SHADE)

        # The message sits on its own card, so it reads cleanly over any screen.
        title_font = QFont("Segoe UI", 30, QFont.Weight.DemiBold)
        subtitle_font = QFont("Segoe UI", 13)
        title_w = QFontMetrics(title_font).horizontalAdvance(self.title)
        subtitle_w = QFontMetrics(subtitle_font).horizontalAdvance(self.subtitle)
        card_w = min(self.width() - 40, max(title_w, subtitle_w) + 96)
        card = QRectF((self.width() - card_w) / 2, self.height() / 2 - 92, card_w, 172)
        p.setPen(QPen(QColor(255, 255, 255, 40), 1.5))
        p.setBrush(CARD)
        p.drawRoundedRect(card, 22, 22)

        p.setPen(QColor(255, 255, 255, 245))
        p.setFont(title_font)
        p.drawText(card.adjusted(24, 26, -24, -82), Qt.AlignmentFlag.AlignCenter, self.title)
        p.setPen(QColor(205, 222, 245))
        p.setFont(subtitle_font)
        p.drawText(card.adjusted(24, 96, -24, -28), Qt.AlignmentFlag.AlignCenter, self.subtitle)

    # Swallow input instead of passing it to whatever is behind.
    def mousePressEvent(self, event) -> None:
        event.accept()

    def keyPressEvent(self, event) -> None:
        event.accept()

    def closeEvent(self, event) -> None:
        # Alt+F4 must not remove the shade; only release() may.
        event.accept() if self.closing else event.ignore()


class ScreenBlocker:
    def __init__(self) -> None:
        self._shades: list[_Shade] = []
        self.max_seconds: float = BLOCK_MAX_SECONDS
        self.on_timeout: Callable[[], None] | None = None  # called if max_seconds runs out
        self._still_needed: Callable[[], bool] = lambda: True
        self._watchdog = QTimer()
        self._watchdog.setInterval(500)
        self._watchdog.timeout.connect(self._check)
        self._limit = QTimer()
        self._limit.setSingleShot(True)
        self._limit.timeout.connect(self._timed_out)

    @property
    def active(self) -> bool:
        return bool(self._shades)

    def block(self, title: str, subtitle: str, still_needed: Callable[[], bool]) -> None:
        """Dim and block every screen until release() (or a safety net) lifts it."""

        self.release()
        self._still_needed = still_needed
        for screen in QGuiApplication.screens():
            shade = _Shade(title, subtitle)
            shade.setGeometry(screen.geometry())
            shade.appear()
            self._shades.append(shade)
        if self._shades:
            self._shades[0].activateWindow()  # typing goes to the shade, not the app behind
        self._watchdog.start()
        self._limit.start(int(self.max_seconds * 1000))

    def release(self) -> None:
        self._watchdog.stop()
        self._limit.stop()
        for shade in self._shades:
            shade.closing = True
            shade.close()
            shade.deleteLater()
        self._shades = []

    def _check(self) -> None:
        if not self._still_needed():
            self.release()

    def _timed_out(self) -> None:
        self.release()
        if self.on_timeout:
            self.on_timeout()
