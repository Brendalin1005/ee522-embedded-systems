import time
from dataclasses import dataclass
from typing import Dict, List

from adafruit_servokit import ServoKit

from robot_config import (
    JOINTS,
    PCA9685_CHANNELS,
    SERVO_MIN_PULSE,
    SERVO_MAX_PULSE,
    DEFAULT_STEP,
    DEFAULT_STEP_DELAY,
)

@dataclass
class JointState:
    angle: int

class RobotController:
    def __init__(self) -> None:
        self.kit = ServoKit(channels=PCA9685_CHANNELS)
        self.state: Dict[str, JointState] = {}

        for joint_name, cfg in JOINTS.items():
            self.kit.servo[cfg.channel].set_pulse_width_range(
                SERVO_MIN_PULSE, SERVO_MAX_PULSE
            )
            self.state[joint_name] = JointState(angle=cfg.home_angle)

        self.home()

    def clamp_angle(self, joint: str, angle: int) -> int:
        cfg = JOINTS[joint]
        return max(cfg.min_angle, min(cfg.max_angle, int(angle)))

    def set_joint_angle(self, joint: str, angle: int) -> None:
        cfg = JOINTS[joint]
        safe_angle = self.clamp_angle(joint, angle)
        self.kit.servo[cfg.channel].angle = safe_angle
        self.state[joint].angle = safe_angle

    def get_joint_angle(self, joint: str) -> int:
        return self.state[joint].angle

    def move_joint_smooth(
        self,
        joint: str,
        target: int,
        step: int = DEFAULT_STEP,
        step_delay: float = DEFAULT_STEP_DELAY,
        hold: float = 0.0,
    ) -> None:
        target = self.clamp_angle(joint, target)
        current = self.get_joint_angle(joint)

        if current == target:
            if hold > 0:
                time.sleep(hold)
            return

        direction = 1 if target > current else -1
        step = max(1, abs(step)) * direction

        angle = current
        while (direction > 0 and angle < target) or (direction < 0 and angle > target):
            angle += step
            if direction > 0 and angle > target:
                angle = target
            elif direction < 0 and angle < target:
                angle = target

            self.set_joint_angle(joint, angle)
            time.sleep(step_delay)

        if hold > 0:
            time.sleep(hold)

    def execute_primitives(self, primitives: List[dict]) -> None:
        for item in primitives:
            ptype = item.get("type")
            if ptype == "move":
                self.move_joint_smooth(
                    joint=item["joint"],
                    target=item["target"],
                    step=item.get("step", DEFAULT_STEP),
                    step_delay=item.get("step_delay", DEFAULT_STEP_DELAY),
                    hold=item.get("hold", 0.0),
                )
            elif ptype == "pause":
                time.sleep(float(item.get("duration", 0.2)))
            else:
                raise ValueError(f"Unsupported primitive type: {ptype}")

    def home(self) -> None:
        for joint_name, cfg in JOINTS.items():
            self.set_joint_angle(joint_name, cfg.home_angle)
            time.sleep(0.10)

    def print_state(self) -> None:
        print("Current joint state:")
        for joint_name in JOINTS:
            print(f"  {joint_name}: {self.get_joint_angle(joint_name)}")
