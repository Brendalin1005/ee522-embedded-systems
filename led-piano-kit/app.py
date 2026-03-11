from __future__ import annotations

import argparse
import time

from led_piano.config import DEFAULT_BRIGHTNESS, DEFAULT_LED_COUNT, FRAME_DT, LOWEST_NOTE, LED_PIN_NAME
from led_piano.led.renderer import Renderer, flash_wrong_note, render_learn_frame
from led_piano.midi.input import live_midi_loop, print_ports, resolve_input_name
from led_piano.midi.learn import LearnEngine, build_steps_from_midi
from led_piano.midi.play import play_midi_file
from led_piano.presets import apply_preset

import signal
import sys



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LED Piano Kit")
    parser.add_argument("--list", action="store_true", help="List MIDI input devices")
    parser.add_argument("--mode", default="live", choices=["live", "play", "learn"])
    parser.add_argument("--in", dest="input_name", default=None, help="MIDI input device name or substring")
    parser.add_argument("--midi", help="MIDI file for play/learn mode")

    parser.add_argument("--preset", choices=["practice", "performance"], help="Use predefined visual settings")
    parser.add_argument("--style", default="solid", choices=["solid", "trail", "gradient"])
    parser.add_argument("--hands", default="off", choices=["off", "split", "auto"])
    parser.add_argument("--split-note", type=int, default=60)
    parser.add_argument("--velocity-mode", default="brightness", choices=["off", "brightness", "color", "both"])

    parser.add_argument("--trail-decay", type=float, default=0.92)
    parser.add_argument("--width", type=int, default=1)
    parser.add_argument("--led-count", type=int, default=DEFAULT_LED_COUNT)
    parser.add_argument("--brightness", type=float, default=DEFAULT_BRIGHTNESS)
    parser.add_argument("--pin", default=LED_PIN_NAME, choices=["D12", "D18", "D21"])

    parser.add_argument("--base-note", type=int, default=LOWEST_NOTE)
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--sustain-threshold", type=int, default=64)

    parser.add_argument("--hint", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--chord-press-window-ms", type=int, default=200)
    parser.add_argument("--min-hold-ms", type=int, default=80)
    parser.add_argument("--loop-start-step", type=int, default=None)
    parser.add_argument("--loop-end-step", type=int, default=None)

    parser.add_argument("--loop-start-sec", type=float, default=None)
    parser.add_argument("--loop-end-sec", type=float, default=None)

    parser.add_argument("--clear-only", action="store_true")

    parser.add_argument(
        "--learn-hand-source",
        choices=["track", "channel", "split"],
        default="track",
        help="How to infer left/right hand in learn mode",
    )
    parser.add_argument(
        "--play-hand-source",
        choices=["channel", "track", "split"],
        default="channel",
        help="How to infer left/right hand in play mode when using --hands auto/track-aware playback",
    )
    return parser


def make_pixels(args):
    import board
    import neopixel

    pin_map = {
        "D18": board.D18,
        "D12": board.D12,
        "D21": board.D21,
    }

    return neopixel.NeoPixel(
        pin_map[args.pin],
        args.led_count,
        brightness=args.brightness,
        auto_write=False,
    )


def run_live_mode(args, renderer: Renderer) -> None:
    if args.input_name is None:
        print("Please specify MIDI device with --in")
        return
    resolved_name = resolve_input_name(args.input_name)
    if resolved_name is None:
        return

    print("Opening MIDI:", resolved_name)
    print("Mode:", args.mode)
    print("Preset:", args.preset)
    print("Style:", args.style)

    def on_message(msg):
        if msg.type == "note_on" and msg.velocity > 0:
            renderer.note_on(msg.note, msg.velocity, channel=getattr(msg, "channel", None))
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            renderer.note_off(msg.note)
        elif msg.type == "control_change" and msg.control == 64:
            renderer.set_sustain(msg.value)

    live_midi_loop(resolved_name, FRAME_DT, on_message, renderer.update)


def run_play_mode(args, renderer: Renderer) -> None:
    if not args.midi:
        print("Please provide --midi file")
        return

    play_midi_file(
        args.midi,
        renderer,
        loop_start_sec=args.loop_start_sec,
        loop_end_sec=args.loop_end_sec,
        hand_source=args.play_hand_source,
        split_note=args.split_note,
    )
    renderer.clear()


def run_learn_mode(args, renderer: Renderer) -> None:
    if not args.midi:
        print("Please provide --midi file for learn mode")
        return
    if args.input_name is None:
        print("Please specify MIDI device with --in for learn mode")
        return

    resolved_name = resolve_input_name(args.input_name)
    if resolved_name is None:
        return

    steps = build_steps_from_midi(
        args.midi,
        hand_source=args.learn_hand_source,
        split_note=args.split_note,
    )
    if not steps:
        print("No learn steps found in MIDI file")
        return

    engine = LearnEngine(
        steps,
        chord_press_window_ms=args.chord_press_window_ms,
        min_hold_ms=args.min_hold_ms,
        loop_start_step=args.loop_start_step,
        loop_end_step=args.loop_end_step,
    )

    print("Opening MIDI:", resolved_name)
    print("Mode: learn")
    print("Steps total:", len(steps))
    print("Loop range:", engine.loop_start, "to", engine.loop_end)
    print("Learn hand source:", args.learn_hand_source)

    import mido

    with mido.open_input(resolved_name) as port:
        while True:
            if engine.is_finished():
                print("Loop finished.")
                engine.reset_to_loop_start()

            current_step = engine.current()
            next_step = engine.next()
            render_learn_frame(renderer, current_step=current_step, next_step=next_step, hint=args.hint)

            now_sec = time.monotonic()
            for msg in port.iter_pending():
                if msg.type == "note_on" and msg.velocity > 0:
                    engine.press(msg.note, now_sec)
                    if args.strict and engine.wrong_note_pressed(msg.note):
                        flash_wrong_note(renderer, msg.note)
                elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                    engine.release(msg.note)
                elif msg.type == "control_change" and msg.control == 64:
                    engine.set_sustain(msg.value, args.sustain_threshold)

            advanced = engine.check_advance(time.monotonic())
            if advanced:
                print("Advanced to step", engine.index)

            time.sleep(FRAME_DT)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    apply_preset(args)

    if args.list:
        print_ports()
        return

    pixels = make_pixels(args)
    renderer = Renderer(pixels, args.led_count, args)
    renderer.clear()

    try:
        if args.mode == "play":
            run_play_mode(args, renderer)
        elif args.mode == "learn":
            run_learn_mode(args, renderer)
        else:
            run_live_mode(args, renderer)
    finally:
        try:
            renderer.clear()
        except Exception:
            pass
        try:
            if hasattr(pixels, "deinit"):
                pixels.deinit()
        except Exception:
            pass


if __name__ == "__main__":
    main()