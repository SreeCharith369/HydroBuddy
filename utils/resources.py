"""Resource path helpers for HydroBuddy.

The packaged app may resolve bundled files differently than a source checkout.
This helper centralizes that distinction without loading resources itself.
"""

from pathlib import Path
import sys


def resource_path(relative_path: str) -> Path:
    """Return an absolute path for a project resource.

    When packaged, some tools expose bundled resources through `sys._MEIPASS`.
    When running from source, resources are resolved from the project root.
    """

    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base_path / relative_path
