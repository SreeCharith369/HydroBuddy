from datetime import date, datetime, time

from hydrobuddy.core.history import History, load_history, save_history

TWO_AM = time(2, 0)
GOAL = 3


def at(day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute)


def log(h: History, when: datetime, times: int = 1) -> None:
    for _ in range(times):
        h.log_glass(when, TWO_AM, GOAL)


def test_log_and_undo():
    h = History()
    log(h, at(13), 2)
    assert h.today(at(13), TWO_AM, GOAL).glasses == 2
    h.undo_glass(at(13), TWO_AM, GOAL)
    assert h.today(at(13), TWO_AM, GOAL).glasses == 1


def test_undo_never_goes_negative():
    h = History()
    assert h.undo_glass(at(13), TWO_AM, GOAL).glasses == 0


def test_glass_after_midnight_counts_for_previous_day():
    h = History()
    log(h, at(13, 23, 50))
    log(h, at(14, 1, 30))  # before 02:00 -> still the 13th
    assert h.record(date(2026, 11, 13), GOAL).glasses == 2
    assert h.today(at(14, 2, 5), TWO_AM, GOAL).glasses == 0  # new day


def test_app_closed_for_days_leaves_zero_gaps():
    h = History()
    log(h, at(10), 3)
    log(h, at(13), 1)
    recent = h.recent(at(13), TWO_AM, GOAL, days=4)
    assert [r.day.day for r in recent] == [10, 11, 12, 13]
    assert [r.glasses for r in recent] == [3, 0, 0, 1]


def test_streak_counts_consecutive_goal_days():
    h = History()
    log(h, at(10), 3)
    log(h, at(11), 3)
    log(h, at(12), 4)
    # today (13th) not finished yet -> streak counts up to yesterday
    assert h.streak(at(13), TWO_AM, GOAL) == 3
    log(h, at(13), 3)
    assert h.streak(at(13), TWO_AM, GOAL) == 4


def test_streak_broken_by_missed_day():
    h = History()
    log(h, at(10), 3)
    log(h, at(12), 3)
    assert h.streak(at(12), TWO_AM, GOAL) == 1


def test_changing_goal_keeps_todays_glasses_and_past_goals():
    h = History()
    log(h, at(12), 3)  # goal 3, met
    log(h, at(13), 2)
    today = h.today(at(13), TWO_AM, goal=8)
    assert (today.glasses, today.goal) == (2, 8)
    assert h.record(date(2026, 11, 12), goal=8).goal == 3  # past day keeps its goal


def test_persistence_round_trip():
    h = History()
    log(h, at(12), 2)
    log(h, at(13), 1)
    save_history(h)
    loaded = load_history()
    assert loaded.to_dict() == h.to_dict()


def test_bad_day_entries_are_skipped_not_fatal():
    h = History.from_dict(
        {"days": {"2026-11-12": {"glasses": 2, "goal": 3}, "oops": {}, "2026-11-13": "x"}}
    )
    assert h.record(date(2026, 11, 12), GOAL).glasses == 2
    assert list(h.to_dict()["days"]) == ["2026-11-12"]
