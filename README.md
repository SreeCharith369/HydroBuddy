# HydroBuddy

A small Windows tray app that reminds you to drink water. A cartoon water drop
pops up from behind your taskbar, asks you to drink, and celebrates when you do.

- Reminders on a timer (default: every 60 minutes), with **Done** / **Snooze**.
  No answer for 60 seconds counts as "busy", and he tries again after a full interval.
- **Time to actually drink:** Done stays locked for 30 seconds and Snooze for 7, each
  showing a countdown, so you can't click Done without drinking. The "no answer" minute
  starts only once Done unlocks.
- **Optional screen block:** dims every screen and blocks clicks until you press Done or
  Snooze. Off by default. It lifts by itself after 5 minutes as a safety net, and system
  shortcuts such as Alt+Tab and Ctrl+Alt+Del keep working.
- Counts today's glasses against a daily goal; the count resets at **02:00**.
- Keeps about **three months** of daily records, shown as a calendar in **History**.
- Every change is saved the moment it happens, so a shutdown, restart or crash loses nothing,
  and the next reminder time survives a restart too.
- Doesn't interrupt fullscreen apps, games, videos or slideshows, or a locked screen;
  optional quiet hours.

## Install and run

**Install (recommended; no Python needed afterwards):**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python tools\build_exe.py
.\.venv\Scripts\python tools\install.py
```

`install.py` copies the app to `%LOCALAPPDATA%\Programs\HydroBuddy`, adds a **HydroBuddy**
Start menu shortcut and starts it. Run the last two commands again to update; your data is
kept. Install it rather than running `dist\HydroBuddy\HydroBuddy.exe` from the project
folder: an app that starts with Windows shouldn't live in OneDrive (OneDrive can turn its
files into cloud-only placeholders, and then the app can't start) or in a folder you might
move (the startup entry would point at the old place, and nothing would start).

**From source:** double-click `run.pyw`, or run `.\.venv\Scripts\pythonw run.pyw`.
(A double-click uses the system Python, so `run.pyw` hands over to `.venv` by itself.)

HydroBuddy opens no window. It lives in the system tray (the water-drop icon near the
clock, possibly under the `^` overflow arrow) and shows a "HydroBuddy is running" notice
when you start it. If it can't start, it shows an error box instead of closing silently.

- `HydroBuddy.exe --quit` (or `python -m hydrobuddy --quit`) closes the running copy.
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
| Unlock Done after | 30 seconds | 0–120 (0 = no wait) |
| Unlock Snooze after | 7 seconds | 0–60 (0 = no wait) |
| Dim and block the whole screen until I answer | off | on / off |
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
.\.venv\Scripts\python -m pytest                    # 119 automated tests (about 13 s)
.\.venv\Scripts\python -m ruff check .              # lint
.\.venv\Scripts\python tools\desktop_check.py       # 17 checks on the real desktop (about 15 s)
.\.venv\Scripts\python tools\preview_character.py   # render character previews to preview/
.\.venv\Scripts\python tools\build_exe.py           # build dist\HydroBuddy\HydroBuddy.exe
.\.venv\Scripts\python tools\install.py             # install that build and start it
```

The automated tests drive the whole app with a fake clock: reminders, Done, Snooze,
button cooldowns, the screen block, ignoring, fullscreen and lock-screen deferral, quiet
hours, pause, the 02:00 rollover, restarts, settings and history. `desktop_check.py`
covers what needs a real, unlocked screen: click-through on the popup's see-through
parts, the screen block catching clicks with the popup on top, fullscreen vs.
maximized windows, and the tray icon. Its screenshots in `preview/` show your real
screen, so they stay out of git.

```text
hydrobuddy/
  core/       storage, settings, day boundary, history, scheduler, tracker (no Qt)
  platform/   start-with-Windows, fullscreen/lock detection, single instance
  ui/         character (vector art + animations), popup, screen block, settings, history
  app.py      tray icon and wiring
tests/        pytest suite
tools/        exe builder, installer, desktop checks, character previews
docs/         rebuild and animation plans
```
