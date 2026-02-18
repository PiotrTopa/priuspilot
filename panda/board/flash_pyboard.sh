#!/usr/bin/env bash
# Flash panda firmware to Pyboard v1.1 via DFU
# Pyboard must be in DFU mode (hold USR button, press RST, release USR)
# DFU device: 0483:df11 (STM internal bootloader)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Build the pyboard firmware
echo "=== Building panda_pyboard firmware ==="
cd "$SCRIPT_DIR"
scons -u -j$(nproc) panda_pyboard

BOOTSTUB="$SCRIPT_DIR/obj/bootstub.panda_pyboard.bin"
FIRMWARE="$SCRIPT_DIR/obj/panda_pyboard.bin.signed"

if [ ! -f "$BOOTSTUB" ]; then
  echo "ERROR: Bootstub not found at $BOOTSTUB"
  exit 1
fi

if [ ! -f "$FIRMWARE" ]; then
  echo "ERROR: Firmware not found at $FIRMWARE"
  exit 1
fi

echo "=== Flashing bootstub to 0x08000000 ==="
dfu-util -d 0483:df11 -a 0 -s 0x08000000:leave -D "$BOOTSTUB"

sleep 1

echo "=== Flashing main firmware to 0x08004000 ==="
dfu-util -d 0483:df11 -a 0 -s 0x08004000:leave -D "$FIRMWARE"

echo "=== Done! Pyboard should enumerate as panda ==="
