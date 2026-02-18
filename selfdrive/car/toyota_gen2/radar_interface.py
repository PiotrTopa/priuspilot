# PriusPilot — Prius Gen 2 (NHW20) radar interface
# Phase 1: no radar hardware — stub implementation
import os
import time
from cereal import car
from selfdrive.car.interfaces import RadarInterfaceBase


class RadarInterface(RadarInterfaceBase):
  def __init__(self, CP):
    super().__init__(CP)
    # Prius Gen 2 has no factory radar
    self.no_radar_sleep = 'NO_RADAR_SLEEP' in os.environ

  def update(self, can_strings):
    ret = car.RadarData.new_message()
    if not self.no_radar_sleep:
      time.sleep(self.radar_ts)
    return ret
