from __future__ import annotations

from dataclasses import dataclass, field

import mido


@dataclass
class Step:
    notes: list[int]
    start_sec: float
    hands: dict[int, str] = field(default_factory=dict)


def _pack_step(events: list[dict], start_sec: float) -> Step:
    notes = sorted(set(ev["note"] for ev in events))
    hands: dict[int, str] = {}
    for ev in events:
        note = ev["note"]
        hand = ev["hand"]
        if hand is not None and note not in hands:
            hands[note] = hand
    return Step(notes=notes, start_sec=start_sec, hands=hands)


def build_steps_from_midi(
    path: str,
    group_threshold_sec: float = 0.08,
    hand_source: str = "track",
    split_note: int = 60,
) -> list[Step]:
    """
    Build learn steps from a MIDI file.

    hand_source:
      - "track": use track index to infer hand
      - "channel": use MIDI channel to infer hand
      - "split": use split_note to infer hand
    """
    mid = mido.MidiFile(path)
    note_events: list[dict] = []

    # iterate track-by-track so we retain track index
    for track_idx, track in enumerate(mid.tracks):
        abs_time = 0.0
        for msg in track:
            abs_time += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                hand = None
                if hand_source == "track":
                    hand = "right" if track_idx == 0 else "left"
                elif hand_source == "channel":
                    if hasattr(msg, "channel"):
                        hand = "left" if msg.channel == 0 else "right"
                elif hand_source == "split":
                    hand = "left" if msg.note < split_note else "right"

                note_events.append(
                    {
                        "time": abs_time,
                        "note": msg.note,
                        "hand": hand,
                    }
                )

    if not note_events:
        return []

    note_events.sort(key=lambda x: x["time"])

    steps: list[Step] = []
    current_events = [note_events[0]]
    current_start = note_events[0]["time"]

    for ev in note_events[1:]:
        if ev["time"] - current_start <= group_threshold_sec:
            current_events.append(ev)
        else:
            steps.append(_pack_step(current_events, current_start))
            current_events = [ev]
            current_start = ev["time"]

    steps.append(_pack_step(current_events, current_start))
    return steps


class LearnEngine:
    def __init__(
        self,
        steps: list[Step],
        chord_press_window_ms: int = 200,
        min_hold_ms: int = 80,
        loop_start_step: int | None = None,
        loop_end_step: int | None = None,
    ):
        self.steps = steps
        self.loop_start = 0 if loop_start_step is None else max(0, loop_start_step)
        self.loop_end = len(steps) - 1 if loop_end_step is None else min(len(steps) - 1, loop_end_step)
        if self.loop_start > self.loop_end:
            self.loop_start, self.loop_end = 0, len(steps) - 1

        self.index = self.loop_start
        self.chord_press_window_sec = chord_press_window_ms / 1000.0
        self.min_hold_sec = min_hold_ms / 1000.0
        self.pressed_notes: set[int] = set()
        self.press_times: dict[int, float] = {}
        self.sustain_on = False

    def current(self) -> Step | None:
        if self.index < 0 or self.index >= len(self.steps):
            return None
        return self.steps[self.index]

    def next(self) -> Step | None:
        next_idx = self.index + 1
        if next_idx <= self.loop_end and next_idx < len(self.steps):
            return self.steps[next_idx]
        return None

    def is_finished(self) -> bool:
        return self.index > self.loop_end

    def reset_to_loop_start(self) -> None:
        self.index = self.loop_start
        self.pressed_notes.clear()
        self.press_times.clear()

    def set_sustain(self, value: int, threshold: int = 64) -> None:
        self.sustain_on = value >= threshold

    def press(self, note: int, now_sec: float) -> None:
        self.pressed_notes.add(note)
        self.press_times[note] = now_sec

    def release(self, note: int) -> None:
        if self.sustain_on:
            return
        self.pressed_notes.discard(note)

    def wrong_note_pressed(self, note: int) -> bool:
        current = self.current()
        return current is not None and note not in set(current.notes)

    def check_advance(self, now_sec: float) -> bool:
        current = self.current()
        if current is None:
            return False

        required = set(current.notes)
        if not required.issubset(self.pressed_notes):
            return False

        times = [self.press_times.get(n) for n in required]
        if any(t is None for t in times):
            return False

        earliest = min(times)
        latest = max(times)
        if latest - earliest > self.chord_press_window_sec:
            return False

        for n in required:
            if now_sec - self.press_times[n] < self.min_hold_sec:
                return False

        self.index += 1
        return True
