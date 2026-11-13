"""Windows integration: autostart (on a throwaway registry key), focus, single instance."""

from __future__ import annotations

import sys

import pytest
from PySide6.QtTest import QTest

from hydrobuddy.platform import autostart, focus
from hydrobuddy.platform.single_instance import SingleInstance

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")

TEST_KEY = r"Software\HydroBuddyTest\Run"


@pytest.fixture
def test_key():
    """A scratch registry key, so the real Run key is never touched."""

    import winreg

    yield TEST_KEY
    for path in (TEST_KEY, r"Software\HydroBuddyTest"):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        except FileNotFoundError:
            pass


def test_autostart_on_and_off(test_key):
    assert not autostart.is_enabled(test_key)
    autostart.set_enabled(True, test_key)
    assert autostart.is_enabled(test_key)
    assert autostart.registered_command(test_key) == autostart.launch_command()
    autostart.set_enabled(False, test_key)
    assert not autostart.is_enabled(test_key)
    autostart.set_enabled(False, test_key)  # turning off twice is fine


def test_autostart_refresh_fixes_a_moved_app_but_never_turns_it_on(test_key):
    import winreg

    assert not autostart.refresh(test_key)
    assert not autostart.is_enabled(test_key)

    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, test_key, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, autostart.VALUE_NAME, 0, winreg.REG_SZ, r'"C:\old\HydroBuddy.exe"')
    assert autostart.refresh(test_key)
    assert autostart.registered_command(test_key) == autostart.launch_command()
    assert not autostart.refresh(test_key)  # already correct


def test_launch_command_points_at_windowless_launcher():
    command = autostart.launch_command()
    assert "pythonw.exe" in command and "run.pyw" in command


def test_focus_checks_run_on_this_machine():
    # 0 is undocumented but returned by some Windows builds; it must not count as busy
    assert focus.notification_state() in range(0, 8)
    assert isinstance(focus.is_fullscreen(), bool)
    assert focus.screen_locked() is False  # someone is running these tests
    assert focus.is_away() is False


def test_undocumented_zero_state_is_not_treated_as_busy(monkeypatch):
    monkeypatch.setattr(focus, "notification_state", lambda: 0)
    monkeypatch.setattr(focus, "foreground_is_fullscreen", lambda: False)
    monkeypatch.setattr(focus, "screen_locked", lambda: False)
    assert not focus.is_fullscreen()
    assert not focus.is_away()


@pytest.mark.parametrize("state", [focus.BUSY, focus.D3D_FULLSCREEN, focus.PRESENTATION, focus.APP])
def test_windows_busy_states_count_as_fullscreen(monkeypatch, state):
    monkeypatch.setattr(focus, "notification_state", lambda: state)
    monkeypatch.setattr(focus, "foreground_is_fullscreen", lambda: False)
    assert focus.is_fullscreen()


def test_second_launch_is_refused_and_activates_the_first(qapp, isolated_data_dir):
    isolated_data_dir.mkdir(parents=True, exist_ok=True)
    first = SingleInstance(isolated_data_dir)
    assert first.acquire()
    activations = []
    first.activated.connect(lambda: activations.append(1))

    second = SingleInstance(isolated_data_dir)
    assert not second.acquire()
    for _ in range(50):
        if activations:
            break
        QTest.qWait(20)
    assert activations == [1]
