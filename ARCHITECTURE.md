# PriusPilot Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Pocophone F1                          │
│                                                         │
│  ┌─────────────────┐       ┌──────────────────────┐    │
│  │  Android APK     │       │  Proot Ubuntu         │    │
│  │  (ai.flow.android)│◄────►│  Backend              │    │
│  │                   │ ZMQ  │                        │    │
│  │  - libGDX UI/HUD │ TCP  │  - flowinitd (mgr)    │    │
│  │  - CameraX       │      │  - controlsd          │    │
│  │  - TNN/SNPE model│      │  - plannerd           │    │
│  │  - SensorManager │      │  - radard             │    │
│  │  - SetUpScreen    │      │  - calibrationd       │    │
│  │  - OnRoadScreen   │      │  - pandad             │    │
│  └─────────────────┘       │  - thermald           │    │
│                              │  - modelparsed        │    │
│                              │  - bridge_ws.py       │    │
│                              └──────────┬───────────┘    │
│                                          │ USB Serial    │
└──────────────────────────────────────────┼───────────────┘
                                           │
                                ┌──────────▼──────────┐
                                │   Pyboard v1.1      │
                                │   (panda firmware)  │
                                │                     │
                                │   STM32F405RG       │
                                │   CAN1: PB8/PB9     │
                                │   XTAL: 12MHz       │
                                │   SN65HVD230        │
                                └──────────┬──────────┘
                                           │ CAN bus
                                ┌──────────▼──────────┐
                                │  Toyota Prius Gen 2 │
                                │  NHW20 (2004-2009)  │
                                │  500 kbit/s CAN     │
                                └─────────────────────┘
```

## Communication Architecture

### ZeroMQ Messaging (cereal)

All inter-process communication uses ZeroMQ PUB/SUB over TCP.

| Port Range | Protocol | Bind Address |
|------------|----------|--------------|
| 5100+ | TCP | 0.0.0.0 (DISCOVERABLE_PUBLISHERS=1) |

Key topics and their publishers:
- `controlsState` — controlsd (lateral/longitudinal state)
- `carState` — pandad (parsed CAN data)
- `modelV2` — modelparsed (lane lines, path prediction)
- `radarState` — radard (lead vehicle tracking)
- `liveCalibration` — calibrationd (camera-to-road transform)
- `carParams` — pandad (vehicle identification)
- `deviceState` — thermald (temps, battery, network)
- `gpsLocation` — sensord (GPS if available)
- `liveParameters` — locationd (vehicle dynamics estimates)
- `lateralPlan` / `longitudinalPlan` — plannerd (path plans)

### External access

With `DISCOVERABLE_PUBLISHERS=1` (default), all ZMQ publishers bind on `0.0.0.0`
instead of `127.0.0.1`, making them accessible from other devices on the same network.

The WebSocket bridge (`tools/bridge_ws.py`) subscribes to 13 ZMQ topics and
rebroadcasts as JSON on `ws://<phone-ip>:8867` at ~20Hz. Supports per-client
topic filtering via `{"subscribe": ["topic1", "topic2"]}` messages.

### CAN Communication

The Pyboard runs panda firmware that provides:
- USB serial interface (CDC ACM) to the phone
- CAN1 at 500 kbit/s to the Prius CAN bus
- Heartbeat monitoring (LED blink)
- No GPS, no LIN, no OBD, no fan control, no harness detection

pandad on the phone talks to the Pyboard via `/dev/ttyACM0` using the panda
Python library protocol (bulk USB transfers for CAN frames).

## Android App Startup Sequence

1. `LoadingActivity` starts → requests permissions
2. Sends Intent to Termux `RUN_COMMAND_SERVICE` → executes `boot_flowpilot`
3. `boot_flowpilot` enters proot Ubuntu → runs `launch_flowpilot.sh`
4. `launch_flowpilot.sh` starts tmux → `scons && flowinit`
5. `flowinitd.py` starts all backend processes, rsyncs model to /sdcard
6. `LoadingActivity` waits for params → launches `AndroidLauncher` (libGDX)
7. `AndroidLauncher` initializes camera, sensors, model runner
8. `SetUpScreen` shown (our version auto-accepts, goes to calibration)
9. `OnRoadScreen` renders HUD (our version: no nag banners)

## Filesystem on Phone

| Path | Contents |
|------|----------|
| `/data/data/com.termux/files/home/` | Termux home |
| `.../proot-distro/.../ubuntu-jammy-fd/root/flowpilot/` | Backend code (Python/C++) |
| `/sdcard/flowpilot/selfdrive/assets/models/f2/` | ONNX/TNN model files |
| `/data/params/d/` | Runtime parameters (Params interface) |

## Panda Firmware Details

Built for STM32F405RG (Pyboard v1.1). Key differences from stock panda:

| Feature | Stock Panda | Pyboard Port |
|---------|-------------|--------------|
| MCU | STM32F413 | STM32F405RG |
| Crystal | 8 MHz | 12 MHz (PLLM=6) |
| CAN ports | CAN1+CAN2+CAN3 | CAN1 only (PB8/PB9 AF9) |
| Transceiver | TJA1042 w/ standby | SN65HVD230 (always active) |
| Harness | Has harness detection | No harness (car_harness_status forced NORMAL) |
| GPS/LIN/OBD | Yes | No |
| Deep sleep | Yes (STOP mode) | No (WFI only, no wake hardware) |
| Fan | Yes | No |
| Ignition | CAN-based detection | Forced always-on |
| LEDs | Has RGB | PA13(red), PA14(green), PA15(yellow), PB4(blue) |
| HW type ID | 0x00-0x07 | 0x0a (HW_TYPE_PYBOARD) |
