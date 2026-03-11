from __future__ import annotations


def apply_preset(args) -> None:
    """Mutate argparse Namespace in-place."""
    if args.preset == "practice":
        args.style = "solid"
        args.hands = "split"
        args.width = 1
        args.velocity_mode = "brightness"
    elif args.preset == "performance":
        args.style = "gradient"
        args.hands = "split"
        args.width = 4
        args.velocity_mode = "brightness"
