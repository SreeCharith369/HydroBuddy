from datetime import date, datetime, time

from hydrobuddy.core.day import day_key, next_day_start

TWO_AM = time(2, 0)


def test_before_boundary_counts_as_previous_day():
    assert day_key(datetime(2026, 11, 13, 1, 59), TWO_AM) == date(2026, 11, 12)


def test_at_boundary_starts_new_day():
    assert day_key(datetime(2026, 11, 13, 2, 0), TWO_AM) == date(2026, 11, 13)


def test_late_evening_is_same_day():
    assert day_key(datetime(2026, 11, 13, 23, 30), TWO_AM) == date(2026, 11, 13)


def test_dst_spring_forward_skips_two_am_cleanly():
    # On a spring-forward night local time jumps 01:59 -> 03:00.
    assert day_key(datetime(2026, 3, 8, 1, 59), TWO_AM) == date(2026, 3, 7)
    assert day_key(datetime(2026, 3, 8, 3, 0), TWO_AM) == date(2026, 3, 8)


def test_dst_fall_back_repeated_hour_stays_same_day():
    # 01:30 happens twice; both belong to the previous day, 02:00 starts the new one.
    assert day_key(datetime(2026, 11, 1, 1, 30), TWO_AM) == date(2026, 10, 31)
    assert day_key(datetime(2026, 11, 1, 2, 0), TWO_AM) == date(2026, 11, 1)


def test_next_day_start():
    assert next_day_start(datetime(2026, 11, 13, 1, 0), TWO_AM) == datetime(2026, 11, 13, 2, 0)
    assert next_day_start(datetime(2026, 11, 13, 2, 0), TWO_AM) == datetime(2026, 11, 14, 2, 0)
    assert next_day_start(datetime(2026, 11, 13, 22, 0), TWO_AM) == datetime(2026, 11, 14, 2, 0)
