"""Render previews of the character so the art can be reviewed without running the app.

Writes to preview/ (git-ignored):
    <animation>.png   contact sheet of evenly spaced frames
    story.gif         the full reminder flow on a mock desktop

Run:  .venv/Scripts/python tools/preview_character.py
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402
from PySide6.QtCore import QBuffer, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402

from hydrobuddy.ui.character import VIEW_H, VIEW_W, paint_character  # noqa: E402
from hydrobuddy.ui.character_anim import ANIMATIONS  # noqa: E402

PREVIEW_DIR = ROOT / "preview"
SHEET_FRAMES = 12
GIF_FPS = 25


def render(name: str, t: float, scale: float = 1.0) -> Image.Image:
    """Render one frame of an animation as a transparent PIL image."""

    animation = ANIMATIONS[name]
    image = QImage(int(VIEW_W * scale), int(VIEW_H * scale), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.scale(scale, scale)
    paint_character(painter, animation.pose_at(t), animation.sparkles_at(t))
    painter.end()
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGBA")


def contact_sheet(name: str) -> Image.Image:
    animation = ANIMATIONS[name]
    cols = 6
    rows = SHEET_FRAMES // cols
    sheet = Image.new("RGBA", (VIEW_W * cols, VIEW_H * rows), (38, 42, 54, 255))
    draw = ImageDraw.Draw(sheet)
    for i in range(SHEET_FRAMES):
        t = animation.duration * i / (SHEET_FRAMES - 1)
        x, y = (i % cols) * VIEW_W, (i // cols) * VIEW_H
        sheet.alpha_composite(render(name, t), (x, y))
        draw.text((x + 6, y + 4), f"{t:.2f}s", fill=(200, 205, 220, 255))
    return sheet


def mock_desktop(w: int, h: int, taskbar: int) -> Image.Image:
    """A stand-in for 'your screen' so the GIF shows the transparency."""

    desk = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(desk)
    for y in range(h - taskbar):
        k = y / (h - taskbar)
        draw.line([(0, y), (w, y)], fill=(int(44 + 50 * k), int(62 + 40 * k), int(112 + 46 * k)))
    draw.rounded_rectangle([24, 28, w - 150, h - taskbar - 36], 10, fill=(245, 246, 250))
    draw.rectangle([24, 28, w - 150, 54], fill=(226, 229, 237))
    for i, y in enumerate(range(74, h - taskbar - 60, 20)):
        draw.rounded_rectangle(
            [46, y, 46 + (200 if i % 3 else 290), y + 9], 4, fill=(206, 211, 223)
        )
    draw.rectangle([0, h - taskbar, w, h], fill=(32, 32, 38))
    for i in range(5):
        x = w // 2 - 95 + i * 40
        draw.rounded_rectangle([x, h - taskbar + 9, x + 26, h - 9], 5, fill=(82, 86, 98))
    return desk


def story_gif() -> None:
    taskbar, w, h = 44, 560, 400
    desk = mock_desktop(w, h, taskbar)
    bar = desk.crop((0, h - taskbar, w, h))
    plan = [("appear", 1), ("idle", 1), ("celebrate", 1), ("leave", 1), (None, 0.5),
            ("appear", 1), ("idle", 0.5), ("sad", 1), ("leave_sad", 1), (None, 0.5)]  # fmt: skip
    frames = []
    for name, portion in plan:
        duration = ANIMATIONS[name].duration * portion if name else portion
        for i in range(int(duration * GIF_FPS)):
            canvas = desk.copy()
            if name:
                sprite = render(name, i / GIF_FPS)
                canvas.alpha_composite(sprite, (w - VIEW_W - 20, h - taskbar - VIEW_H))
                canvas.paste(bar, (0, h - taskbar))  # taskbar on top: he comes from behind it
            frames.append(canvas.convert("RGB"))
    frames[0].save(
        PREVIEW_DIR / "story.gif",
        save_all=True,
        append_images=frames[1:],
        duration=1000 // GIF_FPS,
        loop=0,
    )


def main() -> None:
    app = QGuiApplication(sys.argv)  # noqa: F841 (needed for painting)
    PREVIEW_DIR.mkdir(exist_ok=True)
    for name in ANIMATIONS:
        contact_sheet(name).save(PREVIEW_DIR / f"{name}.png")
    story_gif()
    print(f"Wrote previews to {PREVIEW_DIR}")


if __name__ == "__main__":
    main()
