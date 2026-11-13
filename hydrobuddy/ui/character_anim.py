"""Character poses and animations as pure data (no Qt, so it is unit-testable).

A ``Pose`` describes the water drop at one instant. An ``Animation`` maps a
time in seconds to a pose. ``hydrobuddy.ui.character`` turns poses into pixels.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, fields, replace

HIDDEN_DY = 175.0  # far enough below the taskbar line to be fully out of sight


@dataclass(frozen=True)
class Pose:
    dy: float = 0.0  # feet offset in px; positive = lower (behind the taskbar)
    sx: float = 1.0  # horizontal squash/stretch
    sy: float = 1.0  # vertical squash/stretch
    arm_l: float = -50.0  # arm angle in degrees above horizontal
    arm_r: float = -50.0
    arm_r_len: float = 26.0
    sip: float = 0.0  # 0..1 = right hand travels from its arm position to the mouth
    eye_open: float = 1.0  # 0 = closed, 1 = normal, >1 = wide
    glass: float = 0.0  # glass size in the right hand; 0 = no glass
    tilt: float = 0.0  # glass rotation in degrees (negative = towards the mouth)
    water: float = 1.0  # how full the glass is, 0..1
    tear: float = -1.0  # 0..1 = a tear falling; outside that range = no tear
    eyes: str = "open"  # open | happy | sad
    mouth: str = "smile"  # smile | open | frown | sip


_NUMERIC = tuple(f.name for f in fields(Pose) if f.type == "float")

_EASE: dict[str, Callable[[float], float]] = {
    "smooth": lambda u: u * u * (3 - 2 * u),
    "in": lambda u: u * u,
    "out": lambda u: 1 - (1 - u) ** 2,
}


def _blend(a: Pose, b: Pose, u: float) -> Pose:
    """Numbers glide from ``a`` to ``b``; face styles stay as ``a`` until ``b`` is reached."""

    return replace(a, **{n: getattr(a, n) + (getattr(b, n) - getattr(a, n)) * u for n in _NUMERIC})


def keyframes(*keys: tuple) -> Callable[[float], Pose]:
    """Build a pose function from ``(time, pose[, easing])`` keys."""

    def pose_at(t: float) -> Pose:
        if t <= keys[0][0]:
            return keys[0][1]
        for prev, nxt in zip(keys, keys[1:], strict=False):
            if t <= nxt[0]:
                ease = _EASE[nxt[2] if len(nxt) > 2 else "smooth"]
                return _blend(prev[1], nxt[1], ease((t - prev[0]) / (nxt[0] - prev[0])))
        return keys[-1][1]

    return pose_at


@dataclass(frozen=True)
class Sparkle:
    x: float  # position in view coordinates
    y: float
    start: float  # seconds into the animation
    life: float
    size: float


@dataclass(frozen=True)
class Animation:
    name: str
    duration: float
    pose_at: Callable[[float], Pose]
    loop: bool = False
    next: str | None = None
    sparkles: tuple[Sparkle, ...] = ()

    def sparkles_at(self, t: float) -> list[tuple[float, float, float]]:
        """Return ``(x, y, size)`` for each sparkle visible at time ``t``."""

        out = []
        for s in self.sparkles:
            progress = (t - s.start) / s.life
            if 0 < progress < 1:
                out.append((s.x, s.y, s.size * math.sin(math.pi * progress)))
        return out


# --------------------------------------------------------------------------- #
# The animations
# --------------------------------------------------------------------------- #

NEUTRAL = Pose()
_UP = {"arm_l": 58.0, "arm_r": 58.0}


def _appear() -> Callable[[float], Pose]:
    """Pop up from behind the taskbar, overshoot, land with a squash, wobble."""

    wide = {"eye_open": 1.25, "mouth": "open", **_UP}
    return keyframes(
        (0.00, Pose(dy=HIDDEN_DY, sx=0.86, sy=1.20, **wide)),
        (0.30, Pose(dy=-22, sx=0.90, sy=1.12, **wide), "out"),
        (0.42, Pose(dy=-30, **wide)),
        (0.58, Pose(dy=0, sx=0.95, sy=1.06, eyes="happy", **_UP), "in"),
        (0.66, Pose(sx=1.20, sy=0.80, eyes="happy")),
        (0.78, Pose(sx=0.94, sy=1.07, eyes="happy")),
        (0.88, Pose(sx=1.04, sy=0.97)),
        (1.00, NEUTRAL),
    )


def _idle(t: float) -> Pose:
    """Gentle breathing, with a blink once per loop."""

    breath = math.sin(2 * math.pi * t / 1.6)
    since_blink = t - 2.3
    eye_open = abs(1 - since_blink / 0.1) if 0 <= since_blink <= 0.2 else 1.0
    return Pose(
        sx=1 - 0.025 * breath,
        sy=1 + 0.025 * breath,
        arm_l=-50 + 4 * breath,
        arm_r=-50 + 4 * breath,
        eye_open=eye_open,
    )


def _celebrate() -> Callable[[float], Pose]:
    """A glass pops into his hand, he drinks it, then jumps for joy holding it up."""

    size = 1.2
    side = {"arm_r": -18.0, "arm_r_len": 30.0}  # holding the glass out to the side
    lips = {**side, "sip": 1.0, "eye_open": 0.0, "mouth": "sip", "glass": size}
    joy = {"eyes": "happy", "mouth": "open"}
    empty = {"glass": size, "water": 0.0}
    return keyframes(
        (0.00, Pose(**side)),
        (0.14, Pose(glass=size * 1.25, **side)),
        (0.24, Pose(glass=size, **side)),
        (0.55, Pose(tilt=-38, **lips)),
        (0.70, Pose(tilt=-42, water=0.75, sx=0.98, sy=1.03, **lips)),
        (0.85, Pose(tilt=-46, water=0.50, **lips)),
        (1.00, Pose(tilt=-50, water=0.25, sx=0.98, sy=1.03, **lips)),
        (1.15, Pose(tilt=-54, water=0.0, **lips)),
        (1.40, Pose(**empty, **side, **joy)),
        (1.52, Pose(sx=1.15, sy=0.85, **empty, **side, **joy)),
        (1.68, Pose(dy=-40, sx=0.92, sy=1.10, tilt=10, **empty, **_UP, **joy), "out"),
        (1.82, Pose(dy=-52, tilt=10, **empty, **_UP, **joy)),
        (1.98, Pose(dy=-8, sx=0.94, sy=1.08, tilt=10, **empty, **_UP, **joy), "in"),
        (2.05, Pose(sx=1.18, sy=0.84, **empty, **side, **joy)),
        (2.20, Pose(sx=0.95, sy=1.05, eyes="happy")),
        (2.32, Pose(eyes="happy")),
        (2.50, Pose(eyes="happy")),
    )


_DROOP = {"sx": 1.07, "sy": 0.91, "arm_l": -72.0, "arm_r": -72.0, "eyes": "sad", "mouth": "frown"}


def _sad() -> Callable[[float], Pose]:
    """Droop, frown, one tear."""

    return keyframes(
        (0.00, NEUTRAL),
        (0.25, Pose(eyes="sad", mouth="frown")),
        (0.65, Pose(**_DROOP)),
        (0.80, Pose(tear=0.0, **_DROOP)),
        (1.60, Pose(tear=1.0, **_DROOP), "in"),
        (2.00, Pose(tear=1.0, **_DROOP)),
    )


def _leave() -> Callable[[float], Pose]:
    """Wave goodbye, hop, dive back behind the taskbar."""

    def wave(angle: float) -> Pose:
        return Pose(eyes="happy", arm_r=angle, arm_r_len=34.0)

    surprised = {"eye_open": 1.25, "mouth": "open"}
    return keyframes(
        (0.00, Pose(eyes="happy")),
        (0.12, wave(62)),
        (0.24, wave(28)),
        (0.36, wave(62)),
        (0.48, wave(28)),
        (0.60, wave(62)),
        (0.72, Pose(eyes="happy", sx=1.14, sy=0.86)),
        (0.84, Pose(dy=-14, sx=0.90, sy=1.14, **surprised), "out"),
        (0.92, Pose(dy=-10, sx=0.90, sy=1.14, **surprised)),
        (1.25, Pose(dy=HIDDEN_DY, sx=0.88, sy=1.16, eye_open=0.0, mouth="open"), "in"),
    )


def _leave_sad() -> Callable[[float], Pose]:
    """Sink away quietly, still sad."""

    return keyframes(
        (0.00, Pose(tear=1.0, **_DROOP)),
        (0.15, Pose(tear=1.0, **{**_DROOP, "sx": 1.10, "sy": 0.88})),
        (0.90, Pose(dy=HIDDEN_DY, tear=1.0, **_DROOP), "in"),
    )


_CHEER_SPARKLES = (
    Sparkle(38, 78, 1.58, 0.55, 11),
    Sparkle(186, 60, 1.64, 0.55, 13),
    Sparkle(70, 30, 1.72, 0.50, 9),
    Sparkle(150, 22, 1.78, 0.50, 10),
    Sparkle(24, 130, 1.84, 0.45, 8),
    Sparkle(204, 118, 1.88, 0.45, 9),
)

ANIMATIONS: dict[str, Animation] = {
    a.name: a
    for a in (
        Animation("appear", 1.00, _appear(), next="idle"),
        Animation("idle", 3.20, _idle, loop=True),
        Animation("celebrate", 2.50, _celebrate(), next="leave", sparkles=_CHEER_SPARKLES),
        Animation("sad", 2.00, _sad(), next="leave_sad"),
        Animation("leave", 1.25, _leave()),
        Animation("leave_sad", 0.90, _leave_sad()),
    )
}
