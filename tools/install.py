"""Install the built app to a fixed place outside OneDrive, and start it from there.

Why: an app that starts at sign-in shouldn't live in a synced or movable folder.
OneDrive may turn its files into cloud-only placeholders (the app then can't load
and vanishes silently), and moving the project folder breaks the startup entry.

What it does:
  1. Closes the running HydroBuddy, if any (your data is saved, nothing is lost).
  2. Copies dist/HydroBuddy to %LOCALAPPDATA%/Programs/HydroBuddy.
  3. Adds a Start menu shortcut, "HydroBuddy".
  4. Starts the installed copy. If "Start with Windows" is on, the app points
     the startup entry at the installed copy by itself.

Your data (%APPDATA%/HydroBuddy) is not touched.

Run:  .venv/Scripts/python tools/build_exe.py   (first, if dist/ is missing or old)
      .venv/Scripts/python tools/install.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILT = ROOT / "dist" / "HydroBuddy"
TARGET = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "HydroBuddy"
SHORTCUT = (
    Path(os.environ["APPDATA"])
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "HydroBuddy.lnk"
)


def running() -> bool:
    out = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq HydroBuddy.exe", "/NH"], capture_output=True, text=True
    ).stdout
    return "HydroBuddy.exe" in out


def stop_running_copy() -> None:
    if not running():
        return
    print("Closing the running HydroBuddy…")
    for exe in (TARGET / "HydroBuddy.exe", BUILT / "HydroBuddy.exe"):
        if exe.exists():
            subprocess.run([str(exe), "--quit"], timeout=30)
            break
    for _ in range(50):
        if not running():
            return
        time.sleep(0.2)
    raise SystemExit("HydroBuddy didn't close; quit it from the tray icon and run this again.")


def make_shortcut() -> None:
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:HB_LINK);"
        "$s.TargetPath = $env:HB_EXE; $s.WorkingDirectory = $env:HB_DIR;"
        "$s.Description = 'HydroBuddy water reminder'; $s.Save()"
    )
    env = {
        **os.environ,
        "HB_LINK": str(SHORTCUT),
        "HB_EXE": str(TARGET / "HydroBuddy.exe"),
        "HB_DIR": str(TARGET),
    }
    subprocess.run(["powershell", "-NoProfile", "-Command", script], env=env, check=True)


def main() -> int:
    if not (BUILT / "HydroBuddy.exe").exists():
        print("No build found. Run first:  .venv/Scripts/python tools/build_exe.py")
        return 1
    stop_running_copy()
    print(f"Installing to {TARGET}")
    shutil.rmtree(TARGET, ignore_errors=True)
    shutil.copytree(BUILT, TARGET)
    make_shortcut()
    print(f"Start menu shortcut: {SHORTCUT}")
    subprocess.Popen([str(TARGET / "HydroBuddy.exe")], cwd=TARGET, close_fds=True)
    print("Started the installed HydroBuddy. Look for the water drop near the clock.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
