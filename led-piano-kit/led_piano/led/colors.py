from __future__ import annotations

from typing import Tuple

Color = Tuple[int, int, int]

NOTE_NAME_COLORS: dict[int, Color] = {
    0: (255, 0, 0),
    1: (255, 80, 0),
    2: (255, 160, 0),
    3: (255, 220, 0),
    4: (180, 255, 0),
    5: (0, 255, 0),
    6: (0, 255, 120),
    7: (0, 140, 255),
    8: (0, 0, 255),
    9: (120, 0, 255),
    10: (200, 0, 255),
    11: (255, 0, 160),
}


def clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def note_color(note: int, hands: str, split_note: int, channel: int | None = None) -> Color:
    if hands == "off":
        return NOTE_NAME_COLORS[note % 12]

    if hands == "split":
        return (0, 120, 255) if note < split_note else (255, 80, 0)

    if hands == "auto":
        if channel is None:
            return NOTE_NAME_COLORS[note % 12]
        return (0, 120, 255) if channel == 0 else (255, 80, 0)

    return NOTE_NAME_COLORS[note % 12]


def apply_velocity(color: Color, velocity: int, mode: str) -> Color:
    scale = max(0.15, velocity / (5 * 127.0))

    if mode == "off":
        return color

    if mode == "brightness":
        return tuple(int(c * scale) for c in color)

    if mode == "color":
        # low velocity = a little whiter/softer, high velocity = closer to original hue
        white_mix = 1.0 - scale
        return tuple(min(255, int(c * scale + 255 * white_mix * 0.35)) for c in color)

    if mode == "both":
        white_mix = 1.0 - scale
        base = tuple(int(c * scale) for c in color)
        return tuple(min(255, int(b + 255 * white_mix * 0.20)) for b in base)

    return color


def scale_color(color: Color, factor: float) -> Color:
    return tuple(int(c * factor) for c in color)


def blend_add(dst: Color, src: Color) -> Color:
    return (
        clamp(dst[0] + src[0], 0, 255),
        clamp(dst[1] + src[1], 0, 255),
        clamp(dst[2] + src[2], 0, 255),
    )
