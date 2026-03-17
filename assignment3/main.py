from llm_decoder import decode_language_command
from robot_controller import RobotController
from robot_config import HELP_TEXT

def main() -> None:
    robot = RobotController()
    print("Language-Guided Multi-Joint Robotic System")
    print(HELP_TEXT)

    while True:
        try:
            command = input("\nEnter command: ").strip()
            if not command:
                continue
            if command.lower() in {"quit", "exit"}:
                print("Exiting.")
                break
            if command.lower() in {"help", "h", "?"}:
                print(HELP_TEXT)
                continue
            if command.lower() == "state":
                robot.print_state()
                continue

            primitives = decode_language_command(command)
            print(f"Decoded primitives: {primitives}")
            robot.execute_primitives(primitives)
            robot.print_state()

        except KeyboardInterrupt:
            print("\nInterrupted by user.")
            break
        except Exception as exc:
            print(f"Error: {exc}")

if __name__ == "__main__":
    main()
