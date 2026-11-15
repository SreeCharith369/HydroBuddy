"""Double-click (or autostart) launcher: runs HydroBuddy without a console window.

Windows opens .pyw files with the system Python, which usually doesn't have
the app's libraries; only the project's .venv does. So if PySide6 is missing
here, this script restarts itself with .venv's Python. If that isn't possible
it says so in a message box, because without a console an error would
otherwise be invisible and the app would just seem to close.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "pythonw.exe"


def show_error(text: str) -> None:
    import ctypes

    ctypes.windll.user32.MessageBoxW(None, text, "HydroBuddy", 0x10)  # MB_ICONERROR


def main() -> int:
    try:
        import PySide6  # noqa: F401
    except ImportError:
        if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
            subprocess.Popen([str(VENV_PYTHON), str(ROOT / "run.pyw"), *sys.argv[1:]], cwd=ROOT)
            return 0
        show_error(
            "HydroBuddy can't start because its libraries aren't installed.\n\n"
            f"In the folder {ROOT} run:\n\n"
            "    py -3.12 -m venv .venv\n"
            "    .venv\\Scripts\\python -m pip install -r requirements.txt\n\n"
            "Or use the packaged app: dist\\HydroBuddy\\HydroBuddy.exe"
        )
        return 1

    from hydrobuddy.__main__ import main as run_app

    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
