from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Never let a test touch the real %APPDATA%\\HydroBuddy."""

    folder = tmp_path / "data"
    monkeypatch.setenv("HYDROBUDDY_DATA_DIR", str(folder))
    return folder
