from llm_decoder import decode_language_command
from robot_controller import RobotController

DEMO_COMMANDS = [
    "home",
    "raise arm",
    "turn left",
    "turn right",
    "wave",
    "pick pose",
    "home",
]

def main() -> None:
    robot = RobotController()
    for cmd in DEMO_COMMANDS:
        print(f"\nRunning command: {cmd}")
        primitives = decode_language_command(cmd)
        print(f"Decoded primitives: {primitives}")
        robot.execute_primitives(primitives)
    print("Demo finished.")

if __name__ == "__main__":
    main()
