"""History window: the last three months as a calendar grid, plus a few totals."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QLabel, QToolTip, QVBoxLayout, QWidget

from hydrobuddy.core.history import DayRecord

CELL, GAP = 20, 4
LEFT, TOP = 38, 24  # room for weekday and month labels
WEEKDAYS = ("Mon", "", "Wed", "", "Fri", "", "Sun")

_EMPTY = QColor(128, 128, 128, 56)  # faint in both light and dark themes
_SHADES = (QColor(178, 222, 250), QColor(104, 190, 244), QColor(46, 140, 220))
_GOAL = QColor(22, 92, 180)


def _colour(record: DayRecord) -> QColor:
    if record.glasses == 0:
        return _EMPTY
    if record.met_goal:
        return _GOAL
    return _SHADES[min(2, int(3 * record.glasses / record.goal))]


class _Grid(QWidget):
    """One column per week (Monday on top), newest week on the right."""

    def __init__(self) -> None:
        super().__init__()
        self.setMouseTracking(True)
        self._cells: list[tuple[QRectF, DayRecord]] = []
        self._months: list[tuple[float, str]] = []

    def set_records(self, records: list[DayRecord]) -> None:
        self._cells, self._months = [], []
        first: date = records[0].day
        last_month = None
        for record in records:
            column = ((record.day - first).days + first.weekday()) // 7
            x = LEFT + column * (CELL + GAP)
            y = TOP + record.day.weekday() * (CELL + GAP)
            self._cells.append((QRectF(x, y, CELL, CELL), record))
            if record.day.month != last_month and (record.day.day <= 7 or last_month is None):
                self._months.append((x, record.day.strftime("%b")))
                last_month = record.day.month
        columns = ((records[-1].day - first).days + first.weekday()) // 7 + 1
        self.setFixedSize(LEFT + columns * (CELL + GAP) + 8, TOP + 7 * (CELL + GAP) + 4)
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(self.palette().windowText().color())
        for row, name in enumerate(WEEKDAYS):
            p.drawText(
                QRectF(0, TOP + row * (CELL + GAP), LEFT - 8, CELL),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                name,
            )
        for x, name in self._months:
            p.drawText(QRectF(x, 0, 60, TOP - 6), Qt.AlignmentFlag.AlignBottom, name)
        p.setPen(Qt.PenStyle.NoPen)
        for rect, record in self._cells:
            p.setBrush(_colour(record))
            p.drawRoundedRect(rect, 4, 4)

    def mouseMoveEvent(self, event) -> None:
        for rect, record in self._cells:
            if rect.contains(event.position()):
                text = f"{record.day:%a %d %b}: {record.glasses} of {record.goal} glasses"
                QToolTip.showText(event.globalPosition().toPoint() + QPoint(12, 12), text, self)
                return
        QToolTip.hideText()


class HistoryWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HydroBuddy history")
        self.summary = QLabel()
        self.summary.setFont(QFont("Segoe UI", 10))
        self.grid = _Grid()
        hint = QLabel("Darker = more glasses. Darkest = goal reached. Hover a day for details.")
        hint.setStyleSheet("color: gray;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(self.summary)
        layout.addWidget(self.grid)
        layout.addWidget(hint)

    def show_records(self, records: list[DayRecord], streak: int) -> None:
        """``records`` is oldest-first and ends with today."""

        today = records[-1]
        total = sum(r.glasses for r in records)
        goal_days = sum(1 for r in records if r.met_goal)
        self.summary.setText(
            f"<b>Today:</b> {today.glasses} of {today.goal} glasses"
            f" &nbsp;•&nbsp; <b>Streak:</b> {streak} day{'s' if streak != 1 else ''}"
            f"<br><b>Last {len(records)} days:</b> {total} glasses,"
            f" goal reached on {goal_days} day{'s' if goal_days != 1 else ''}"
        )
        self.grid.set_records(records)
        self.adjustSize()
        self.setFixedSize(self.sizeHint())
        self.show()
        self.raise_()
        self.activateWindow()
