#!/usr/bin/env python3
"""
Low-level PCA9685 probe for debugging.
Reads and writes MODE1 register directly over I2C.
"""
import sys
import time
import smbus2

ADDR = 0x40
MODE1 = 0x00

def main() -> int:
    bus = smbus2.SMBus(1)
    try:
        val = bus.read_byte_data(ADDR, MODE1)
        print(f"Read MODE1 success: 0x{val:02X}")
        bus.write_byte_data(ADDR, MODE1, val)
        time.sleep(0.01)
        val2 = bus.read_byte_data(ADDR, MODE1)
        print(f"Read back MODE1: 0x{val2:02X}")
        return 0
    except Exception as exc:
        print(f"I2C test failed: {exc!r}")
        return 1
    finally:
        bus.close()

if __name__ == "__main__":
    raise SystemExit(main())
