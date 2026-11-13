from datetime import datetime, timedelta

from hydrobuddy.core.scheduler import Scheduler

T0 = datetime(2026, 11, 13, 9, 0)


def minutes(n: int) -> timedelta:
    return timedelta(minutes=n)


def fresh() -> Scheduler:
    return Scheduler.create(interval_minutes=60, snooze_minutes=10).start(T0)


def test_first_reminder_after_one_interval():
    s = fresh()
    assert not s.is_due(T0 + minutes(59))
    assert s.is_due(T0 + minutes(60))


def test_long_sleep_gives_exactly_one_reminder():
    s = fresh()
    wake = T0 + timedelta(hours=3)
    assert s.is_due(wake)
    s = s.mark_shown(wake)
    # polling again and again while it's on screen never fires a second one
    assert not any(s.is_due(wake + timedelta(seconds=30 * i)) for i in range(20))
    s = s.on_done(wake + minutes(1))
    assert s.next_due == wake + minutes(61)


def test_snooze_then_done_gives_full_interval():
    s = fresh().mark_shown(T0 + minutes(60))
    s = s.on_snooze(T0 + minutes(60))
    assert s.next_due == T0 + minutes(70)
    assert s.is_due(T0 + minutes(70))
    s = s.mark_shown(T0 + minutes(70)).on_done(T0 + minutes(71))
    assert s.next_due == T0 + minutes(131)


def test_skip_waits_full_interval():
    s = fresh().mark_shown(T0 + minutes(60)).on_skip(T0 + minutes(61))
    assert s.next_due == T0 + minutes(121)


def test_pause_blocks_then_resume_waits_a_snooze():
    s = fresh().pause(until=T0 + timedelta(hours=2))
    assert not s.is_due(T0 + minutes(90))  # would be due, but paused
    s = s.resume(T0 + minutes(90))
    assert s.next_due == T0 + minutes(100)
    assert s.is_due(T0 + minutes(100))


def test_pause_expires_on_its_own():
    s = fresh().pause(until=T0 + minutes(90))
    assert not s.is_due(T0 + minutes(80))
    assert s.is_due(T0 + minutes(90))


def test_restart_keeps_saved_next_due():
    saved = fresh().to_dict()
    restored = Scheduler.create(60, 10).restore(saved).start(T0 + minutes(20))
    assert restored.next_due == T0 + minutes(60)


def test_restart_after_pc_was_off_waits_one_snooze():
    saved = fresh().to_dict()
    boot = T0 + timedelta(hours=10)
    restored = Scheduler.create(60, 10).restore(saved).start(boot)
    assert not restored.is_due(boot)
    assert restored.next_due == boot + minutes(10)


def test_shorter_interval_pulls_next_reminder_in():
    s = fresh().with_settings(interval_minutes=30, snooze_minutes=5, now=T0 + minutes(5))
    assert s.next_due == T0 + minutes(35)
    assert s.snooze == minutes(5)


def test_longer_interval_does_not_push_existing_reminder_out():
    s = fresh().with_settings(interval_minutes=120, snooze_minutes=10, now=T0 + minutes(5))
    assert s.next_due == T0 + minutes(60)


def test_corrupt_saved_state_is_ignored():
    s = Scheduler.create(60, 10).restore({"next_due": "not a date", "paused_until": 5})
    assert s.next_due is None and s.paused_until is None
