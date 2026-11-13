"""Checks that need a real Windows desktop (the automated tests run without one).

What it does, in about 10 seconds:
  1. Pops up a reminder and checks that its see-through parts let clicks pass to
     the window behind, while the bubble, buttons and character catch them.
  2. Briefly shows a maximized window, then a fullscreen one, and checks that
     only the fullscreen one counts as "don't interrupt".
  3. Starts the real app (with a throwaway data folder), checks the tray icon,
     and saves screenshots of the tray menu, popup and windows to preview/.

Run:  .venv/Scripts/python tools/desktop_check.py
"""

from __future__ import annotations

import ctypes
import os
import sys
import tempfile
from ctypes import wintypes
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["HYDROBUDDY_DATA_DIR"] = tempfile.mkdtemp(prefix="hydrobuddy-check-")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QSystemTrayIcon  # noqa: E402

from hydrobuddy.core.history import DayRecord  # noqa: E402
from hydrobuddy.platform import focus  # noqa: E402
from hydrobuddy.ui.popup import BUBBLE_H, BUBBLE_W, ReminderPopup  # noqa: E402

OUT = ROOT / "preview"
user32 = ctypes.windll.user32
results: list[tuple[str, bool]] = []


def expect(label: str, ok: bool) -> None:
    results.append((label, ok))


def check_click_through(popup: ReminderPopup) -> None:
    rect = wintypes.RECT()
    user32.GetWindowRect(int(popup.winId()), ctypes.byref(rect))
    scale = (rect.right - rect.left) / popup.width()

    def catches(x: float, y: float) -> bool:
        point = wintypes.POINT(int(rect.left + x * scale), int(rect.top + y * scale))
        return user32.GetAncestor(user32.WindowFromPoint(point), 2) == int(popup.winId())

    expect("see-through corner passes clicks through", not catches(30, 8))
    expect("see-through area above his head passes clicks", not catches(popup.width() - 40, 15))
    expect("gap under the bubble passes clicks through", not catches(40, 26 + BUBBLE_H + 30))
    expect("speech bubble catches clicks", catches(120, 70))
    expect("character catches clicks", catches(BUBBLE_W - 12 + 108, popup.height() - 40))


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    OUT.mkdir(exist_ok=True)

    popup = ReminderPopup()
    window = QLabel("HydroBuddy desktop check: this window closes by itself")
    window.setStyleSheet("background:#20304a;color:white;font-size:26px;padding:40px;")

    def fullscreen_state(label: str, expected: bool) -> None:
        window.activateWindow()
        window.raise_()
        expect(label, focus.is_fullscreen() is expected)

    def start_app() -> None:
        from hydrobuddy.app import AppController

        controller = AppController(app)
        expect("system tray is available", QSystemTrayIcon.isSystemTrayAvailable())
        expect("tray icon is showing", controller.tray.isVisible())
        controller.tracker.drink(controller.clock.now())
        controller.refresh()
        controller.menu.popup(controller.tray.geometry().topLeft())

        def capture() -> None:
            controller.menu.grab().save(str(OUT / "check_tray_menu.png"))
            controller.menu.hide()
            controller.timer.stop()
            controller.tray.hide()
            app.quit()

        QTimer.singleShot(600, capture)

    popup.remind("Desktop check 💧", DayRecord(date.today(), 3, 8))
    steps = [
        (1800, lambda: check_click_through(popup)),
        (1900, lambda: popup.screen().grabWindow(0).save(str(OUT / "check_screen.png"))),
        (2000, popup.dismiss),
        (2100, window.showMaximized),
        (3000, lambda: fullscreen_state("maximized window is NOT fullscreen", False)),
        (3100, window.showFullScreen),
        (4000, lambda: fullscreen_state("fullscreen window IS fullscreen", True)),
        (4100, window.close),
        (4700, lambda: expect("nothing fullscreen after closing", not focus.is_fullscreen())),
        (4800, start_app),
    ]
    for ms, step in steps:
        QTimer.singleShot(ms, step)
    app.exec()

    failed = [label for label, ok in results if not ok]
    for label, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    print(f"\n{len(results) - len(failed)} of {len(results)} desktop checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
