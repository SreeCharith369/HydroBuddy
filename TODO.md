# TODO

## Milestone 1.1

- [x] Refine folder structure.
- [x] Rename modules to match the planned architecture.
- [x] Add default JSON data files.
- [x] Add state machine placeholder.
- [x] Document the animation contract.
- [x] Update project documentation.

## Milestone 1.2

- [x] Split UI placeholders into focused component modules.
- [x] Add core event definitions.
- [x] Convert state vocabulary to a Python `Enum`.
- [x] Add animation metadata JSON.
- [x] Add UI theme constants.
- [x] Add global default constants.
- [x] Add logging foundation.
- [x] Add resource path helper.
- [x] Store daily goal alongside progress.
- [x] Synchronize documentation.

## Verification

- [ ] Confirm Python 3.14 is available on PATH.
- [x] Use the local virtual environment for current verification.
- [x] Install `requirements.txt`.
- [x] Run application smoke checks through the PySide6 shell.

## Milestone 2 Preparation

- [x] Create minimal PySide6 application shell.
- [x] Add reminder window shell.
- [x] Wire component skeletons into a real window.
- [x] Add clean startup and shutdown path.
- [x] Keep timers, reminder logic, and animation playback out of Milestone 2.

## Milestone 3 Finalization

- [x] Add reminder scheduler with one active timer.
- [x] Add reminder state machine.
- [x] Add Done, Later, and Ignore flows.
- [x] Add placeholder enter, drink, disappointed, and exit animation events.
- [x] Verify 60-minute reminder, 10-minute snooze, and 60-second ignore timeout behavior.
- [x] Fix Settings window contrast for Windows light and dark modes.
- [x] Confirm reminder window top-level transparency setup.
- [x] Update documentation for Milestone 3 completion.

## Milestone 4 Preparation

- [ ] Add settings validation and error recovery.
- [ ] Add safer defaults when JSON files are missing.
- [ ] Decide how settings changes should notify future app services.
