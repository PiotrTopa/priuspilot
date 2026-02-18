# PriusPilot — Copilot Workspace Instructions

## What This Project Is

A custom driving computer for a **highly modded Toyota Prius Gen 2 (NHW20, 2004-2009)**,
based on [flowpilot](https://github.com/flowdriveai/flowpilot) open-source driving
assistant. The car has NO factory LKA or ACC — all driver-assist features are being
added aftermarket.

**Code name**: PriusPilot

## Hardware Stack

| Component | Role |
|-----------|------|
| **Pocophone F1** (Snapdragon 845) | Main compute — runs flowpilot Android app + proot Ubuntu backend |
| **Pyboard v1.1** (STM32F405RG) | CAN interface — replaces comma.ai panda, running ported panda firmware |
| **SN65HVD230** | CAN transceiver on Pyboard, always active (no standby pin) |
| **Prius Gen 2 CAN bus** | Vehicle communication (no OBD-II gateway, direct CAN) |
| External display device (TBD) | Network-connected HUD, receives data via WebSocket bridge |

## Software Architecture

- **Android APK** (Java, libGDX): UI, camera, neural net inference (TNN/SNPE/ONNX), sensors
- **Proot Ubuntu backend** (Python/C++): controlsd, plannerd, calibrationd, pandad, radard, thermald
- **Communication**: ZeroMQ over TCP, ports starting at 5100, bound on 0.0.0.0 (DISCOVERABLE_PUBLISHERS=1)
- **Panda firmware** (C, arm-none-eabi): STM32F4 firmware handling CAN rx/tx, USB serial to phone
- **WebSocket bridge** (tools/bridge_ws.py): Subscribes ZMQ topics, broadcasts JSON on ws://phone:8867

## Key Files Modified (Our Changes)

### Panda firmware port (panda/ submodule @ f120999e)
- `board/boards/pyboard.h` — NEW: Pyboard v1.1 board definition (CAN1 PB8/PB9 AF9, LEDs PA13-15/PB4)
- `board/boards/board_declarations.h` — Added HW_TYPE_PYBOARD = 10
- `board/stm32fx/clock.h` — PLLM=6 for 12MHz crystal (#ifdef PYBOARD)
- `board/stm32fx/board.h` — Include pyboard.h, detect_board_type() returns PYBOARD
- `board/main.c` — Force ignition_can=true, skip GPS/LIN/ESP, WFI instead of deepsleep
- `board/SConscript` — panda_pyboard build target with -DPYBOARD
- `board/flash_pyboard.sh` — NEW: DFU flash script
- `python/__init__.py` — HW_TYPE_PYBOARD=0x0a, added to F4_DEVICES

### Gatekeeping removal (flowpilot main repo)
- `selfdrive/ui/java/.../SetUpScreen.java` — Skip terms/registration/training screens
- `selfdrive/ui/java/.../OnRoadScreen.java` — Remove connectivity/time nag banners
- `selfdrive/thermald/thermald.py` — Force time_valid, up_to_date, terms, training = True
- `selfdrive/manager/flowinitd.py` — Default params: accepted terms, enabled toggle, discoverable publishers
- `selfdrive/manager/process_config.py` — Disabled uploader and statsd
- `selfdrive/sentry.py` — sentry_init() and capture_error() are no-ops

### Network visualization (cereal/ submodule + flowpilot)
- `cereal/messaging/java/messaging/Utils.java` — getZMQBindAddress() respects DISCOVERABLE_PUBLISHERS
- `cereal/messaging/java/messaging/ZMQPubHandler.java` — Uses getBindSocketPath() for 0.0.0.0 binding
- `launch_flowpilot.sh` — DISCOVERABLE_PUBLISHERS=1 by default
- `tools/bridge_ws.py` — NEW: WebSocket bridge for external display devices

### Build dependency fix
- `android/build.gradle` — Fixed termux-shared: com.github.termux.termux-app:termux-shared:v0.118.0

## Build System

All builds happen on **WSL2 Ubuntu** at `/home/piotr/projects/priuspilot/flowpilot`.

```bash
# Panda firmware
cd panda && scons board/obj/panda_pyboard.bin.signed && cd ..

# APK
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export ANDROID_HOME=/home/piotr/android-sdk
./gradlew android:assembleRelease -PandroidSlim

# Cap'n Proto Java defs (if .capnp schemas change)
capnpc --src-prefix=cereal cereal/log.capnp cereal/car.capnp cereal/legacy.capnp \
  -ojava:cereal/java/ai.flow.definitions
```

## Prius Gen 2 CAN Notes

- CAN bus speed: 500 kbit/s
- Key messages: steering angle (0x025), wheel speeds (0x0B4), brake (0x224), gas pedal, gear
- No factory ADAS — all actuator control must be added via aftermarket hardware
- Pyboard connects directly to vehicle CAN bus (no OBD-II port)

## Code Conventions

- All code, comments, function names, and documentation in **English only**
- Chat may be in Polish or other languages, but technical content stays English
- Linux-native project. No CRLF. WSL2 Ubuntu is the build environment.
- The old Windows clone at `D:\Projects\CyberPunk\priuspilot` is **deprecated**. Use the Linux clone.
