from __future__ import annotations

from flask import Flask, render_template, request, jsonify
import os
import subprocess
import threading
import time
from pathlib import Path

import signal

import sys

BASE_DIR = Path(__file__).resolve().parent
SONGS_DIR = BASE_DIR / "songs"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

current_process = None
current_log_lines: list[str] = []
current_cmd: list[str] = []
process_lock = threading.Lock()

play_controller = None
play_renderer = None
play_pixels = None
play_args = None


def append_log(line: str) -> None:
    global current_log_lines
    if not line:
        return
    current_log_lines.append(line.rstrip())
    if len(current_log_lines) > 300:
        current_log_lines = current_log_lines[-300:]


def stop_current_process() -> None:
    global current_process
    if current_process is None:
        return

    try:
        if current_process.poll() is None:
            try:
                # send Ctrl+C style signal first
                if os.name != "nt":
                    os.killpg(os.getpgid(current_process.pid), signal.SIGINT)
                else:
                    current_process.terminate()
            except Exception:
                current_process.terminate()

            try:
                current_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                current_process.kill()
                current_process.wait(timeout=1)
    except Exception as e:
        append_log(f"[stop error] {e}")

    current_process = None
    time.sleep(0.2)


def stream_output(proc: subprocess.Popen) -> None:
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            append_log(line)
    except Exception as e:
        append_log(f"[stream error] {e}")


def build_cli_command(payload: dict) -> list[str]:
    mode = payload.get("mode", "play")
    song = payload.get("song", "").strip()
    midi_in = payload.get("input_name", "").strip()
    preset = payload.get("preset", "").strip()
    style = payload.get("style", "").strip()
    hands = payload.get("hands", "").strip()
    velocity_mode = payload.get("velocity_mode", "").strip()

    brightness = payload.get("brightness", "")
    width = payload.get("width", "")
    split_note = payload.get("split_note", "")

    hint = bool(payload.get("hint", False))
    strict = bool(payload.get("strict", False))
    reverse = bool(payload.get("reverse", False))

    cmd = [sys.executable, "app.py", "--mode", mode]

    if song:
        cmd += ["--midi", str(SONGS_DIR / song)]

    if midi_in:
        cmd += ["--in", midi_in]

    if preset:
        cmd += ["--preset", preset]

    if style:
        cmd += ["--style", style]

    if hands:
        cmd += ["--hands", hands]

    if velocity_mode:
        cmd += ["--velocity-mode", velocity_mode]

    if brightness not in ("", None):
        cmd += ["--brightness", str(brightness)]

    if width not in ("", None):
        cmd += ["--width", str(width)]

    if split_note not in ("", None):
        cmd += ["--split-note", str(split_note)]

    if hint:
        cmd.append("--hint")

    if strict:
        cmd.append("--strict")

    if reverse:
        cmd.append("--reverse")

    return cmd


def stop_play_controller() -> None:
    global play_controller, play_renderer, play_pixels, play_args

    if play_controller is not None:
        try:
            play_controller.stop()
        except Exception as e:
            append_log(f"[play stop error] {e}")

    # force clear LEDs owned by play renderer
    if play_renderer is not None:
        try:
            play_renderer.clear()
        except Exception as e:
            append_log(f"[play renderer clear error] {e}")

    # explicitly release neopixel object
    if play_pixels is not None:
        try:
            if hasattr(play_pixels, "fill"):
                play_pixels.fill((0, 0, 0))
            if hasattr(play_pixels, "show"):
                play_pixels.show()
        except Exception as e:
            append_log(f"[play pixels clear error] {e}")

        try:
            if hasattr(play_pixels, "deinit"):
                play_pixels.deinit()
        except Exception as e:
            append_log(f"[play pixels deinit error] {e}")

    play_controller = None
    play_renderer = None
    play_pixels = None
    play_args = None

    # give hardware/backend a moment to settle
    time.sleep(0.2)


