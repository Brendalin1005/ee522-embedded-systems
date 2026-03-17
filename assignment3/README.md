# Assignment 3 Code Package

This package contains a clean, modular reference implementation for the **Language-Guided Multi-Joint Robotic System on Raspberry Pi with PCA9685**.

## Contents

- `main.py` — interactive CLI entry point
- `robot_config.py` — joint/channel/safety configuration
- `robot_commands.py` — rule-based command decoder
- `llm_decoder.py` — optional LLM-style decoder stub with safe fallback
- `robot_controller.py` — low-level servo control via PCA9685
- `demo_sequence.py` — scripted demo runner
- `debug_tools/i2c_probe.py` — low-level PCA9685 I2C read/write check
- `debug_tools/scan_i2c.sh` — helper script for `i2cdetect`
- `docs/setup_notes.md` — setup and wiring notes
- `requirements.txt` — Python dependencies

## Quick start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Important notes

1. Enable I2C first:

```bash
sudo raspi-config
# Interface Options -> I2C -> Enable
```

2. Check detection:

```bash
i2cdetect -y 1
```

3. Recommended power architecture:
- Pi 3.3V -> PCA9685 VCC
- Pi GND -> PCA9685 GND
- Pi SDA/SCL -> PCA9685 SDA/SCL
- External 5V (preferred) -> PCA9685 V+
- Common ground between Pi and external supply

## Safety

- Always clamp servo targets to safe angle limits.
- Start with **one servo** before moving to multiple joints.
- Hobby servos can draw surge current; avoid stressing the Pi 5V rail in final demos.
