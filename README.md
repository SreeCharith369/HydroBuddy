# HydroBuddy

HydroBuddy is a lightweight personal Windows desktop companion that reminds the user to drink water with an animated pixel-art character.

The project is built in small milestones. Milestone 3 provides a runnable desktop shell with a reminder scheduler, reminder state machine, Done/Later/Ignore flows, placeholder animation events, system tray menu, settings dialog, JSON loading/saving, and logging. Character animation playback, persistent hydration history, fullscreen detection, and notification features are intentionally left for later milestones.

## Tech Stack

- Python 3.14
- PySide6
- Windows 11
- Local JSON storage
- MP4 animations
- Git

## How to Run

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the placeholder entry point:

```powershell
python main.py
```

HydroBuddy starts in the system tray and schedules the next reminder. Use the tray menu to show or hide the reminder window, open settings, or exit.

## Folder Structure

```text
HydroBuddy/
  assets/
    animations/    Future MP4 files: enter, idle, drink, disappointed, exit.
    icons/         Future Windows icon.
    images/        Future static visual assets.
  core/            App coordination, reminder flow, settings, storage, state, tracking.
  data/            Local JSON defaults for settings, progress, messages, and animation metadata.
  docs/            Supporting project notes.
  logs/            Local application log file.
  ui/              PySide6 shell windows, tray manager, components, theme, and animation placeholder.
  utils/           Small shared helpers for paths, resources, logging, Windows behavior, and utilities.
  main.py          Application entry point.
```

## Current Milestone

Milestone 3 finalizes the reminder scheduler and state machine. The reminder window remains a transparent top-level overlay with opaque placeholder widgets, ready for future animated assets.
