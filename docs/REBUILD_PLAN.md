# HydroBuddy Rebuild Plan

> **Status (2026-11-13):** Phases 0–6 are built and tested: core logic, tray app,
> Windows integration (start with Windows, fullscreen/lock-screen deferral, quiet
> hours, single instance), packaging as `dist/HydroBuddy/HydroBuddy.exe`, the
> history view, and the character (drawn live as vector art instead of sprite
> sheets). Not done: an installer (the .exe folder is copied by hand), Windows
> toast notifications, sound, and multi-monitor placement (the popup always uses
> the primary screen).

Goal: a Windows tray app that reliably reminds you to drink water, makes logging a
glass one click, and runs invisibly from boot, with an animated character added
**after** the core loop is proven.

Guiding rules (lessons from v1):

- Ship a usable app early (end of Phase 2), then layer features on top.
- Every setting in the UI must do something. If it isn't built, it isn't shown.
- Art and code are decoupled by an animation contract, so the app never waits on art.
- User data lives in `%APPDATA%`, never in the install folder.
- Core logic has tests before UI is built on it.

---

## Phase 0: Project setup (½ day)

- New branch `rebuild` (or a fresh folder). Keep v1 for reference.
- `pyproject.toml` with pinned versions (Python 3.12+, PySide6 6.x pinned).
- Dev tools: `pytest`, `ruff`.
- `.gitignore`: `.venv/`, `__pycache__/`, `build/`, `dist/`, `logs/`, `desktop.ini`. The app no longer writes runtime data into the repo.
- `.gitattributes`: `* text=auto eol=lf` to stop the CRLF warnings.

**Layout**

```text
hydrobuddy/
  core/        clock, scheduler, store, settings, history   (no Qt imports)
  platform/    windows startup, fullscreen/DND detection, single instance
  ui/          tray, popup, settings dialog, character view
  assets/      icon, character sprite sheets + JSON
tests/
```

**Done when:** `pytest` runs (empty) and `ruff` passes.

---

## Phase 1: Core logic, no UI (2–3 days)

| Module | Responsibility |
|---|---|
| `clock.py` | `now()` wrapper so tests can fake time |
| `store.py` | Path = `%APPDATA%\HydroBuddy`. Atomic write (temp file + `os.replace`), keep one `.bak`, recover from corrupt files without wiping history |
| `settings.py` | Dataclass schema + validation (reuse v1's `_normalize_settings` ideas) |
| `history.py` | Per-day records `{date, glasses, goal}`; log drink; undo last; today's total; streak |
| `scheduler.py` | Stores `next_due` as a **timestamp**. `is_due(now)`, `on_done()`, `on_snooze()`, `on_skip()`, `pause_until(t)`. No `QTimer` here |
| `day.py` | Day boundary (default 02:00, configurable), DST-safe (reuse v1 tracker logic) |

**Tests must cover:**

- PC slept for 3 hours, so exactly one reminder fires (no burst).
- Reset across 02:00 and across a DST change.
- App closed for 3 days, then the history shows gaps correctly.
- A corrupt or missing JSON file means you recover and keep the backup.
- Snooze, then Done, then the next reminder is a full interval later.

**Done when:** all tests pass and core has zero Qt imports.

---

## Phase 2: Tray MVP (2 days) and dogfood for 1 week

- Tray icon with progress in the tooltip ("5 / 8 glasses").
- Tray menu: **Log a glass**, **Pause ▸ (30 min / 1 h / rest of day)**, Settings, Quit.
- One `QTimer` ticks every 30 s and asks `scheduler.is_due(now)`. This survives sleep/wake because it compares timestamps rather than trusting a long timer.
- Plain popup (no animation yet): message, progress bar, **Done / Snooze / Skip**.
  Bottom-right of the primary screen, frameless, always on top, no focus stealing.
- Settings dialog with **only** interval, snooze length, daily goal and day-start time.
- Rotating log (`RotatingFileHandler`, 1 MB × 3) in `%APPDATA%\HydroBuddy\logs`.

**Done when:** you have used it yourself for 5 working days without it misbehaving.
Write down every annoyance; that list drives Phase 3.

---

## Phase 3: Windows integration (2–3 days)

- **Start with Windows:** `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` via `winreg`, toggle in settings.
- **Don't interrupt:** `SHQueryUserNotificationState` (fullscreen, presentation, D3D game, quiet time). If busy, defer the reminder until free.
- **Quiet hours** (e.g. 23:00–08:00).
- **Single instance:** `QLocalServer`/`QLocalSocket`. A second launch tells the first one to show itself.
- Optional sound, plus a real **silent mode** that respects it.

**Done when:** a reboot autostarts it, a fullscreen game or video blocks popups, and a second launch doesn't create a duplicate.

---

## Phase 4: Packaging (1–2 days)

- PyInstaller `--onedir --windowed`. Bundled resources come via `sys._MEIPASS`, and user data via `%APPDATA%`.
- Optional Inno Setup installer (Start Menu shortcut, uninstall).
- Test in **Windows Sandbox** (a clean machine): install, run, reboot, uninstall.

**Done when:** a fresh Windows install can run it with no Python present.

---

## Phase 5: History and motivation (2 days)

- "This week" view: 7 bars, goal line, current streak.
- Smart skip: if you logged a glass in the last N minutes, push the reminder back.
- Undo last glass from the tray.

---

## Phase 6: Animated character (see `ANIMATION_PLAN.md`)

- Build `CharacterView` against the **animation contract** first, using a static placeholder PNG.
- Swap in real sprite sheets when the art is ready. No code changes should be needed.
- States: `appear`, `idle` (loop), `celebrate`, `sad`, `leave`.

---

## Phase 7: Polish

- Windows toast notification as an alternative to the popup.
- Custom messages, theme, and multiple characters.
- Optional auto-update check.

---

## What to reuse from v1

| v1 file | Reuse? |
|---|---|
| `core/tracker.py` reset and normalize logic | Yes, move into `day.py`/`history.py` |
| `core/settings_manager.py` validation | Yes, as a dataclass validator |
| `core/storage.py` | Yes, but add atomic write + backup |
| `core/state_machine.py`, `events.py` | Simplify; the popup needs about 4 states |
| `ui/animation_player.py` (video playback) | No. It is replaced by the sprite-sheet player |
| `assets/raw videos/*` | Optionally, as reference frames for the animation pipeline |

## Rough timeline

| Week | Outcome |
|---|---|
| 1 | Phases 0–2: usable tray app, dogfooding starts |
| 2 | Phases 3–4: autostart, no interruptions, installable exe |
| 3 | Phase 5 + animation production in parallel |
| 4 | Phase 6 character integration, polish |
