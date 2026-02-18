# PriusPilot — Prius Gen 2 (NHW20) car interface
# Phase 1: read-only, no actuator control
from cereal import car
from common.conversions import Conversions as CV
from selfdrive.car import STD_CARGO_KG, scale_rot_inertia, scale_tire_stiffness, gen_empty_fingerprint, get_safety_config
from selfdrive.car.interfaces import CarInterfaceBase
from selfdrive.car.toyota_gen2.values import CAR

EventName = car.CarEvent.EventName


class CarInterface(CarInterfaceBase):
  @staticmethod
  def get_params(candidate, fingerprint=gen_empty_fingerprint(), car_fw=[]):
    ret = CarInterfaceBase.get_std_params(candidate, fingerprint)

    ret.carName = "toyota_gen2"

    # Phase 1: NO_OUTPUT safety — blocks all CAN transmissions
    ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.noOutput)]

    # ---- Prius Gen 2 (NHW20) vehicle parameters ----
    ret.wheelbase = 2.70          # meters (same as Gen 3)
    ret.steerRatio = 17.1         # steering ratio (Gen 2 is slightly higher than Gen 3)
    ret.steerActuatorDelay = 0.3  # seconds
    ret.steerLimitTimer = 1.0

    tire_stiffness_factor = 0.6
    ret.mass = 1380. + STD_CARGO_KG  # curb weight ~1380 kg (NHW20)

    ret.centerToFront = ret.wheelbase * 0.44

    ret.rotationalInertia = scale_rot_inertia(ret.mass, ret.wheelbase)
    ret.tireStiffnessFront, ret.tireStiffnessRear = scale_tire_stiffness(
      ret.mass, ret.wheelbase, ret.centerToFront,
      tire_stiffness_factor=tire_stiffness_factor
    )

    # ---- Feature flags ----
    ret.enableBsm = False           # no blind spot monitor
    ret.enableDsu = False           # no DSU on Gen 2
    ret.enableGasInterceptor = False
    ret.openpilotLongitudinalControl = False

    # Gen 2 is a hybrid — stop and go capable
    ret.minEnableSpeed = -1.0       # no minimum speed for engagement
    ret.pcmCruise = True            # cruise state comes from the car's PCM
    ret.stoppingControl = False     # Phase 1: no stopping control

    # ---- Longitudinal tuning (unused in Phase 1) ----
    ret.longitudinalTuning.kpBP = [0.]
    ret.longitudinalTuning.kpV = [0.]
    ret.longitudinalTuning.kiBP = [0.]
    ret.longitudinalTuning.kiV = [0.]
    ret.longitudinalTuning.kf = 0.

    return ret

  # returns a car.CarState
  def update(self, c, can_strings):
    # parse CAN
    self.cp.update_strings(can_strings)
    # cp_cam is None for Gen 2 — create a dummy if needed
    if self.cp_cam is not None:
      self.cp_cam.update_strings(can_strings)

    ret = self.CS.update(self.cp, self.cp_cam)
    ret.canValid = self.cp.can_valid
    ret.steeringRateLimited = False

    # events
    events = self.create_common_events(ret)

    # Phase 1: always report startupNoControl (we can see but not steer)
    # This event fires once on startup to inform the user
    if self.frame == 0:
      events.add(EventName.startupNoControl)

    ret.events = events.to_msg()
    self.CS.out = ret.as_reader()
    return self.CS.out

  def apply(self, c):
    # Phase 1: no-op — return empty CAN messages
    hud_control = c.hudControl
    ret = self.CC.update(c, self.CS, self.frame,
                         c.actuators, False,
                         0, False, False, False, False, False)
    self.frame += 1
    return ret
