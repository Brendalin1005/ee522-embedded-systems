"""
Optional LLM-style decoder stub.

This file is intentionally lightweight so it can be included in the report package
without requiring network access or external APIs. The default behavior falls back
to the rule-based parser in `robot_commands.py`.
"""
from typing import List, Dict, Any
from robot_commands import parse_command

Primitive = Dict[str, Any]

def decode_language_command(text: str) -> List[Primitive]:
    """
    Safe local fallback:
    - normalize and map known user phrases
    - use the existing rule-based parser

    This keeps the project reproducible even without internet or API keys.
    """
    synonyms = {
        "move arm up": "raise arm",
        "move arm down": "lower arm",
        "go left": "turn left",
        "go right": "turn right",
        "return home": "home",
    }
    normalized = " ".join(text.strip().lower().split())
    normalized = synonyms.get(normalized, normalized)
    return parse_command(normalized)
