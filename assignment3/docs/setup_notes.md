# Setup Notes

## Raspberry Pi -> PCA9685

| Pi pin | Signal | PCA9685 pin |
|---|---|---|
| Pin 1 | 3.3V | VCC |
| Pin 3 | SDA1 | SDA |
| Pin 5 | SCL1 | SCL |
| Pin 9 (or any GND) | GND | GND |
| Pin 2 or 4 | 5V | V+ (temporary benchtop power, use external 5V in final setup) |

## Servo wiring

- Brown/Black -> GND
- Red -> V+
- Orange/Yellow -> Signal pin of selected channel

## Recommended workflow

1. Enable I2C in `raspi-config`
2. Run `i2cdetect -y 1`
3. Run `python debug_tools/i2c_probe.py`
4. Start with one servo on channel 0
5. Run `python main.py`

## Fault handling notes

If SCL or SDA is accidentally shorted:
- shut down Pi
- fully remove power
- disconnect and rewire
- test again with minimal bus
