LED_PIN_NAME = "D18"
DEFAULT_LED_COUNT = 144
DEFAULT_BRIGHTNESS = 0.20
FRAME_DT = 0.01  # 100 Hz refresh

# 43 calibrated white-key anchors from C0 to C6.
WHITE_KEY_LEDS = [
    0, 4, 8, 10, 14, 18, 21,
    24, 28, 32, 34, 38, 42, 45,
    48, 52, 56, 58, 61, 65, 69,
    71, 75, 79, 81, 85, 89, 93,
    95, 99, 103, 105, 109, 113, 117,
    119, 123, 127, 129, 133, 136, 140, 143,
]

# Current calibrated note range: C0 -> C6 inclusive = 73 notes.
LOWEST_NOTE = 24
HIGHEST_NOTE = LOWEST_NOTE + 72
