from __future__ import annotations

import threading
import time
from typing import Any

import mido


def _ticks_to_seconds(abs_tick: int, tempo_events: list[tuple[int, int]], ticks_per_beat: int) -> float:
    if not tempo_events:
        tempo_events = [(0, 500000)]

    total_sec = 0.0
    prev_tick = 0
    prev_tempo = tempo_events[0][1]

    for tick, tempo in tempo_events[1:]:
        if abs_tick <= tick:
            break
        dticks = tick - prev_tick
        total_sec += (dticks / ticks_per_beat) * (prev_tempo / 1_000_000.0)
        prev_tick = tick
        prev_tempo = tempo

    dticks = abs_tick - prev_tick
    total_sec += (dticks / ticks_per_beat) * (prev_tempo / 1_000_000.0)
    return total_sec


def _collect_timed_events(mid: mido.MidiFile) -> list[dict[str, Any]]:
    tempo_events: list[tuple[int, int]] = [(0, 500000)]
    timed_events: list[dict[str, Any]] = []

    for track_idx, track in enumerate(mid.tracks):
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time

            if msg.type == "set_tempo":
                tempo_events.append((abs_tick, msg.tempo))

            if msg.type in ("note_on", "note_off", "control_change"):
                timed_events.append(
                    {
                        "tick": abs_tick,
                        "track_idx": track_idx,
                        "msg": msg,
                    }
                )

    tempo_events.sort(key=lambda x: x[0])
    deduped: list[tuple[int, int]] = []
    for tick, tempo in tempo_events:
        if deduped and deduped[-1][0] == tick:
            deduped[-1] = (tick, tempo)
        else:
            deduped.append((tick, tempo))

    for ev in timed_events:
        ev["sec"] = _ticks_to_seconds(ev["tick"], deduped, mid.ticks_per_beat)

    timed_events.sort(key=lambda x: (x["sec"], x["track_idx"]))
    return timed_events


def _hand_override_from_event(ev: dict, hand_source: str, split_note: int) -> str | None:
    msg = ev["msg"]

    if hand_source == "track":
        return "right" if ev["track_idx"] == 0 else "left"

    if hand_source == "split":
        if hasattr(msg, "note"):
            return "left" if msg.note < split_note else "right"

    return None


def _apply_event_to_renderer(ev: dict, renderer, hand_source: str, split_note: int) -> None:
    msg = ev["msg"]
    hand_override = _hand_override_from_event(ev, hand_source, split_note)

    if msg.type == "note_on" and msg.velocity > 0:
        if hand_override is None:
            renderer.note_on(msg.note, msg.velocity, channel=getattr(msg, "channel", None))
        else:
            if renderer.args.hands == "auto":
                synth_channel = 0 if hand_override == "left" else 1
                renderer.note_on(msg.note, msg.velocity, channel=synth_channel)
            else:
                renderer.note_on(msg.note, msg.velocity, channel=getattr(msg, "channel", None))

    elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
        renderer.note_off(msg.note)

    elif msg.type == "control_change" and msg.control == 64:
        renderer.set_sustain(msg.value)

    renderer.update()


