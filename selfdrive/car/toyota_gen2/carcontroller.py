# PriusPilot — Prius Gen 2 (NHW20) car controller
# Phase 1: NO CONTROLS — all actuator commands are no-ops
from opendbc.can.packer import CANPacker
from selfdrive.car.toyota_gen2.values import DBC


class CarController():
  def __init__(self, dbc_name, CP, VM):
    self.packer = CANPacker(dbc_name)
    self.steer_rate_limited = False

  def update(self, c, CS, frame, actuators, pcm_cancel_cmd, hud_alert,
             left_line, right_line, lead, left_lane_depart, right_lane_depart):
    # Phase 1: Do NOT send any CAN messages to the car.
    # The panda safety mode is set to NO_OUTPUT, so even if we tried,
    # messages would be blocked. This is a safety belt.
    can_sends = []
    return can_sends
