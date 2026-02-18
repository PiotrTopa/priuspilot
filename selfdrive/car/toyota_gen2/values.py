# PriusPilot — Prius Gen 2 (NHW20, 2004-2009) car definitions
# Phase 1: read-only, no actuator control
from selfdrive.car import dbc_dict


class CAR:
  PRIUS_GEN2 = "TOYOTA PRIUS GEN2 2004"


# DBC file mapping
DBC = {
  CAR.PRIUS_GEN2: dbc_dict('prius_gen2_pt', None),  # no ADAS bus
}

# Gear values mapping (from CAN message 0x0120)
GEAR_MAP = {
  0: "P",   # Park
  1: "R",   # Reverse
  2: "N",   # Neutral
  3: "D",   # Drive
}

# CAN fingerprint — set of (CAN_address: data_length) pairs seen on bus 0
# when the car is in READY mode. Used for automatic car identification.
FINGERPRINTS = {
  CAR.PRIUS_GEN2: [{
    # Core powertrain messages (broadcast when car is in READY)
    0x0022: 8,   # Lateral acceleration
    0x0023: 8,   # Longitudinal acceleration
    0x0025: 8,   # Steering angle sensor
    0x0030: 8,   # Brake pedal position
    0x0038: 8,   # ICE RPM (coarse)
    0x0039: 8,   # ICE coolant temperature
    0x003B: 8,   # EM current / HV voltage
    0x0081: 8,   # Front wheel pulses
    0x0083: 8,   # Rear wheel pulses
    0x0120: 8,   # Drive mode (gear: P/R/N/D)
    0x0244: 8,   # Throttle pedal position
    0x03CA: 8,   # Vehicle speed
    0x03CB: 8,   # HV battery SOC
    0x0529: 8,   # Event messages
    0x05B6: 8,   # Doors/hatch status
    0x05CC: 8,   # Outside temperature
  }],
}
