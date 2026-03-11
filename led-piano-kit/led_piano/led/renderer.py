from __future__ import annotations

import time
from typing import Dict, Tuple

from led_piano.led.colors import apply_velocity, blend_add, note_color, scale_color
from led_piano.led.mapping import midi_note_to_led

Color = Tuple[int, int, int]
NoteState = Tuple[int, Color, int]


class Renderer:
    def __init__(self, pixels, led_count: int, args):
        self.pixels = pixels
        self.led_count = led_count
        self.args = args
        self.active_notes: Dict[int, NoteState] = {}
        self.sustained_notes: Dict[int, NoteState] = {}
        self.sustain_on = False
        self.trail = [(0, 0, 0)] * led_count

    def _note_to_led(self, note: int) -> int | None:
        return midi_note_to_led(note, base_note=self.args.base_note, reverse=self.args.reverse)
    
    def _note_to_color(self, note: int, velocity: int, channel: int | None = None):
        color = note_color(note, self.args.hands, self.args.split_note, channel=channel)
        color = apply_velocity(color, velocity, self.args.velocity_mode)
        return color

    def clear(self) -> None:
        self.pixels.fill((0, 0, 0))
        self.pixels.show()

    def note_on(self, note: int, velocity: int, channel: int | None = None) -> None:
        led = self._note_to_led(note)
        if led is None:
            return

        color = self._note_to_color(note, velocity, channel=channel)

        self.sustained_notes.pop(note, None)
        self.active_notes[note] = (led, color, velocity)

        if self.args.style == "solid":
            self.render_solid_frame()
        elif self.args.style == "trail":
            self.inject_trail(led, color)
        elif self.args.style == "gradient":
            self.render_gradient_frame()

    def note_off(self, note: int) -> None:
        if note in self.active_notes:
            data = self.active_notes.pop(note)
            if self.sustain_on:
                self.sustained_notes[note] = data

        if self.args.style == "solid":
            self.render_solid_frame()
        elif self.args.style == "gradient":
            self.render_gradient_frame()

    def set_sustain(self, value: int) -> None:
        new_state = value >= self.args.sustain_threshold
        if new_state == self.sustain_on:
            return

        self.sustain_on = new_state
        if not self.sustain_on:
            for note in list(self.sustained_notes):
                if note not in self.active_notes:
                    del self.sustained_notes[note]

        if self.args.style == "solid":
            self.render_solid_frame()
        elif self.args.style == "gradient":
            self.render_gradient_frame()

    def inject_trail(self, led: int, color: Color) -> None:
        radius = self.args.width
        for dx in range(-radius, radius + 1):
            i = led + dx
            if 0 <= i < self.led_count:
                factor = 1.0 if dx == 0 else max(0.15, 1.0 - abs(dx) / (radius + 1))
                c = scale_color(color, factor)
                self.trail[i] = blend_add(self.trail[i], c)

    def update(self) -> None:
        if self.args.style == "trail":
            combined = {}
            combined.update(self.sustained_notes)
            combined.update(self.active_notes)
            for _, (led, color, _) in combined.items():
                self.inject_trail(led, color)
            self.render_trail_frame()

    def render_solid_frame(self) -> None:
        frame = [(0, 0, 0)] * self.led_count
        combined = {}
        combined.update(self.sustained_notes)
        combined.update(self.active_notes)
        for _, (led, color, _) in combined.items():
            radius = self.args.width
            for dx in range(-radius, radius + 1):
                i = led + dx
                if 0 <= i < self.led_count:
                    factor = 1.0 if dx == 0 else max(0.20, 1.0 - abs(dx) / (radius + 1))
                    frame[i] = blend_add(frame[i], scale_color(color, factor))
        for i in range(self.led_count):
            self.pixels[i] = frame[i]
        self.pixels.show()

    def render_gradient_frame(self) -> None:
        frame = [(0, 0, 0)] * self.led_count
        combined = {}
        combined.update(self.sustained_notes)
        combined.update(self.active_notes)
        for _, (led, color, _) in combined.items():
            radius = max(1, self.args.width)
            for dx in range(-radius, radius + 1):
                i = led + dx
                if 0 <= i < self.led_count:
                    dist = abs(dx)
                    norm = dist / radius if radius > 0 else 0.0
                    factor = max(0.06, (1.0 - norm) ** 2.2)
                    frame[i] = blend_add(frame[i], scale_color(color, factor))
            if 0 <= led < self.led_count:
                frame[led] = blend_add(frame[led], scale_color(color, 0.35))
        for i in range(self.led_count):
            self.pixels[i] = frame[i]
        self.pixels.show()

    def render_trail_frame(self) -> None:
        decay = self.args.trail_decay
        for i in range(self.led_count):
            r, g, b = self.trail[i]
            self.trail[i] = (int(r * decay), int(g * decay), int(b * decay))
            self.pixels[i] = self.trail[i]
        self.pixels.show()


def render_learn_frame(renderer, current_step, next_step=None, hint: bool = False) -> None:
    frame = [(0, 0, 0)] * renderer.led_count

    def learn_hand_color(hand_label: str | None):
        if hand_label == "left":
            return (0, 120, 255)   # blue
        if hand_label == "right":
            return (255, 180, 0)    # orange

        if renderer.args.hands == "split":
            return (255, 255, 255)
        if renderer.args.hands == "auto":
            return (255, 255, 255)
        return (255, 255, 255)

    # current step
    if current_step:
        for note in current_step.notes:
            led = renderer._note_to_led(note)
            if led is None:
                continue

            base_color = learn_hand_color(current_step.hands.get(note))
            frame[led] = blend_add(frame[led], scale_color(base_color, 0.65))

    # next step hint
    if hint and next_step:
        for note in next_step.notes:
            led = renderer._note_to_led(note)
            if led is None:
                continue

            base_color = learn_hand_color(next_step.hands.get(note))
            frame[led] = blend_add(frame[led], scale_color(base_color, 0.05))

    for i in range(renderer.led_count):
        renderer.pixels[i] = frame[i]
    renderer.pixels.show()


def flash_wrong_note(renderer: Renderer, note: int, color: Color = (255, 0, 0), flash_ms: int = 120) -> None:
    led = renderer._note_to_led(note)
    if led is None:
        return
    old_style = renderer.args.style
    frame = [(0, 0, 0)] * renderer.led_count
    radius = max(0, renderer.args.width)
    for dx in range(-radius, radius + 1):
        i = led + dx
        if 0 <= i < renderer.led_count:
            factor = 1.0 if dx == 0 else max(0.20, 1.0 - abs(dx) / (radius + 1))
            frame[i] = blend_add(frame[i], scale_color(color, factor))
    for i in range(renderer.led_count):
        renderer.pixels[i] = frame[i]
    renderer.pixels.show()
    time.sleep(flash_ms / 1000.0)

    if old_style == "solid":
        renderer.render_solid_frame()
    elif old_style == "gradient":
        renderer.render_gradient_frame()
    else:
        renderer.render_trail_frame()
