from dataclasses import dataclass

@dataclass(frozen=True)
class JointConfig:
    name: str
    channel: int
    min_angle: int
    max_angle: int
    home_angle: int

PCA9685_CHANNELS = 16
SERVO_MIN_PULSE = 500
SERVO_MAX_PULSE = 2500

DEFAULT_STEP = 3
DEFAULT_STEP_DELAY = 0.03
DEFAULT_HOLD = 0.15

JOINTS = {
    "base": JointConfig(
        name="base",
        channel=0,
        min_angle=20,
        max_angle=160,
        home_angle=90,
    ),
    "arm": JointConfig(
        name="arm",
        channel=1,
        min_angle=30,
        max_angle=150,
        home_angle=90,
    ),
}

HELP_TEXT = """
Available commands:
  home
  raise arm
  lower arm
  turn left
  turn right
  wave
  pick pose
  demo
  base <angle>
  arm <angle>
  state
  quit
""".strip()
