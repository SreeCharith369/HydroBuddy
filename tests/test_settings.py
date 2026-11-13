from datetime import time

from hydrobuddy.core.settings import Settings, load_settings, save_settings


def test_defaults_when_no_file():
    assert load_settings() == Settings()


def test_round_trip():
    custom = Settings(interval_minutes=45, snooze_minutes=5, daily_goal=10, day_start="03:30")
    save_settings(custom)
    assert load_settings() == custom


def test_invalid_values_fall_back_to_defaults():
    s = Settings.from_dict(
        {
            "interval_minutes": 0,  # below minimum
            "snooze_minutes": "abc",  # not a number
            "daily_goal": True,  # bool is not a goal
            "day_start": "25:99",  # not a time
            "unknown_key": 1,  # ignored
        }
    )
    assert s == Settings()


def test_numeric_strings_are_accepted():
    s = Settings.from_dict({"interval_minutes": "90", "day_start": "4:05"})
    assert s.interval_minutes == 90
    assert s.day_start == "04:05"
    assert s.day_start_time == time(4, 5)


def test_corrupt_settings_file_gives_defaults(isolated_data_dir):
    isolated_data_dir.mkdir(parents=True, exist_ok=True)
    (isolated_data_dir / "settings.json").write_text("garbage", encoding="utf-8")
    assert load_settings() == Settings()
