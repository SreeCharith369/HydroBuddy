"""Build HydroBuddy as a standalone Windows app (no Python needed to run it).

Output: dist/HydroBuddy/HydroBuddy.exe (keep the whole dist/HydroBuddy folder together).

Run:  .venv/Scripts/python tools/build_exe.py
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BUILD = ROOT / "build"
DIST = ROOT / "dist"

# Qt modules HydroBuddy doesn't use; leaving them out keeps the app much smaller.
UNUSED_QT = [
    "QtQml", "QtQuick", "QtQuick3D", "QtQuickWidgets", "QtPdf", "QtPdfWidgets",
    "QtWebEngineCore", "QtWebEngineWidgets", "QtWebChannel", "QtWebSockets",
    "QtMultimedia", "QtMultimediaWidgets", "QtSql", "QtTest", "QtOpenGL",
    "QtOpenGLWidgets", "QtSvg", "QtSvgWidgets", "QtCharts", "QtDataVisualization",
    "Qt3DCore", "Qt3DRender", "QtBluetooth", "QtPositioning", "QtSensors",
    "QtSerialPort", "QtDesigner", "QtHelp", "QtUiTools", "QtXml", "QtConcurrent",
    "QtPrintSupport", "QtRemoteObjects", "QtScxml", "QtSpatialAudio", "QtTextToSpeech",
]  # fmt: skip


# Files PyInstaller's Qt hook copies in anyway that HydroBuddy never loads.
UNUSED_FILES = [
    "PySide6/opengl32sw.dll",  # software OpenGL fallback (we don't use OpenGL)
    "PySide6/Qt6Quick.dll",
    "PySide6/Qt6Qml.dll",
    "PySide6/Qt6QmlModels.dll",
    "PySide6/Qt6QmlMeta.dll",
    "PySide6/Qt6QmlWorkerScript.dll",
    "PySide6/Qt6Pdf.dll",
    "PySide6/plugins/imageformats/qpdf.dll",
    "PySide6/plugins/tls",  # Qt's TLS backends (no network use)
    "PySide6/plugins/networkinformation",
    "PySide6/translations",  # the UI is English only
    "libcrypto-3-x64.dll",  # OpenSSL for Qt's TLS backends
    "libssl-3-x64.dll",
]


def prune(app_dir: Path) -> None:
    internal = app_dir / "_internal"
    for relative in UNUSED_FILES:
        target = internal / relative
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def make_icon(path: Path) -> None:
    """Render the character into a multi-size .ico for the .exe."""

    from PIL import Image
    from PySide6.QtCore import QBuffer
    from PySide6.QtGui import QGuiApplication

    from hydrobuddy.ui.character import character_icon

    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    character_icon(256).save(buffer, "PNG")
    png = BUILD / "icon.png"
    png.write_bytes(bytes(buffer.data()))
    Image.open(png).save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)])


def main() -> None:
    import PyInstaller.__main__

    BUILD.mkdir(exist_ok=True)
    icon = BUILD / "HydroBuddy.ico"
    make_icon(icon)

    args = [
        str(ROOT / "run.pyw"),
        "--name=HydroBuddy",
        "--windowed",
        "--onedir",
        "--noconfirm",
        "--clean",
        f"--icon={icon}",
        f"--distpath={DIST}",
        f"--workpath={BUILD / 'pyinstaller'}",
        f"--specpath={BUILD}",
        f"--paths={ROOT}",
    ]
    for module in UNUSED_QT:
        args.append(f"--exclude-module=PySide6.{module}")
    for module in ("PIL", "pytest", "tkinter"):
        args.append(f"--exclude-module={module}")
    PyInstaller.__main__.run(args)

    exe = DIST / "HydroBuddy" / "HydroBuddy.exe"
    prune(exe.parent)
    size = sum(f.stat().st_size for f in exe.parent.rglob("*") if f.is_file())
    print(f"\nBuilt {exe}  ({size / 1_000_000:.0f} MB folder)")
    shutil.rmtree(BUILD / "pyinstaller", ignore_errors=True)


if __name__ == "__main__":
    main()
