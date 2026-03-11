# led-piano-kit

Raspberry Pi + WS2812 + MIDI piano visualizer / practice tool.

This project supports three modes:
- `live`: real-time MIDI input -> LEDs
- `play`: play a `.mid` file -> LEDs
- `learn`: show the current step, optionally hint the next step, and only advance after the correct note/chord is pressed

It also supports:
- calibrated physical key-to-LED alignment using measured white-key anchors
- practice vs performance presets
- sustain pedal (CC64)
- split-hand coloring
- solid / trail / gradient rendering

## Project layout

```text
led-piano-kit/
├── app.py
├── requirements.txt
├── README.md
├── examples/
└── led_piano/
    ├── config.py
    ├── presets.py
    ├── led/
    │   ├── colors.py
    │   ├── mapping.py
    │   └── renderer.py
    └── midi/
        ├── input.py
        ├── play.py
        └── learn.py
```

## Install

Use a virtual environment on Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y python3-venv python3-full
python3 -m venv ~/venv-ledpiano
source ~/venv-ledpiano/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

Run with `sudo` for NeoPixel access.

## List MIDI devices

```bash
sudo ~/venv-ledpiano/bin/python app.py --list
```

## Live mode

Practice preset:

```bash
sudo ~/venv-ledpiano/bin/python app.py \
  --mode live \
  --in "GENERAL" \
  --preset practice
```

Performance preset:

```bash
sudo ~/venv-ledpiano/bin/python app.py \
  --mode live \
  --in "GENERAL" \
  --preset performance
```

## Play mode

```bash
sudo ~/venv-ledpiano/bin/python app.py \
  --mode play \
  --midi song.mid \
  --preset performance
```

## Learn mode

```bash
sudo ~/venv-ledpiano/bin/python app.py \
  --mode learn \
  --midi song.mid \
  --in "GENERAL" \
  --hands split \
  --split-note 60 \
  --hint
```

Strict learn mode with a looped section:

```bash
sudo ~/venv-ledpiano/bin/python app.py \
  --mode learn \
  --midi song.mid \
  --in "GENERAL" \
  --hands split \
  --split-note 60 \
  --hint \
  --strict \
  --loop-start-step 10 \
  --loop-end-step 25
```

## Useful flags

- `--pin D18|D12|D21`
- `--led-count 144`
- `--brightness 0.2`
- `--base-note 24`
- `--reverse`
- `--style solid|trail|gradient`
- `--hands off|split`
- `--split-note 60`
- `--velocity-mode off|brightness`
- `--trail-decay 0.92`
- `--width 1`
- `--sustain-threshold 64`
- `--chord-press-window-ms 200`
- `--min-hold-ms 80`

## Notes

The current mapping is calibrated for a 144 LED / 1 meter strip and a 73-note piano range from C0 to C6.
You can adjust `WHITE_KEY_LEDS` in `led_piano/config.py` if you recalibrate the physical alignment.
