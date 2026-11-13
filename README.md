# HydroBuddy

A Windows tray companion that reminds you to drink water. A pixel-art water drop
pops up from behind your taskbar, asks you to drink, and celebrates when you do.

Status: **rebuild, Phase 1** (core logic). See [docs/REBUILD_PLAN.md](docs/REBUILD_PLAN.md).

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
```

## Commands

```powershell
.\.venv\Scripts\python -m pytest            # run tests
.\.venv\Scripts\python -m ruff check .      # lint
.\.venv\Scripts\python tools\make_character.py   # regenerate character sprites + previews
.\.venv\Scripts\python tools\demo_popup.py       # see the character on your desktop
```

## Layout

```text
hydrobuddy/
  core/       clock, storage, settings, day boundary, history, scheduler (no Qt)
  platform/   Windows integration (Phase 3)
  ui/         tray, popup, character view (Phase 2+)
  assets/character/   sprite strips + character.json (animation contract)
tests/        pytest suite for core
tools/        character generator and desktop demo
docs/         rebuild and animation plans
```

User data is stored in `%APPDATA%\HydroBuddy` (override with `HYDROBUDDY_DATA_DIR`).
