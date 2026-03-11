from __future__ import annotations

from led_piano.config import HIGHEST_NOTE, LOWEST_NOTE, WHITE_KEY_LEDS


def build_note_map() -> list[int]:
    """Build a 73-note LED map from calibrated white-key anchors."""
    full: list[int] = []
    for oct_idx in range(6):
        base = oct_idx * 7
        c = WHITE_KEY_LEDS[base + 0]
        d = WHITE_KEY_LEDS[base + 1]
        e = WHITE_KEY_LEDS[base + 2]
        f = WHITE_KEY_LEDS[base + 3]
        g = WHITE_KEY_LEDS[base + 4]
        a = WHITE_KEY_LEDS[base + 5]
        b = WHITE_KEY_LEDS[base + 6]

        cs = round((c + d) / 2)
        ds = round((d + e) / 2)
        fs = round((f + g) / 2)
        gs = round((g + a) / 2)
        a_s = round((a + b) / 2)

        full.extend([c, cs, d, ds, e, f, fs, g, gs, a, a_s, b])

    full.append(WHITE_KEY_LEDS[-1])
    return full


NOTE_LED_MAP = build_note_map()


def midi_note_to_index(note: int, base_note: int = LOWEST_NOTE) -> int | None:
    high = base_note + (HIGHEST_NOTE - LOWEST_NOTE)
    if note < base_note or note > high:
        return None
    return note - base_note


def midi_note_to_led(note: int, base_note: int = LOWEST_NOTE, reverse: bool = False) -> int | None:
    idx = midi_note_to_index(note, base_note=base_note)
    if idx is None:
        return None
    led = NOTE_LED_MAP[idx]
    if reverse:
        return WHITE_KEY_LEDS[-1] - led
    return led