def make_playback_objects(payload: dict):
    from app import build_parser, make_pixels
    from led_piano.led.renderer import Renderer
    from led_piano.midi.play import MidiPlaybackController
    from led_piano.presets import apply_preset

    parser = build_parser()
    args = parser.parse_args([])

    args.mode = "play"
    args.midi = str(SONGS_DIR / payload["song"])
    args.input_name = payload.get("input_name") or None
    args.preset = payload.get("preset") or None
    args.style = payload.get("style") or args.style
    args.hands = payload.get("hands") or args.hands
    args.velocity_mode = payload.get("velocity_mode") or args.velocity_mode
    args.brightness = float(payload.get("brightness") or args.brightness)
    args.width = int(payload.get("width") or args.width)
    args.split_note = int(payload.get("split_note") or args.split_note)
    args.hint = bool(payload.get("hint", False))
    args.strict = bool(payload.get("strict", False))
    args.reverse = bool(payload.get("reverse", False))

    apply_preset(args)

    pixels = make_pixels(args)
    renderer = Renderer(pixels, args.led_count, args)
    renderer.clear()

    controller = MidiPlaybackController(
        renderer,
        hand_source=args.play_hand_source,
        split_note=args.split_note,
    )
    controller.load(args.midi)

    return args, pixels, renderer, controller

