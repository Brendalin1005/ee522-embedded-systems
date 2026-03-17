from typing import Any, Dict, List

Primitive = Dict[str, Any]

def normalize_command(text: str) -> str:
    return " ".join(text.strip().lower().split())

def parse_command(command: str) -> List[Primitive]:
    cmd = normalize_command(command)

    if cmd in {"home", "go home", "reset"}:
        return [
            {"type": "move", "joint": "base", "target": 90, "hold": 0.15},
            {"type": "move", "joint": "arm", "target": 90, "hold": 0.15},
        ]

    if cmd in {"raise arm", "lift arm", "up"}:
        return [{"type": "move", "joint": "arm", "target": 120, "hold": 0.15}]

    if cmd in {"lower arm", "down"}:
        return [{"type": "move", "joint": "arm", "target": 60, "hold": 0.15}]

    if cmd in {"turn left", "left"}:
        return [{"type": "move", "joint": "base", "target": 60, "hold": 0.15}]

    if cmd in {"turn right", "right"}:
        return [{"type": "move", "joint": "base", "target": 120, "hold": 0.15}]

    if cmd in {"pick pose", "ready", "grasp ready"}:
        return [
            {"type": "move", "joint": "base", "target": 90, "hold": 0.10},
            {"type": "move", "joint": "arm", "target": 70, "hold": 0.25},
        ]

    if cmd in {"wave", "wave hand"}:
        return [
            {"type": "move", "joint": "arm", "target": 110, "hold": 0.10},
            {"type": "move", "joint": "base", "target": 65, "hold": 0.12},
            {"type": "move", "joint": "base", "target": 115, "hold": 0.12},
            {"type": "move", "joint": "base", "target": 65, "hold": 0.12},
            {"type": "move", "joint": "base", "target": 115, "hold": 0.12},
            {"type": "move", "joint": "base", "target": 90, "hold": 0.12},
        ]

    if cmd in {"demo", "run demo"}:
        return [
            {"type": "move", "joint": "base", "target": 90, "hold": 0.10},
            {"type": "move", "joint": "arm", "target": 120, "hold": 0.10},
            {"type": "move", "joint": "base", "target": 60, "hold": 0.10},
            {"type": "move", "joint": "base", "target": 120, "hold": 0.10},
            {"type": "move", "joint": "arm", "target": 70, "hold": 0.20},
            {"type": "move", "joint": "base", "target": 90, "hold": 0.10},
            {"type": "move", "joint": "arm", "target": 90, "hold": 0.10},
        ]

    if cmd.startswith("base "):
        try:
            angle = int(cmd.split()[1])
            return [{"type": "move", "joint": "base", "target": angle, "hold": 0.10}]
        except Exception as exc:
            raise ValueError("Invalid base angle command. Example: base 100") from exc

    if cmd.startswith("arm "):
        try:
            angle = int(cmd.split()[1])
            return [{"type": "move", "joint": "arm", "target": angle, "hold": 0.10}]
        except Exception as exc:
            raise ValueError("Invalid arm angle command. Example: arm 120") from exc

    raise ValueError(f"Unknown command: {command}")
