# PriusPilot — Project Vision & Roadmap

## The Vision

Build a fully custom driving assistant for a heavily modified Toyota Prius Gen 2
(NHW20, 2004-2009). This isn't a stock car with comma.ai hardware — it's a modded
vehicle where every piece of driver-assist technology is being added from scratch.

The system uses:
- **Pocophone F1** as the brain (Snapdragon 845 — fast enough for real-time NN inference)
- **Pyboard v1.1** as the CAN adapter (cheaper and more hackable than a comma panda)
- **flowpilot** as the software base (open-source, runs on Android, supports custom hardware)
- **External display** on the network for HUD visualization (the phone mounts differently)

## Iteration Plan

### Phase 1: Passive (CURRENT)
**Goal**: See what the car sees, get lane visualization and alerts on an external display.

- [x] Port panda firmware to Pyboard v1.1 (STM32F405)
- [x] Remove all agreement/training/gatekeeping screens
- [x] Enable network-accessible ZMQ publishers
- [x] Create WebSocket bridge for external display
- [x] Build APK and panda firmware
- [ ] Deploy to Pocophone, verify CAN communication
- [ ] Build external display client (web-based HUD)
- [ ] Drive with passive monitoring — validate lane detection, log CAN data

### Phase 2: Active Cruise
**Goal**: Longitudinal control — accelerator follow (not braking yet).

- [ ] Reverse-engineer Prius Gen 2 throttle CAN messages
- [ ] Implement throttle actuation in panda firmware (safety-limited)
- [ ] Add cruise control state machine in controlsd
- [ ] Implement lead vehicle following (radar-based if available, vision-only otherwise)
- [ ] Safety: max acceleration limit, driver override detection, fault modes

### Phase 3: Steering Assist
**Goal**: Lateral control — lane keeping assist.

- [ ] Design/install aftermarket EPS actuator (Prius Gen 2 has no electric steering)
- [ ] OR: Use a column-mounted steering motor
- [ ] Implement steering torque commands in panda firmware
- [ ] Tune lateral PID/MPC controller for the specific car
- [ ] Safety: torque limits, hands-off detection, instant driver override

### Phase 4: Full Longitudinal
**Goal**: Gas + brake control for full adaptive cruise.

- [ ] Implement brake actuation (likely requires additional hardware — brake booster or ABS module mod)
- [ ] Merge with Phase 2 cruise for full stop-and-go
- [ ] Tune following distance, comfort profiles
- [ ] Safety: redundant brake path, fault tolerance

## Design Principles

1. **Safety first**: Every actuator control has hard limits in firmware. Driver can always override.
2. **Passive before active**: Get monitoring/visualization working perfectly before any control.
3. **Minimal modifications**: Use the least invasive hardware changes possible.
4. **Open source**: All custom code stays open. No proprietary dependencies.
5. **Iterate fast**: MVP approach — get something working, then improve.

## Known Challenges

- **No factory ADAS**: Prius Gen 2 has no radar, no LKA, no ACC. Everything is aftermarket.
- **Steering**: The biggest challenge. Gen 2 doesn't have EPS — it's hydraulic. Need a motor.
- **CAN reverse engineering**: Need to map out all relevant CAN messages for this specific car.
- **Model accuracy**: flowpilot's neural net was trained on highway data, may need fine-tuning for this specific setup/camera angle.
- **Thermal management**: Pocophone running NN inference continuously may overheat. Monitor temps.

## Key Decisions Made

| Decision | Rationale |
|----------|-----------|
| Pyboard v1.1 over comma panda | Cheaper, available, hackable. Same STM32F4 family. |
| flowpilot over openpilot | Runs on Android phones, no need for comma hardware. |
| Network-accessible ZMQ | External display support, debugging from laptop. |
| Remove all gatekeeping | "It starts, it works." No cloud accounts, no telemetry. |
| WSL2 Ubuntu for builds | Native Linux tools, no CRLF issues, fast ext4 builds. |
| Phase 1 passive first | Validate the entire stack before any actuation. |