def clear_leds() -> None:
    try:
        proc = subprocess.run(
            [sys.executable, "app.py", "--clear-only"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            append_log(f"[clear_leds rc={proc.returncode}]")
            if proc.stdout:
                append_log(proc.stdout)
            if proc.stderr:
                append_log(proc.stderr)
    except Exception as e:
        append_log(f"[clear_leds error] {e}")


def fmt_mmss(seconds: float) -> str:
    seconds = max(0, int(seconds))
    mm = seconds // 60
    ss = seconds % 60
    return f"{mm:02d}:{ss:02d}"


@app.route("/")
def index():
    songs = []
    if SONGS_DIR.exists():
        songs = sorted(
            [p.name for p in SONGS_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".mid", ".midi"}]
        )
    return render_template("index.html", songs=songs)


@app.route("/api/status")
def api_status():
    running = current_process is not None and current_process.poll() is None

    play_status = None
    if play_controller is not None:
        try:
            play_status = play_controller.status()
            play_status["current_time_text"] = fmt_mmss(play_status["current_time_sec"])
            play_status["total_time_text"] = fmt_mmss(play_status["total_time_sec"])
        except Exception as e:
            play_status = {"error": str(e)}

    return jsonify(
        {
            "running_subprocess": running,
            "cmd": " ".join(current_cmd) if current_cmd else "",
            "logs": current_log_lines[-80:],
            "play_status": play_status,
        }
    )


@app.route("/api/start", methods=["POST"])
def api_start():
    global current_process, current_cmd, current_log_lines
    global play_controller, play_renderer, play_pixels, play_args

    payload = request.get_json(silent=True) or {}
    mode = payload.get("mode", "play")

    try:
        with process_lock:
            # play mode: don't recreate controller if same song already loaded
            if mode == "play":
                song = (payload.get("song") or "").strip()
                if not song:
                    return jsonify({"ok": False, "error": "play mode 需要選一首 MIDI 檔"}), 400

                song_path = str(SONGS_DIR / song)

                # already loaded same song
                if play_controller is not None and play_args is not None and getattr(play_args, "midi", None) == song_path:
                    st = play_controller.status()

                    if st["paused"]:
                        play_controller.resume()
                        append_log("[resume existing play controller]")
                        return jsonify({"ok": True, "mode": "play-controller-resume"})

                    if st["running"]:
                        return jsonify({"ok": True, "mode": "play-controller-already-running"})

                    if st["loaded"] and not st["finished"]:
                        play_controller.play()
                        append_log("[continue existing play controller]")
                        return jsonify({"ok": True, "mode": "play-controller-continue"})

                # otherwise create brand new controller
                stop_current_process()
                stop_play_controller()
                time.sleep(0.2)
                current_log_lines = []
                current_cmd = []

                play_args, play_pixels, play_renderer, play_controller = make_playback_objects(payload)
                play_controller.play()

                current_cmd = [
                    "internal-play-controller",
                    f"song={song}",
                    f"speed={play_controller.status()['speed']}",
                ]
                append_log("[play controller started]")
                append_log(song)
                return jsonify({"ok": True, "mode": "play-controller"})

            # non-play mode keeps old subprocess behavior
            stop_current_process()
            stop_play_controller()
            time.sleep(0.2)
            current_log_lines = []
            current_cmd = []

            cmd = build_cli_command(payload)
            current_cmd = cmd[:]
            append_log("[starting subprocess]")
            append_log(" ".join(cmd))

            current_process = subprocess.Popen(
                cmd,
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid if os.name != "nt" else None,
            )
            t = threading.Thread(target=stream_output, args=(current_process,), daemon=True)
            t.start()

        return jsonify({"ok": True, "mode": "subprocess"})
    except Exception as e:
        append_log(f"[start error] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/stop", methods=["POST"])
def api_stop():
    try:
        with process_lock:
            stop_current_process()
            stop_play_controller()
            clear_leds()
            append_log("[stopped]")
        return jsonify({"ok": True})
    except Exception as e:
        append_log(f"[stop error] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/pause", methods=["POST"])
def api_pause():
    if play_controller is None:
        return jsonify({"ok": False, "error": "目前沒有 play controller"}), 400
    try:
        play_controller.pause()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/resume", methods=["POST"])
def api_resume():
    if play_controller is None:
        return jsonify({"ok": False, "error": "目前沒有 play controller"}), 400
    try:
        play_controller.resume()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/seek", methods=["POST"])
def api_seek():
    if play_controller is None:
        return jsonify({"ok": False, "error": "目前沒有 play controller"}), 400
    try:
        payload = request.get_json(silent=True) or {}
        target_sec = float(payload.get("target_sec", 0))
        play_controller.seek(target_sec)
        return jsonify({"ok": True, "target_sec": target_sec})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    
@app.route("/api/skip", methods=["POST"])
def api_skip():
    if play_controller is None:
        return jsonify({"ok": False, "error": "目前沒有 play controller"}), 400
    try:
        payload = request.get_json(silent=True) or {}
        delta_sec = float(payload.get("delta_sec", 0))
        play_controller.skip_by(delta_sec)
        return jsonify({"ok": True, "delta_sec": delta_sec})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    
@app.route("/api/restart", methods=["POST"])
def api_restart():
    if play_controller is None:
        return jsonify({"ok": False, "error": "目前沒有 play controller"}), 400
    try:
        play_controller.restart()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/set_speed", methods=["POST"])
def api_set_speed():
    if play_controller is None:
        return jsonify({"ok": False, "error": "目前沒有 play controller"}), 400
    try:
        payload = request.get_json(silent=True) or {}
        speed = float(payload.get("speed", 1.0))
        play_controller.set_speed(speed)
        return jsonify({"ok": True, "speed": speed})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/list_midi_inputs", methods=["GET"])
def api_list_midi_inputs():
    try:
        proc = subprocess.run(
            [sys.executable, "app.py", "--list"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=20,
        )
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return jsonify({"ok": True, "output": output})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def api_upload():
    try:
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "沒有收到檔案"}), 400

        f = request.files["file"]
        if not f.filename:
            return jsonify({"ok": False, "error": "檔名是空的"}), 400

        ext = Path(f.filename).suffix.lower()
        if ext not in {".mid", ".midi"}:
            return jsonify({"ok": False, "error": "只支援 .mid / .midi"}), 400

        SONGS_DIR.mkdir(parents=True, exist_ok=True)
        save_path = SONGS_DIR / Path(f.filename).name
        f.save(str(save_path))

        return jsonify({"ok": True, "filename": save_path.name})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    SONGS_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=False)