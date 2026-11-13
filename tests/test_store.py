import json

from hydrobuddy.core import store


def test_data_dir_uses_override(isolated_data_dir):
    assert store.data_dir() == isolated_data_dir
    assert isolated_data_dir.is_dir()


def test_save_then_load_round_trip(tmp_path):
    path = tmp_path / "x.json"
    store.save(path, {"a": 1})
    assert store.load(path) == {"a": 1}


def test_missing_file_returns_none(tmp_path):
    assert store.load(tmp_path / "nope.json") is None


def test_second_save_keeps_backup(tmp_path):
    path = tmp_path / "x.json"
    store.save(path, {"v": 1})
    store.save(path, {"v": 2})
    assert json.loads((tmp_path / "x.json.bak").read_text()) == {"v": 1}
    assert store.load(path) == {"v": 2}


def test_corrupt_file_recovers_from_backup_and_is_kept(tmp_path):
    path = tmp_path / "x.json"
    store.save(path, {"v": 1})
    store.save(path, {"v": 2})
    path.write_text("{ not json", encoding="utf-8")

    assert store.load(path) == {"v": 1}  # from .bak
    assert (tmp_path / "x.json.corrupt").read_text(encoding="utf-8") == "{ not json"


def test_corrupt_without_backup_returns_none(tmp_path):
    path = tmp_path / "x.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")  # valid JSON, wrong shape
    assert store.load(path) is None
    assert (tmp_path / "x.json.corrupt").exists()


def test_no_temp_files_left_behind(tmp_path):
    path = tmp_path / "x.json"
    store.save(path, {"v": 1})
    store.save(path, {"v": 2})
    assert sorted(p.name for p in tmp_path.iterdir()) == ["x.json", "x.json.bak"]
