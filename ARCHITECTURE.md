# Architecture

HydroBuddy is a local Windows desktop app built with Python 3.14 and PySide6. The architecture stays deliberately small: core behavior, UI presentation, data files, assets, logging, and utilities.

Milestone 3 implements the reminder scheduler and state machine while keeping final character visuals as placeholders.

## Folder Structure

```text
assets/
  animations/      Future MP4 animation assets.
  icons/           Future Windows application icon.
  images/          Future static images.

core/
  Application coordination, state vocabulary, storage, settings, reminders, and tracking.

data/
  Local JSON files for settings, progress, message text, and animation metadata.

docs/
  Supporting implementation notes.

logs/
  Local application log file.

ui/
  Future PySide6 windows, small components, tray integration, theme constants, and animation playback surface.

utils/
  Small cross-cutting helpers.
```

## Module Responsibilities

`main.py`

Stable application entry point. It initializes PySide6 through the app controller.

`core/app_controller.py`

Top-level coordinator. It connects settings, progress loading, the reminder manager, tray manager, settings window, and reminder window.

`core/reminder_manager.py`

Reminder-flow coordinator. It handles timer expirations, Done, Later, Ignore, placeholder animation events, window show/hide callbacks, and graceful shutdown.

`core/reminder_scheduler.py`

Owns the single reusable Qt timer used for normal reminders, snooze reminders, and the 60-second ignore timeout.

`core/events.py`

Defines event names for future communication between core and UI modules. It does not dispatch events.

`core/constants.py`

Defines application defaults used as a single reference point. Runtime settings still come from JSON.

`core/tracker.py`

Loads progress for display. Persistent daily progress updates are still future work.

`core/settings_manager.py`

Loads and saves settings with current defaults. Validation and recovery hardening are still future work.

`core/storage.py`

JSON storage boundary for reading and writing local files.

`core/state_machine.py`

Defines `ApplicationState` and the deterministic reminder transition table.

`ui/reminder_window.py`

Transparent companion reminder window and composition root for reminder UI components. The top-level window uses a translucent background with opaque placeholder child widgets.

`ui/speech_bubble.py`

Future speech bubble component for reminder and response text.

`ui/character_widget.py`

Future character display component.

`ui/action_buttons.py`

Future reminder action button group.

`ui/settings_window.py`

Settings editor backed by `data/settings.json`; styling is defined through `ui/theme.py` so controls remain readable in Windows light and dark modes.

`ui/tray_manager.py`

Future Windows tray integration.

`ui/animation_player.py`

Future MP4 playback surface for companion animations.

`ui/theme.py`

Defines UI constants for fonts, colors, dimensions, spacing, radii, and settings-control contrast.

`utils/windows.py`

Future Windows-specific helpers such as startup registration and fullscreen checks.

`utils/paths.py`

Future path helpers for project files, user data, and assets.

`utils/helpers.py`

Future home for tiny generic helpers that do not justify a dedicated module.

`utils/resources.py`

Resolves resource paths in source and packaged-executable contexts.

`utils/logger.py`

Configures and exposes the shared application logger.

## Planned Data Flow

1. `main.py` starts the app.
2. `app_controller` initializes managers.
3. `settings_manager` reads settings through `storage`.
4. `reminder_manager` coordinates state transitions.
5. UI modules display the current state.
6. User actions return to `reminder_manager`.
7. `tracker` updates progress and `storage` persists it.

Milestone 3 implements this flow through the app controller, reminder manager, scheduler, and state machine. Persistent progress updates remain future work.

## Timer Engine

Timer behavior is implemented in `core/reminder_scheduler.py`.

Timer responsibility remains outside UI widgets and currently supports:

- Default 60-minute reminder intervals.
- Exactly 10-minute snooze intervals.
- Exactly 60-second ignore timeout.
- Safe cancellation and restart with one active timer.

Daily reset scheduling and fullscreen delay behavior are future work.

## Animation Contract

Animation playback belongs in `ui/animation_player.py` in a future milestone. Milestone 3 exposes log-only placeholder events from `ReminderManager`.

Planned flow:

- `ENTER` plays once, then moves to `IDLE`.
- `IDLE` loops while waiting for user action.
- `DRINK` plays once, then moves to `EXITING`.
- `DISAPPOINTED` plays once, then moves to `EXITING`.
- `EXIT` plays once, then hides the companion.

Metadata for this flow lives in `data/animations.json`. It is not consumed by code yet.

## Events

Events are named in `core/events.py`:

- `ReminderTriggered`
- `WaterDrank`
- `Snoozed`
- `AnimationFinished`
- `ReminderDismissed`
- `SettingsChanged`
- `DayReset`

The project intentionally does not include an event bus or dispatcher yet.

## Storage

Storage uses local JSON files in `data/`:

- `settings.json`
- `progress.json`
- `messages.json`
- `animations.json`

The app should not require a database, server, account, or network access.

`progress.json` stores the current goal next to the glass count so a daily record remains self-contained if the user later changes settings.

## UI

The UI should eventually be small and non-intrusive:

- Transparent always-on-top reminder window.
- Pixel-art companion.
- Rounded speech bubble.
- Two reminder actions.
- Tray menu for quiet control.
- Settings window for simple preferences.

The reminder window should be composed from focused modules: speech bubble, character widget, action buttons, animation player, and theme constants.

## Logging

`logs/hydrobuddy.log` is the default local log file. Milestone 3 logs application startup and exit, reminder scheduling and cancellation, reminder show and hide, Done, Later, Ignore timeout, placeholder animation events, state transitions, settings saves, and handled errors.
