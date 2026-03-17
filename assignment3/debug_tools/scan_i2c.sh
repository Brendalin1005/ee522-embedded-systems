#!/usr/bin/env bash
set -euo pipefail
echo "Scanning I2C bus 1..."
i2cdetect -y 1