class MidiPlaybackController:
    def __init__(
        self,
        renderer,
        hand_source: str = "channel",
        split_note: int = 60,
    ):
        self.renderer = renderer
        self.hand_source = hand_source
        self.split_note = split_note

        self.path: str | None = None
        self.events: list[dict] = []
        self.total_duration_sec: float = 0.0

        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_flag = False
        self._paused = False
        self._speed = 1.0

        self._position_sec = 0.0
        self._event_index = 0
        self._anchor_wall_time = time.monotonic()
        self._anchor_song_time = 0.0

        self._finished = False

    def load(
        self,
        path: str,
        loop_start_sec: float | None = None,
        loop_end_sec: float | None = None,
    ) -> None:
        mid = mido.MidiFile(path)
        events = _collect_timed_events(mid)

        filtered: list[dict] = []
        for ev in events:
            sec = ev["sec"]
            if loop_start_sec is not None and sec < loop_start_sec:
                continue
            if loop_end_sec is not None and sec > loop_end_sec:
                continue
            filtered.append(ev)

        with self._lock:
            self.stop()
            self.path = path
            self.events = filtered
            self.total_duration_sec = filtered[-1]["sec"] if filtered else 0.0
            self._position_sec = filtered[0]["sec"] if filtered else 0.0
            self._event_index = 0
            self._anchor_wall_time = time.monotonic()
            self._anchor_song_time = self._position_sec
            self._stop_flag = False
            self._paused = False
            self._finished = False
            self._clear_renderer_state()

    def _clear_renderer_state(self) -> None:
        self.renderer.active_notes.clear()
        self.renderer.sustained_notes.clear()
        self.renderer.sustain_on = False
        if hasattr(self.renderer, "trail"):
            self.renderer.trail = [(0, 0, 0)] * self.renderer.led_count
        self.renderer.clear()

    def _find_event_index_for_time(self, target_sec: float) -> int:
        for i, ev in enumerate(self.events):
            if ev["sec"] >= target_sec:
                return i
        return len(self.events)
    
    def _rebuild_state_at_time(self, target_sec: float) -> None:
        """
        Reconstruct renderer state at target_sec so seek/restart keeps held notes
        and sustain state consistent with Renderer's internal data structures.

        Renderer expects:
          active_notes[note] = (led, color, velocity)
          sustained_notes[note] = (led, color, velocity)
        """
        self.renderer.active_notes.clear()
        self.renderer.sustained_notes.clear()
        self.renderer.sustain_on = False
        if hasattr(self.renderer, "trail"):
            self.renderer.trail = [(0, 0, 0)] * self.renderer.led_count

        # temporary logical state:
        # active_notes[note] = (velocity, channel)
        active_notes: dict[int, tuple[int, int | None]] = {}
        # sustained_notes[note] = (velocity, channel)
        sustained_notes: dict[int, tuple[int, int | None]] = {}
        sustain_on = False

        for ev in self.events:
            if ev["sec"] > target_sec:
                break

            msg = ev["msg"]

            if msg.type == "control_change" and msg.control == 64:
                new_sustain = msg.value >= self.renderer.args.sustain_threshold

                # sustain released: clear notes that were only being held by pedal
                if sustain_on and not new_sustain:
                    sustained_notes.clear()

                sustain_on = new_sustain

            elif msg.type == "note_on" and msg.velocity > 0:
                ch = getattr(msg, "channel", None)
                hand_override = _hand_override_from_event(ev, self.hand_source, self.split_note)

                if hand_override is not None and self.renderer.args.hands == "auto":
                    ch = 0 if hand_override == "left" else 1

                active_notes[msg.note] = (msg.velocity, ch)
                sustained_notes.pop(msg.note, None)

            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                if msg.note in active_notes:
                    if sustain_on:
                        sustained_notes[msg.note] = active_notes[msg.note]
                    del active_notes[msg.note]
                else:
                    sustained_notes.pop(msg.note, None)

        self.renderer.sustain_on = sustain_on

        # rebuild active_notes in renderer's expected structure
        rebuilt_active = {}
        for note, (velocity, channel) in active_notes.items():
            led = self.renderer._note_to_led(note)
            if led is None:
                continue
            color = self.renderer._note_to_color(note, velocity, channel)
            rebuilt_active[note] = (led, color, velocity)

        # rebuild sustained_notes in renderer's expected structure
        rebuilt_sustained = {}
        for note, (velocity, channel) in sustained_notes.items():
            led = self.renderer._note_to_led(note)
            if led is None:
                continue
            color = self.renderer._note_to_color(note, velocity, channel)
            rebuilt_sustained[note] = (led, color, velocity)

        self.renderer.active_notes = rebuilt_active
        self.renderer.sustained_notes = rebuilt_sustained

        # redraw according to current style
        if self.renderer.args.style == "solid":
            self.renderer.render_solid_frame()
        elif self.renderer.args.style == "gradient":
            self.renderer.render_gradient_frame()
        else:
            self.renderer.update()

    def _run(self) -> None:
        tick_sleep = 0.005

        while True:
            with self._lock:
                if self._stop_flag:
                    break

                if self._paused:
                    self._anchor_wall_time = time.monotonic()
                    self._anchor_song_time = self._position_sec
                else:
                    now = time.monotonic()
                    self._position_sec = self._anchor_song_time + (now - self._anchor_wall_time) * self._speed

                    while self._event_index < len(self.events) and self.events[self._event_index]["sec"] <= self._position_sec:
                        ev = self.events[self._event_index]
                        _apply_event_to_renderer(ev, self.renderer, self.hand_source, self.split_note)
                        self._event_index += 1

                    if self._event_index >= len(self.events):
                        self._position_sec = self.total_duration_sec
                        self._finished = True
                        self._stop_flag = True
                        break

            time.sleep(tick_sleep)

        with self._lock:
            self._clear_renderer_state()

    def play(self) -> None:
        with self._lock:
            if not self.events:
                return

            if self._thread is not None and self._thread.is_alive():
                self._paused = False
                self._anchor_wall_time = time.monotonic()
                self._anchor_song_time = self._position_sec
                return

            self._stop_flag = False
            self._paused = False
            self._finished = False
            self._anchor_wall_time = time.monotonic()
            self._anchor_song_time = self._position_sec
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def pause(self) -> None:
        with self._lock:
            if self._paused:
                return
            self._position_sec = self.current_time_sec()
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            if not self._paused:
                return
            self._paused = False
            self._anchor_wall_time = time.monotonic()
            self._anchor_song_time = self._position_sec

    def stop(self) -> None:
        with self._lock:
            self._stop_flag = True
            self._paused = False

        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)

        with self._lock:
            self._thread = None
            self._event_index = 0
            self._position_sec = 0.0
            self._finished = False
            self._stop_flag = False
            self._clear_renderer_state()

    def seek(self, target_sec: float) -> None:
        with self._lock:
            if not self.events:
                return

            target_sec = max(0.0, min(target_sec, self.total_duration_sec))
            self._position_sec = target_sec
            self._event_index = self._find_event_index_for_time(target_sec)
            self._anchor_wall_time = time.monotonic()
            self._anchor_song_time = target_sec

            self._rebuild_state_at_time(target_sec)

    def skip_by(self, delta_sec: float) -> None:
        self.seek(self.current_time_sec() + delta_sec)

    def restart(self) -> None:
        self.seek(0.0)

    def set_speed(self, speed: float) -> None:
        with self._lock:
            speed = max(0.25, min(speed, 3.0))
            current = self.current_time_sec()
            self._speed = speed
            self._position_sec = current
            self._anchor_wall_time = time.monotonic()
            self._anchor_song_time = self._position_sec

    def current_time_sec(self) -> float:
        if self._paused or self._thread is None or not self._thread.is_alive():
            return self._position_sec

        now = time.monotonic()
        value = self._anchor_song_time + (now - self._anchor_wall_time) * self._speed
        return max(0.0, min(value, self.total_duration_sec))

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self._paused

    def is_paused(self) -> bool:
        return self._paused

    def is_loaded(self) -> bool:
        return bool(self.events)

    def status(self) -> dict[str, Any]:
        current = self.current_time_sec()
        total = self.total_duration_sec
        progress = (current / total) if total > 0 else 0.0

        return {
            "loaded": self.is_loaded(),
            "running": self.is_running(),
            "paused": self.is_paused(),
            "finished": self._finished,
            "path": self.path,
            "current_time_sec": round(current, 3),
            "total_time_sec": round(total, 3),
            "progress": progress,
            "speed": self._speed,
            "event_index": self._event_index,
            "events_total": len(self.events),
        }


def play_midi_file(
    path: str,
    renderer,
    loop_start_sec: float | None = None,
    loop_end_sec: float | None = None,
    hand_source: str = "channel",
    split_note: int = 60,
) -> None:
    controller = MidiPlaybackController(
        renderer,
        hand_source=hand_source,
        split_note=split_note,
    )
    controller.load(
        path,
        loop_start_sec=loop_start_sec,
        loop_end_sec=loop_end_sec,
    )
    controller.play()

    try:
        while True:
            st = controller.status()
            if st["finished"] or (not st["running"] and not st["paused"] and st["loaded"]):
                break
            time.sleep(0.02)
    finally:
        controller.stop()