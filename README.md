# HydroBuddy

A small Windows tray app that reminds you to drink water. A cartoon water drop
pops up from behind your taskbar, asks you to drink, and celebrates when you do.

- Reminders on a timer (default: every 60 minutes), with **Done** / **Snooze**.
  No answer for 60 seconds counts as "busy", and he tries again after a full interval.
- Counts today's glasses against a daily goal; the count resets at **02:00**.
- Keeps about **three months** of daily records, shown as a calendar in **History**.
- Every change is saved the moment it happens, so a shutdown, restart or crash loses nothing,
  and the next reminder time survives a restart too.
- Doesn't interrupt fullscreen apps, games, videos or slideshows, or a locked screen;
  optional quiet hours.

## Install and run

**Packaged app (no Python needed):** build it once, then run `dist\HydroBuddy\HydroBuddy.exe`.
Keep the whole `dist\HydroBuddy` folder together; you can move it anywhere (for example
`%LOCALAPPDATA%\Programs\HydroBuddy`). If you turned on *Start with Windows* before moving
it, the entry fixes itself the next time you open the app.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python tools\build_exe.py
```

**From source:** `.\.venv\Scripts\pythonw run.pyw`

HydroBuddy lives in the system tray (the water-drop icon).

- **Left-click** opens History.
- **Right-click** opens the menu: today's count and next reminder, Log a glass,
  Undo last glass, Remind me now, Pause (30 min / 1 h / 2 h / until tomorrow),
  History, Settings, Quit.
- Opening the app again while it runs just opens History.

## Settings

| Setting | Default | Range |
|---|---|---|
| Remind me every | 60 minutes | 5–240 |
| Snooze for | 10 minutes | 1–60 |
| Daily goal | 8 glasses | 1–30 |
| New day starts at | 02:00 | any time |
| Quiet hours | off (23:00–08:00) | any window, may cross midnight |
| Wait while a fullscreen app, game or slideshow is open | on | on / off |
| Start HydroBuddy when I sign in to Windows | off | on / off |

## Where your data lives

`%APPDATA%\HydroBuddy` (override with the `HYDROBUDDY_DATA_DIR` environment variable):

- `history.json` holds one record per day, about three months back.
- `settings.json` holds your settings.
- `state.json` holds the next reminder time and any pause.
- `*.bak` is the previous good copy of each file. A damaged file is set aside as `*.corrupt`
  and the backup is used.
- `logs/` holds a small rotating log, including any unexpected errors.

## Development

```powershell
.\.venv\Scripts\python -m pytest                    # 93 automated tests (about 5 s)
.\.venv\Scripts\python -m ruff check .              # lint
.\.venv\Scripts\python tools\desktop_check.py       # 10 checks on the real desktop (about 10 s)
.\.venv\Scripts\python tools\preview_character.py   # render character previews to preview/
.\.venv\Scripts\python tools\build_exe.py           # build dist\HydroBuddy\HydroBuddy.exe
```

The automated tests drive the whole app with a fake clock: reminders, Done, Snooze,
ignoring, fullscreen and lock-screen deferral, quiet hours, pause, the 02:00 rollover,
restarts, settings and history. `desktop_check.py` covers what needs a real screen:
click-through on the popup's see-through parts, fullscreen vs. maximized windows,
and the tray icon.

```text
hydrobuddy/
  core/       storage, settings, day boundary, history, scheduler, tracker (no Qt)
  platform/   start-with-Windows, fullscreen/lock detection, single instance
  ui/         character (vector art + animations), popup, settings, history
  app.py      tray icon and wiring
tests/        pytest suite
tools/        exe builder, desktop checks, character previews
docs/         rebuild and animation plans
```
