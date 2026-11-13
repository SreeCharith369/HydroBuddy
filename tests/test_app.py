"""End-to-end tests of the running app: tray actions, the popup, and the clock.

The clock and the "is a fullscreen app open?" signal are fakes, and animations
run 25x faster, so a whole day of behaviour runs in a few seconds.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from PySide6.QtCore import QElapsedTimer
from PySide6.QtTest import QTest

from hydrobuddy import app as app_module
from hydrobuddy.app import GOAL_REACHED, AppController
from hydrobuddy.core.settings import Settings, save_settings
from hydrobuddy.core.tracker import RETENTION_DAYS, Tracker
from hydrobuddy.ui.popup import Phase

T0 = datetime(2026, 11, 13, 9, 0)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs) -> None:
        self.current += timedelta(**kwargs)


class FakeFocus:
    def __init__(self) -> None:
        self.fullscreen = False
        self.away = False

    def is_fullscreen(self) -> bool:
        return self.fullscreen

    def is_away(self) -> bool:
        return self.away


class FakeAutostart:
    def __init__(self) -> None:
        self.enabled = False

    def is_enabled(self) -> bool:
        return self.enabled

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled


@pytest.fixture
def env(qapp, isolated_data_dir, monkeypatch):
    """A running app with a fake clock; yields a helper object."""

    fake_autostart = FakeAutostart()
    monkeypatch.setattr(app_module, "autostart", fake_autostart)
    controllers: list[AppController] = []

    class Env:
        clock = FakeClock(T0)
        focus = FakeFocus()
        autostart = fake_autostart
        folder = isolated_data_dir

        def start(self) -> AppController:
            ctrl = AppController(
                qapp,
                tracker=Tracker(self.folder),
                clock=self.clock,
                focus_check=self.focus,
                tick_ms=3_600_000,  # the tests call tick() themselves
            )
            ctrl.popup.character.speed = 25.0
            ctrl.popup.ignore_seconds = 0.3
            controllers.append(ctrl)
            return ctrl

    yield Env()
    for ctrl in controllers:
        ctrl.timer.stop()
        ctrl.popup.dismiss()
        ctrl.history_window.close()
        ctrl.tray.hide()


def wait_for(condition, timeout_ms: int = 4000) -> None:
    clock = QElapsedTimer()
    clock.start()
    while not condition():
        assert clock.elapsed() < timeout_ms, "timed out waiting"
        QTest.qWait(10)


def wait_phase(ctrl: AppController, phase: Phase) -> None:
    wait_for(lambda: ctrl.popup.phase is phase)


def glasses(ctrl: AppController) -> int:
    return ctrl.tracker.today(ctrl.clock.now()).glasses


def reminder_on_screen(env) -> AppController:
    ctrl = env.start()
    env.clock.advance(minutes=60)
    ctrl.tick()
    wait_phase(ctrl, Phase.WAITING)
    return ctrl


# --- reminders ------------------------------------------------------------------


def test_nothing_happens_before_the_interval(env):
    ctrl = env.start()
    env.clock.advance(minutes=59)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.HIDDEN


def test_done_logs_a_glass_celebrates_and_leaves(env):
    ctrl = reminder_on_screen(env)
    assert ctrl.popup.bubble.done_button.isVisible()

    ctrl.popup.bubble.done_button.click()
    wait_phase(ctrl, Phase.CELEBRATING)
    assert glasses(ctrl) == 1
    assert not ctrl.popup.bubble.done_button.isVisible()
    wait_phase(ctrl, Phase.HIDDEN)
    assert not ctrl.popup.isVisible()
    assert ctrl.tracker.scheduler.next_due == env.clock.now() + timedelta(minutes=60)


def test_clicking_done_twice_logs_one_glass(env):
    ctrl = reminder_on_screen(env)
    ctrl.popup.bubble.done_button.click()
    ctrl.popup.bubble.done_clicked.emit()  # a second click that slips through
    wait_phase(ctrl, Phase.HIDDEN)
    assert glasses(ctrl) == 1


def test_snooze_is_sad_and_comes_back_after_snooze_time(env):
    ctrl = reminder_on_screen(env)
    ctrl.popup.bubble.snooze_button.click()
    wait_phase(ctrl, Phase.SAD)
    assert "10 minutes" in ctrl.popup.bubble.message.text()
    wait_phase(ctrl, Phase.HIDDEN)
    assert glasses(ctrl) == 0

    env.clock.advance(minutes=9)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.HIDDEN
    env.clock.advance(minutes=1)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.ARRIVING


def test_ignored_reminder_leaves_and_waits_a_full_interval(env):
    ctrl = reminder_on_screen(env)
    wait_phase(ctrl, Phase.SAD)  # ignore timeout (0.3 s in tests)
    wait_phase(ctrl, Phase.HIDDEN)
    assert glasses(ctrl) == 0
    assert ctrl.tracker.scheduler.next_due == env.clock.now() + timedelta(minutes=60)


def test_remind_me_now_while_on_screen_does_not_stack(env):
    ctrl = reminder_on_screen(env)
    ctrl.show_reminder()
    ctrl.tick()
    assert ctrl.popup.phase is Phase.WAITING


def test_reminder_waits_while_fullscreen(env):
    ctrl = env.start()
    env.focus.fullscreen = True
    env.clock.advance(minutes=60)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.HIDDEN
    env.focus.fullscreen = False
    env.clock.advance(minutes=20)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.ARRIVING  # shown as soon as the game/video closes


def test_fullscreen_setting_off_shows_anyway(env):
    save_settings(Settings(skip_when_fullscreen=False), env.folder)
    ctrl = env.start()
    env.focus.fullscreen = True
    env.clock.advance(minutes=60)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.ARRIVING


def test_reminder_waits_while_screen_is_locked(env):
    save_settings(Settings(skip_when_fullscreen=False), env.folder)
    ctrl = env.start()
    env.focus.away = True
    env.clock.advance(minutes=60)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.HIDDEN
    env.focus.away = False
    ctrl.tick()
    assert ctrl.popup.phase is Phase.ARRIVING


def test_quiet_hours(env):
    save_settings(Settings(quiet_hours=True, quiet_start="23:00", quiet_end="08:00"), env.folder)
    env.clock.current = datetime(2026, 11, 13, 22, 30)
    ctrl = env.start()
    env.clock.current = datetime(2026, 11, 13, 23, 30)  # due, but quiet
    ctrl.tick()
    assert ctrl.popup.phase is Phase.HIDDEN
    assert ctrl.next_action.text() == "Quiet hours until 08:00"
    env.clock.current = datetime(2026, 11, 14, 7, 59)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.HIDDEN
    env.clock.current = datetime(2026, 11, 14, 8, 0)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.ARRIVING


def test_pause_and_resume(env):
    ctrl = env.start()
    ctrl.pause(120)
    assert ctrl.next_action.text() == "Paused until 11:00"
    assert ctrl.resume_action.isVisible() and not ctrl.pause_menu.menuAction().isVisible()
    env.clock.advance(minutes=90)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.HIDDEN

    ctrl.resume()
    assert not ctrl.tracker.is_paused(env.clock.now())
    env.clock.advance(minutes=10)  # overdue reminders come back one snooze after resuming
    ctrl.tick()
    assert ctrl.popup.phase is Phase.ARRIVING


def test_pause_until_tomorrow_ends_at_2am(env):
    ctrl = env.start()
    ctrl.pause_until_tomorrow()
    env.clock.current = datetime(2026, 11, 14, 1, 59)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.HIDDEN
    env.clock.current = datetime(2026, 11, 14, 2, 0)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.ARRIVING


# --- logging glasses from the tray -------------------------------------------------


def test_log_a_glass_from_the_tray_pops_up_a_cheer(env):
    ctrl = env.start()
    ctrl.log_glass()
    assert glasses(ctrl) == 1
    wait_phase(ctrl, Phase.CELEBRATING)
    assert not ctrl.popup.bubble.done_button.isVisible()
    wait_phase(ctrl, Phase.HIDDEN)
    assert ctrl.status_action.text() == "1 of 8 glasses today"


def test_log_from_tray_while_reminder_waits_answers_it(env):
    ctrl = reminder_on_screen(env)
    ctrl.log_glass()
    wait_phase(ctrl, Phase.CELEBRATING)
    wait_phase(ctrl, Phase.HIDDEN)
    assert glasses(ctrl) == 1
    assert not ctrl.tracker.is_due(env.clock.now())


def test_log_from_tray_while_he_is_sad_celebrates_after(env):
    ctrl = reminder_on_screen(env)
    ctrl.popup.bubble.snooze_button.click()
    wait_phase(ctrl, Phase.SAD)
    ctrl.log_glass()
    assert glasses(ctrl) == 1
    wait_phase(ctrl, Phase.CELEBRATING)  # comes back up to celebrate
    wait_phase(ctrl, Phase.HIDDEN)


def test_two_glasses_while_celebrating_count_twice(env):
    ctrl = env.start()
    ctrl.log_glass()
    wait_phase(ctrl, Phase.CELEBRATING)
    ctrl.log_glass()
    assert glasses(ctrl) == 2
    assert "2 of 8" in ctrl.popup.bubble.progress_label.text()
    wait_phase(ctrl, Phase.HIDDEN)


def test_goal_reached_message(env):
    save_settings(Settings(daily_goal=2), env.folder)
    ctrl = env.start()
    ctrl.tracker.drink(env.clock.now())
    ctrl.log_glass()
    assert ctrl.popup.bubble.message.text() == GOAL_REACHED
    wait_phase(ctrl, Phase.HIDDEN)


def test_undo(env):
    ctrl = env.start()
    assert not ctrl.undo_action.isEnabled()
    ctrl.tracker.drink(env.clock.now())
    ctrl.refresh()
    assert ctrl.undo_action.isEnabled()
    ctrl.undo_glass()
    assert glasses(ctrl) == 0
    assert not ctrl.undo_action.isEnabled()


# --- days, restarts, settings -----------------------------------------------------------


def test_count_rolls_over_at_2am_while_running(env):
    env.clock.current = datetime(2026, 11, 13, 23, 0)
    ctrl = env.start()
    ctrl.tracker.drink(env.clock.now())
    ctrl.tracker.drink(env.clock.now())
    env.clock.current = datetime(2026, 11, 14, 1, 59)
    ctrl.refresh()
    assert ctrl.status_action.text() == "2 of 8 glasses today"
    env.clock.current = datetime(2026, 11, 14, 2, 0)
    ctrl.tick()
    assert ctrl.status_action.text() == "0 of 8 glasses today"


def test_restart_mid_day_keeps_count_and_schedule(env):
    ctrl = env.start()
    env.clock.advance(minutes=30)
    ctrl.tracker.drink(env.clock.now())
    ctrl.tracker.drink(env.clock.now())
    next_due = ctrl.tracker.scheduler.next_due
    ctrl.quit()  # or a power cut: everything was already saved

    env.clock.advance(minutes=15)
    again = env.start()
    assert glasses(again) == 2
    assert again.tracker.scheduler.next_due == next_due


def test_settings_apply_immediately_and_persist(env):
    ctrl = env.start()
    new = Settings(interval_minutes=30, snooze_minutes=5, daily_goal=12, quiet_hours=True)
    ctrl.apply_settings(new, start_with_windows=True)
    assert env.autostart.enabled
    assert ctrl.status_action.text() == "0 of 12 glasses today"
    assert Tracker(env.folder).settings == new
    env.clock.advance(minutes=30)
    ctrl.tick()
    assert ctrl.popup.phase is Phase.ARRIVING

    ctrl.apply_settings(new, start_with_windows=False)
    assert not env.autostart.enabled


def test_settings_dialog_round_trip(qapp):
    from hydrobuddy.ui.settings_dialog import SettingsDialog

    original = Settings(
        interval_minutes=45,
        snooze_minutes=7,
        daily_goal=11,
        day_start="03:30",
        quiet_hours=True,
        quiet_start="22:15",
        quiet_end="07:45",
        skip_when_fullscreen=False,
    )
    dialog = SettingsDialog(original, autostart=True)
    assert dialog.settings() == original
    assert dialog.autostart_enabled()
    dialog.quiet.setChecked(False)
    assert not dialog.quiet_start.isEnabled()


def test_history_window_shows_three_months(env):
    ctrl = env.start()
    for offset in range(RETENTION_DAYS + 10):
        ctrl.tracker.history.log_glass(
            env.clock.now() - timedelta(days=offset), ctrl.tracker.settings.day_start_time, 8
        )
    ctrl.show_history()
    assert ctrl.history_window.isVisible()
    assert len(ctrl.history_window.grid._cells) == RETENTION_DAYS
    assert "Streak:" in ctrl.history_window.summary.text()


def test_tray_left_click_opens_history(env):
    from PySide6.QtWidgets import QSystemTrayIcon

    ctrl = env.start()
    ctrl.tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    assert ctrl.history_window.isVisible()


def test_quit_hides_everything(env, qapp, monkeypatch):
    monkeypatch.setattr(qapp, "quit", lambda: None)
    ctrl = reminder_on_screen(env)
    ctrl.quit()
    assert ctrl.popup.phase is Phase.HIDDEN
    assert not ctrl.popup.isVisible()
    assert not ctrl.timer.isActive()
