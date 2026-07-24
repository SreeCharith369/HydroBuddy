# Roadmap

Every milestone should leave HydroBuddy in a runnable state.

## Milestone 1: Project Foundation

- Create initial repository structure.
- Add core documentation.
- Add dependency list.
- Add placeholder Python modules.

## Milestone 1.1: Foundation Refinement

- Align folders and module names with the planned architecture.
- Add default JSON data files.
- Define the application state vocabulary.
- Document the animation contract.
- Prepare the project for the first PySide6 shell.

## Milestone 1.2: Architecture Finalization

- Split UI placeholders into focused component modules.
- Add core event names.
- Add global default constants.
- Convert state names to a Python `Enum`.
- Add animation metadata JSON.
- Add theme constants.
- Add logging and resource-helper foundations.
- Update documentation for implementation readiness.

## Milestone 2: Minimal PySide6 Shell

- Create a PySide6 application object.
- Start the app hidden in the system tray.
- Add manual tray actions for show, hide, settings, and exit.
- Compose the reminder window from speech bubble, character placeholder, and action buttons.
- Add fade show/hide behavior.
- Load progress for display only.
- Load and save settings.
- Keep behavior manual; no reminder timers.

## Milestone 3: Reminder Scheduler and State Machine

- Add a single reusable reminder scheduler.
- Start a default 60-minute reminder timer when the app launches.
- Add a deterministic reminder state machine.
- Wire Done, Later, and no-action Ignore flows.
- Keep animation playback as placeholder log events.
- Keep the reminder window as a transparent top-level overlay with opaque placeholder widgets.
- Polish Settings window contrast so it renders correctly in Windows light and dark modes.

## Milestone 4: Settings and Storage Hardening

- Harden JSON load/save behavior.
- Add settings validation and recovery for missing or invalid files.
- Keep defaults recoverable if files are missing or invalid.
- Reconcile `core/constants.py` defaults with `data/settings.json`.

## Milestone 5: Daily Progress

- Implement the daily tracker.
- Store current date and glass count.
- Add reset-time rules without reminder scheduling.

## Milestone 6: Animation Playback

- Add MP4 playback for the companion.
- Connect animation completion to documented state transitions.
- Confirm idle looping.

## Milestone 7: Windows Integration

- Add start-with-Windows support.
- Add fullscreen detection.
- Add primary-monitor positioning.
- Confirm hidden-from-taskbar behavior.

## Milestone 8: Packaging

- Package HydroBuddy for Windows 11.
- Confirm install-once usage.
- Confirm startup behavior after reboot.
- Document release steps.
