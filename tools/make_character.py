"""Generate the HydroBuddy water-drop character as pixel-art sprite strips.

Everything is drawn from code: body shape, face, props, and motion.
Output follows the animation contract in docs/ANIMATION_PLAN.md:

    hydrobuddy/assets/character/<state>.png   horizontal strip, 1x pixels
    hydrobuddy/assets/character/character.json
    preview/                                   enlarged previews for humans

Run:  .venv/Scripts/python tools/make_character.py
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "hydrobuddy" / "assets" / "character"
PREVIEW_DIR = ROOT / "preview"

W, H = 48, 56  # logical pixels per frame; the bottom edge is the taskbar line
SCALE = 4  # nearest-neighbour upscale used by the app
CX = W / 2  # horizontal centre (falls between two pixel columns)
R = 11.0  # radius of the round bottom of the drop
TIP = 30.0  # height of the drop tip above the feet

C = {
    "outline": (27, 58, 107, 255),
    "body": (94, 200, 242, 255),
    "shade": (58, 159, 216, 255),
    "light": (222, 248, 255, 255),
    "eye": (20, 32, 60, 255),
    "shine": (255, 255, 255, 255),
    "cheek": (255, 140, 170, 255),
    "tongue": (232, 92, 112, 255),
    "glass": (215, 238, 246, 255),
    "glass_edge": (110, 140, 165, 255),
    "water": (64, 160, 235, 255),
    "spark": (255, 214, 80, 255),
    "tear": (150, 215, 255, 255),
}


@dataclass
class Pose:
    dy: float = 0.0  # feet offset; positive = lower (behind the taskbar)
    sx: float = 1.0  # horizontal squash/stretch
    sy: float = 1.0  # vertical squash/stretch
    eyes: str = "open"  # open | blink | happy | sad | wide
    mouth: str = "smile"  # smile | open | frown | flat | sip
    arms: str = "down"  # down | up | wave | hold
    glass: tuple[int, int] | None = None  # glass top-left, relative to face
    water: int = 3  # water rows left in the glass (0-3)
    tilt: bool = False  # glass tilted towards the mouth
    sparkles: list[tuple[int, int, int]] = field(default_factory=list)
    tear: float | None = None  # 0..1 progress of a falling tear


# --------------------------------------------------------------------------- #
# Drawing
# --------------------------------------------------------------------------- #


def _inside(px: float, py: float, base: float, sx: float, sy: float) -> bool:
    """Return whether pixel centre (px, py) lies inside the drop."""

    u = (px - CX) / sx
    v = (base - py) / sy
    if v < 0 or v > TIP:
        return False
    if u * u + (v - R) ** 2 <= R * R:
        return True
    if v >= R:
        s = (v - R) / (TIP - R)
        half = R * math.cos(s * math.pi / 2) ** 1.5
        return abs(u) <= half
    return False


def draw_frame(p: Pose) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    base = H + p.dy

    def put(x: int, y: int, color: str) -> None:
        if 0 <= x < W and 0 <= y < H:
            px[x, y] = C[color]

    # Body mask (computed over an extended range so clipping is natural).
    mask = {
        (x, y)
        for y in range(-20, H + 60)
        for x in range(W)
        if _inside(x + 0.5, y + 0.5, base, p.sx, p.sy)
    }

    for x, y in mask:
        u = (x + 0.5 - CX) / p.sx
        v = (base - (y + 0.5)) / p.sy
        edge = any(n not in mask for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
        if edge:
            put(x, y, "outline")
        elif u > R * 0.42 or v < R * 0.38:
            put(x, y, "shade")
        else:
            put(x, y, "body")

    # Highlight on the upper-left.
    hx, hy = CX - R * 0.48 * p.sx, base - R * 1.62 * p.sy
    for y in range(int(hy) - 4, int(hy) + 5):
        for x in range(int(hx) - 3, int(hx) + 4):
            if ((x + 0.5 - hx) / 1.6) ** 2 + ((y + 0.5 - hy) / 3.0) ** 2 <= 1 and (x, y) in mask:
                put(x, y, "light")
    put(int(hx) + 1, int(hy) - 5, "light")

    # Face anchor.
    fy = round(base - R * 1.02 * p.sy)
    lx, rx = 19, 27  # left columns of each 2-pixel-wide eye
    _draw_eyes(put, p.eyes, lx, rx, fy)
    _draw_mouth(put, p.mouth, fy + 4)
    if p.eyes in ("happy", "open", "wide"):
        for x in (16, 17, 30, 31):
            if (x, fy + 2) in mask:
                put(x, fy + 2, "cheek")

    _draw_arms(put, mask, p, base)

    if p.glass is not None:
        _draw_glass(put, CX + p.glass[0], fy + p.glass[1], p.water, p.tilt)

    if p.tear is not None:
        ty = fy + 2 + round(p.tear * 9)
        put(lx, ty, "shine")
        put(lx, ty + 1, "shine")
        put(lx + 1, ty + 1, "tear")
        put(lx, ty + 2, "outline")

    for sx_, sy_, size in p.sparkles:
        _draw_sparkle(put, sx_, sy_, size)

    return img


def _draw_eyes(put, kind: str, lx: int, rx: int, y: int) -> None:
    for x in (lx, rx):
        if kind == "open":
            for dy in (-1, 0, 1):
                put(x, y + dy, "eye")
                put(x + 1, y + dy, "eye")
            put(x, y - 1, "shine")
        elif kind == "wide":
            for dy in (-2, -1, 0, 1):
                put(x, y + dy, "eye")
                put(x + 1, y + dy, "eye")
            put(x, y - 2, "shine")
        elif kind == "blink":
            put(x - 1, y, "eye")
            put(x, y, "eye")
            put(x + 1, y, "eye")
            put(x + 2, y, "eye")
        elif kind == "happy":  # ^ ^
            put(x - 1, y, "eye")
            put(x, y - 1, "eye")
            put(x + 1, y - 1, "eye")
            put(x + 2, y, "eye")
        elif kind == "sad":
            for dy in (0, 1):
                put(x, y + dy, "eye")
                put(x + 1, y + dy, "eye")
            # slanted brows: high in the middle, low at the outside
            if x == lx:
                put(x - 1, y - 2, "eye")
                put(x, y - 2, "eye")
                put(x + 1, y - 3, "eye")
            else:
                put(x, y - 3, "eye")
                put(x + 1, y - 2, "eye")
                put(x + 2, y - 2, "eye")


def _draw_mouth(put, kind: str, y: int) -> None:
    if kind == "smile":
        put(22, y - 1, "eye")
        put(23, y, "eye")
        put(24, y, "eye")
        put(25, y - 1, "eye")
    elif kind == "open":
        for x in (22, 23, 24, 25):
            put(x, y - 1, "eye")
        put(22, y, "eye")
        put(23, y, "tongue")
        put(24, y, "tongue")
        put(25, y, "eye")
        put(23, y + 1, "eye")
        put(24, y + 1, "eye")
    elif kind == "frown":
        put(22, y, "eye")
        put(23, y - 1, "eye")
        put(24, y - 1, "eye")
        put(25, y, "eye")
    elif kind == "flat":
        put(23, y, "eye")
        put(24, y, "eye")
    elif kind == "sip":
        put(23, y - 1, "eye")
        put(24, y - 1, "eye")
        put(23, y, "eye")
        put(24, y, "eye")


def _edges(mask: set[tuple[int, int]], y: int) -> tuple[int, int] | None:
    xs = [x for x, yy in mask if yy == y]
    return (min(xs), max(xs)) if xs else None


def _draw_arms(put, mask, p: Pose, base: float) -> None:
    ay = round(base - R * 0.85 * p.sy)
    edges = _edges(mask, ay)
    if edges is None:
        return
    left, right = edges[0] - 1, edges[1] + 1

    def left_arm(kind: str) -> None:
        if kind == "down":
            put(left, ay, "outline")
            put(left - 1, ay + 1, "outline")
        elif kind in ("up", "wave"):
            put(left, ay, "outline")
            put(left - 1, ay - 1, "outline")
            put(left - 2, ay - 2, "outline")

    def right_arm(kind: str) -> None:
        if kind == "down":
            put(right, ay, "outline")
            put(right + 1, ay + 1, "outline")
        elif kind == "up":
            put(right, ay, "outline")
            put(right + 1, ay - 1, "outline")
            put(right + 2, ay - 2, "outline")
        elif kind == "wave":
            put(right, ay, "outline")
            put(right + 1, ay - 1, "outline")
            put(right + 1, ay - 2, "outline")
            put(right + 2, ay - 3, "outline")

    if p.arms == "hold":
        left_arm("down")
        put(right, ay, "outline")  # the glass covers the hand
    elif p.arms == "wave":
        left_arm("down")
        right_arm("wave")
    else:
        left_arm(p.arms)
        right_arm(p.arms)


def _draw_glass(put, gx: float, gy: int, water: int, tilt: bool) -> None:
    x0 = round(gx)
    rows, cols = 8, 6
    for row in range(rows):
        shift = -1 if tilt and row < 4 else 0
        for col in range(cols):
            x, y = x0 + col + shift, gy + row
            if col in (0, cols - 1) or row == rows - 1:
                put(x, y, "outline")
            elif row >= rows - 1 - water * 2:
                put(x, y, "water")
            else:
                put(x, y, "glass")


def _draw_sparkle(put, x: int, y: int, size: int) -> None:
    put(x, y, "spark")
    for d in range(1, size + 1):
        put(x + d, y, "spark")
        put(x - d, y, "spark")
        put(x, y + d, "spark")
        put(x, y - d, "spark")


# --------------------------------------------------------------------------- #
# Animations
# --------------------------------------------------------------------------- #


def appear() -> list[Pose]:
    """Pop up from behind the taskbar, overshoot, land, wobble."""

    rise = [
        (40, 0.85, 1.20, "wide", "open"),
        (28, 0.85, 1.22, "wide", "open"),
        (17, 0.88, 1.18, "wide", "open"),
        (8, 0.92, 1.10, "wide", "open"),
        (1, 0.96, 1.05, "wide", "open"),
        (-4, 1.00, 1.00, "open", "open"),
        (-6, 1.00, 1.00, "open", "smile"),
        (-4, 0.98, 1.02, "open", "smile"),
        (0, 1.22, 0.80, "happy", "smile"),
        (0, 0.92, 1.08, "open", "smile"),
        (0, 1.06, 0.95, "open", "smile"),
        (0, 0.98, 1.02, "open", "smile"),
        (0, 1.00, 1.00, "open", "smile"),
    ]
    return [
        Pose(dy=d, sx=a, sy=b, eyes=e, mouth=m, arms="up" if d < 0 else "down")
        for d, a, b, e, m in rise
    ]


def idle() -> list[Pose]:
    """Gentle breathing loop with a blink."""

    frames = []
    for i in range(16):
        t = math.sin(2 * math.pi * i / 16)
        eyes = "blink" if i in (11, 12) else "open"
        frames.append(Pose(sx=1 - 0.035 * t, sy=1 + 0.035 * t, eyes=eyes))
    return frames


def celebrate() -> list[Pose]:
    """Lift a glass, sip, cheer with a jump."""

    g = (3, -1)  # glass pressed to the mouth
    seq = [
        Pose(arms="hold", glass=(8, 8)),
        Pose(arms="hold", glass=(7, 4)),
        Pose(arms="hold", glass=(5, 1), eyes="happy"),
        Pose(arms="hold", glass=g, tilt=True, eyes="blink", mouth="sip", water=3),
        Pose(arms="hold", glass=g, tilt=True, eyes="blink", mouth="sip", water=2, sy=1.02),
        Pose(arms="hold", glass=g, tilt=True, eyes="blink", mouth="sip", water=2),
        Pose(arms="hold", glass=g, tilt=True, eyes="blink", mouth="sip", water=1, sy=1.02),
        Pose(arms="hold", glass=g, tilt=True, eyes="blink", mouth="sip", water=0),
        Pose(arms="hold", glass=(7, 4), water=0, eyes="happy", mouth="open"),
        Pose(sx=1.15, sy=0.85, eyes="happy", mouth="open"),
        Pose(
            dy=-5,
            sx=0.9,
            sy=1.12,
            eyes="happy",
            mouth="open",
            arms="up",
            sparkles=[(8, 14, 1), (40, 18, 1)],
        ),
        Pose(
            dy=-10,
            sx=0.95,
            sy=1.06,
            eyes="happy",
            mouth="open",
            arms="up",
            sparkles=[(6, 10, 2), (41, 13, 2), (24, 1, 1)],
        ),
        Pose(
            dy=-12,
            eyes="happy",
            mouth="open",
            arms="up",
            sparkles=[(5, 8, 1), (42, 10, 1), (24, 0, 2), (12, 3, 1)],
        ),
        Pose(
            dy=-9,
            sx=0.96,
            sy=1.05,
            eyes="happy",
            mouth="open",
            arms="up",
            sparkles=[(36, 4, 1), (12, 3, 0)],
        ),
        Pose(dy=-4, sx=0.92, sy=1.10, eyes="happy", mouth="smile", arms="up"),
        Pose(sx=1.18, sy=0.84, eyes="happy", mouth="smile"),
        Pose(sx=0.95, sy=1.05, eyes="happy", mouth="smile"),
        Pose(eyes="happy", mouth="smile"),
    ]
    return seq


def sad() -> list[Pose]:
    """Droop, frown, a single tear."""

    frames = []
    for i in range(14):
        k = min(1.0, i / 4)
        frames.append(
            Pose(
                sx=1 + 0.08 * k,
                sy=1 - 0.09 * k,
                eyes="open" if i < 2 else "sad",
                mouth="flat" if i < 2 else "frown",
                tear=(i - 4) / 7 if 4 <= i <= 11 else None,
            )
        )
    return frames


def leave() -> list[Pose]:
    """Wave, hop, sink back behind the taskbar."""

    return [
        Pose(arms="wave", eyes="happy"),
        Pose(arms="down", eyes="happy"),
        Pose(arms="wave", eyes="happy"),
        Pose(sx=1.15, sy=0.86, eyes="happy"),
        Pose(dy=-4, sx=0.88, sy=1.15, eyes="wide", mouth="open"),
        Pose(dy=2, sx=0.86, sy=1.18, eyes="wide", mouth="open"),
        Pose(dy=12, sx=0.86, sy=1.18, eyes="blink"),
        Pose(dy=24, sx=0.88, sy=1.15, eyes="blink"),
        Pose(dy=36, sx=0.9, sy=1.1, eyes="blink"),
        Pose(dy=48, eyes="blink"),
    ]


STATES = {
    # name: (builder, fps, loop, next)
    "appear": (appear, 14, False, "idle"),
    "idle": (idle, 8, True, None),
    "celebrate": (celebrate, 12, False, "leave"),
    "sad": (sad, 10, False, "leave"),
    "leave": (leave, 14, False, None),
}


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #


def strip(frames: list[Image.Image]) -> Image.Image:
    sheet = Image.new("RGBA", (W * len(frames), H), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        sheet.paste(frame, (i * W, 0))
    return sheet


def fake_desktop(w: int, h: int, taskbar: int) -> Image.Image:
    """A stand-in for 'your screen' so previews show the transparency."""

    bg = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(bg)
    for y in range(h - taskbar):
        t = y / (h - taskbar)
        draw.line(
            [(0, y), (w, y)], fill=(int(40 + 60 * t), int(60 + 40 * t), int(110 + 50 * t), 255)
        )
    # a pretend app window
    draw.rounded_rectangle([20, 24, w - 120, h - taskbar - 30], 8, fill=(245, 246, 250, 255))
    draw.rectangle([20, 24, w - 120, 46], fill=(225, 228, 236, 255))
    for i, y in enumerate(range(64, h - taskbar - 50, 18)):
        draw.rounded_rectangle(
            [40, y, 40 + (180 if i % 3 else 260), y + 8], 4, fill=(205, 210, 222, 255)
        )
    draw.rectangle([0, h - taskbar, w, h], fill=(32, 32, 38, 255))
    for i in range(5):
        draw.rounded_rectangle(
            [w // 2 - 90 + i * 38, h - taskbar + 8, w // 2 - 64 + i * 38, h - 8],
            4,
            fill=(80, 84, 96, 255),
        )
    return bg


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(exist_ok=True)

    contract = {"frame_size": [W, H], "scale": SCALE, "anchor": "bottom-center", "states": {}}
    rendered: dict[str, list[Image.Image]] = {}

    for name, (builder, fps, loop, nxt) in STATES.items():
        frames = [draw_frame(p) for p in builder()]
        rendered[name] = frames
        strip(frames).save(OUT_DIR / f"{name}.png")
        contract["states"][name] = {
            "file": f"{name}.png",
            "frames": len(frames),
            "fps": fps,
            "loop": loop,
            "next": nxt,
        }
        big = strip(frames).resize((W * len(frames) * SCALE, H * SCALE), Image.NEAREST)
        big.save(PREVIEW_DIR / f"{name}_strip.png")

    (OUT_DIR / "character.json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    # Full story preview on a fake desktop: appear -> idle x2 -> celebrate -> leave,
    # then appear -> idle -> sad -> leave.
    story = (
        [("appear", f) for f in rendered["appear"]]
        + [("idle", f) for f in rendered["idle"] * 2]
        + [("celebrate", f) for f in rendered["celebrate"]]
        + [("leave", f) for f in rendered["leave"]]
        + [("blank", None)] * 6
        + [("appear", f) for f in rendered["appear"]]
        + [("idle", f) for f in rendered["idle"]]
        + [("sad", f) for f in rendered["sad"]]
        + [("leave", f) for f in rendered["leave"]]
        + [("blank", None)] * 6
    )
    taskbar = 40
    dw, dh = 520, 360
    desk = fake_desktop(dw, dh, taskbar)
    gif_frames, durations = [], []
    for name, frame in story:
        canvas = desk.copy()
        if frame is not None:
            sprite = frame.resize((W * 3, H * 3), Image.NEAREST)
            canvas.alpha_composite(sprite, (dw - W * 3 - 16, dh - taskbar - H * 3))
            # The taskbar is drawn on top so he really comes from *behind* it.
            canvas.paste(desk.crop((0, dh - taskbar, dw, dh)), (0, dh - taskbar))
        gif_frames.append(canvas.convert("RGB"))
        fps = STATES[name][1] if name in STATES else 10
        durations.append(int(1000 / fps))
    gif_frames[0].save(
        PREVIEW_DIR / "story.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"Wrote {len(STATES)} strips to {OUT_DIR} and previews to {PREVIEW_DIR}")


if __name__ == "__main__":
    main()
