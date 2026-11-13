from datetime import datetime, timedelta

from hydrobuddy.core.settings import Settings
from hydrobuddy.core.tracker import RETENTION_DAYS, Tracker

NOON = datetime(2026, 11, 13, 12, 0)


def started(now: datetime = NOON) -> Tracker:
    tracker = Tracker()
    tracker.start(now)
    return tracker


def test_shutdown_in_the_middle_of_the_day_loses_nothing():
    first = started()
    first.drink(NOON)
    first.drink(NOON + timedelta(hours=1))
    first.drink(NOON + timedelta(hours=2))
    del first  # laptop shuts down: no clean exit, nothing extra is saved

    second = started(NOON + timedelta(hours=3))  # laptop restarts the same day
    assert second.today(NOON + timedelta(hours=3)).glasses == 3


def test_restart_resumes_the_pending_reminder():
    first = started()
    first.drink(NOON + timedelta(minutes=30))  # next reminder at 13:30

    second = started(NOON + timedelta(minutes=45))
    assert not second.is_due(NOON + timedelta(minutes=89))
    assert second.is_due(NOON + timedelta(minutes=90))


def test_count_refreshes_at_two_am():
    tracker = started()
    tracker.drink(datetime(2026, 11, 13, 23, 0))
    tracker.drink(datetime(2026, 11, 14, 1, 30))  # after midnight, before 2 AM
    assert tracker.today(datetime(2026, 11, 14, 1, 59)).glasses == 2
    assert tracker.today(datetime(2026, 11, 14, 2, 0)).glasses == 0  # fresh day
    # yesterday's record is still there
    assert tracker.recent(datetime(2026, 11, 14, 2, 0), days=2)[0].glasses == 2


def test_keeps_about_three_months_and_drops_older_days():
    tracker = started()
    for offset in range(120):
        tracker.history.log_glass(
            NOON - timedelta(days=offset),
            tracker.settings.day_start_time,
            tracker.settings.daily_goal,
        )
    tracker.drink(NOON)  # triggers pruning and a save

    reloaded = started()
    days = reloaded.history.to_dict()["days"]
    assert len(days) == RETENTION_DAYS
    assert min(days) == (NOON.date() - timedelta(days=RETENTION_DAYS - 1)).isoformat()
    assert max(days) == NOON.date().isoformat()


def test_drinking_restarts_the_interval():
    tracker = started()
    tracker.drink(NOON + timedelta(minutes=50))
    assert not tracker.is_due(NOON + timedelta(minutes=60))
    assert tracker.is_due(NOON + timedelta(minutes=110))


def test_undo_persists():
    tracker = started()
    tracker.drink(NOON)
    tracker.drink(NOON)
    tracker.undo(NOON)
    assert started().today(NOON).glasses == 1


def test_settings_change_persists_and_applies():
    tracker = started()
    tracker.drink(NOON)
    new = Settings(interval_minutes=30, snooze_minutes=5, daily_goal=10, day_start="02:00")
    tracker.update_settings(new, NOON)

    reloaded = started(NOON + timedelta(minutes=1))
    assert reloaded.settings == new
    today = reloaded.today(NOON + timedelta(minutes=1))
    assert (today.glasses, today.goal) == (1, 10)  # count kept, new goal applied
    assert reloaded.is_due(NOON + timedelta(minutes=30))


def test_pause_survives_restart():
    tracker = started()
    tracker.pause_for(NOON, minutes=180)
    reloaded = started(NOON + timedelta(minutes=5))
    assert reloaded.is_paused(NOON + timedelta(minutes=90))
    assert not reloaded.is_due(NOON + timedelta(minutes=90))


def test_pause_until_tomorrow_ends_at_day_start():
    tracker = started()
    tracker.pause_until_tomorrow(NOON)
    assert tracker.is_paused(datetime(2026, 11, 14, 1, 59))
    assert not tracker.is_paused(datetime(2026, 11, 14, 2, 0))
