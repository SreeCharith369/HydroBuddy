from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # no real windows during tests

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Never let a test touch the real %APPDATA%\\HydroBuddy."""

    folder = tmp_path / "data"
    monkeypatch.setenv("HYDROBUDDY_DATA_DIR", str(folder))
    return folder


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app
