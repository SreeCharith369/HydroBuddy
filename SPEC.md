# HydroBuddy Specification

HydroBuddy is a lightweight personal Windows 11 desktop companion that reminds the user to drink water using an animated pixel-art character.

The app is local-only, quiet by default, and designed to be installed once and used every day without maintenance.

## Product Principles

- Personal use only.
- No internet dependency.
- No login or cloud sync.
- No sound effects or music.
- Local JSON storage.
- Lightweight runtime footprint.
- Incremental development, with every milestone staying runnable.

## Reminder Flow

Default reminder interval: 60 minutes.

When a reminder is due, the app currently:

1. Enters `REMINDER_APPEARING`.
2. Shows the transparent reminder window with opaque placeholder widgets.
3. Triggers the placeholder enter animation event.
4. Transitions to `WAITING_FOR_USER`.
5. Starts a 60-second ignore timeout.
6. Waits for the user to choose Done or Later.

If the user takes no action for 60 seconds, HydroBuddy treats that as Ignore.

## Daily Tracker

HydroBuddy tracks glasses of water for the current day.

Default goal: 12 glasses.

Progress is stored in `data/progress.json`:

```json
{
  "date": "",
  "glasses": 0,
  "goal": 12
}
```

The current Milestone 3 Done flow performs an in-memory placeholder increment only. Persistent daily progress updates are future work. The daily reset time defaults to `02:00`.

The current goal is stored alongside progress so a saved daily record remains understandable even if the user changes the default daily goal later.

## Settings

Default settings are stored in `data/settings.json`.

Settings include:

- Reminder interval.
- Snooze interval.
- Daily goal.
- Daily reset time.
- Start with Windows.
- Pause during fullscreen apps.
- Primary monitor only.
- Silent mode.

## Fullscreen Behavior

When fullscreen detection is enabled, HydroBuddy should delay reminders while another app is fullscreen. This protects games, videos, presentations, and focused work.

## Snooze

Default snooze interval: 10 minutes.

When the user chooses Later, the app hides the reminder and schedules exactly one 10-minute snooze timer. Ignore also schedules exactly one 10-minute snooze timer after the disappointed placeholder event.

## Startup

HydroBuddy should optionally start with Windows. Startup should be controlled by settings and should launch quietly without immediately showing UI unless a reminder is due.

## State Machine

HydroBuddy uses a Python `Enum` in `core/state_machine.py` to name these reminder states:

- `IDLE`: No reminder is visible; the app waits for the next timer.
- `REMINDER_APPEARING`: The reminder is being shown and the enter placeholder runs.
- `WAITING_FOR_USER`: The reminder is visible and waiting for Done, Later, or Ignore timeout.
- `PROCESSING_DONE`: The Done flow is being processed.
- `PROCESSING_LATER`: The Later flow is being processed.
- `PROCESSING_IGNORE`: The Ignore timeout flow is being processed.
- `EXITING`: The exit animation is playing before the companion hides.

## Animation Contract

Milestone 3 logs placeholder animation events only; no media playback is implemented.

`ENTER`

- Plays once.
- Next state: `IDLE`.

`IDLE`

- Loops.
- Waits for user interaction.

`DRINK`

- Plays once.
- Next state: `EXITING`.

`DISAPPOINTED`

- Plays once.
- Next state: `EXITING`.

`EXIT`

- Plays once.
- Application hides.

Expected asset paths:

- `assets/animations/enter.mp4`
- `assets/animations/idle.mp4`
- `assets/animations/drink.mp4`
- `assets/animations/disappointed.mp4`
- `assets/animations/exit.mp4`

Animation metadata is stored in `data/animations.json`. No code depends on it yet.

## Events

Future core and UI modules should communicate through named events rather than direct knowledge of each other's internals.

Event names are defined in `core/events.py`:

- `ReminderTriggered`
- `WaterDrank`
- `Snoozed`
- `AnimationFinished`
- `ReminderDismissed`
- `SettingsChanged`
- `DayReset`

There is no event dispatcher in Milestone 3.

## Theme

`ui/theme.py` defines constants for fonts, colors, button sizes, corner radius, spacing, window dimensions, speech bubble dimensions, and settings-control contrast. UI modules apply these values through their local stylesheets.

## Logging

HydroBuddy writes runtime logs to `logs/hydrobuddy.log` through `utils/logger.py`.

## Resources

`utils/resources.py` provides a reusable resource path helper for future source and packaged-executable runs.

## Tray Behavior

HydroBuddy should run from the Windows system tray.

Current tray actions:

- Open settings.
- Show reminder.
- Hide reminder.
- Quit HydroBuddy.

## Current Non-Goals

Milestone 3 does not implement media animation playback, persistent hydration statistics, daily reset, fullscreen detection, notifications, sounds, or Windows startup registration.
