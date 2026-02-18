// ///////////////// //
// Pyboard v1.1      //
// STM32F405RG       //
// 12MHz crystal     //
// ///////////////// //

// Pyboard v1.1 pinout for CAN interface:
// CAN1 RX: PB8 (Y3 on Pyboard)
// CAN1 TX: PB9 (Y4 on Pyboard)
// LEDs: Red=PA13, Green=PA14, Yellow=PA15, Blue=PB4
// Note: PA13/PA14 are also SWDIO/SWCLK (directly driving LEDs)

void pyboard_enable_can_transceiver(uint8_t transceiver, bool enabled) {
  // External SN65HVD230 transceiver - always active, no enable pin needed
  UNUSED(transceiver);
  UNUSED(enabled);
}

void pyboard_enable_can_transceivers(bool enabled) {
  UNUSED(enabled);
}

void pyboard_set_led(uint8_t color, bool enabled) {
  // Pyboard LEDs are active high
  switch (color) {
    case LED_RED:
      set_gpio_output(GPIOA, 13, enabled);
      break;
    case LED_GREEN:
      set_gpio_output(GPIOA, 14, enabled);
      break;
    case LED_BLUE:
      set_gpio_output(GPIOA, 15, enabled);
      break;
    default:
      break;
  }
}

void pyboard_set_gps_mode(uint8_t mode) {
  // Pyboard has no GPS
  UNUSED(mode);
}

void pyboard_set_can_mode(uint8_t mode) {
  if (mode == CAN_MODE_NORMAL) {
    // CAN1 on PB8 (RX) and PB9 (TX) - AF9
    set_gpio_alternate(GPIOB, 8, GPIO_AF9_CAN1);
    set_gpio_alternate(GPIOB, 9, GPIO_AF9_CAN1);
  }
}

bool pyboard_check_ignition(void) {
  // No ignition sensing on Pyboard - always return true for standalone operation
  return true;
}

uint32_t pyboard_read_current(void) {
  // No current sensing on Pyboard
  return 0U;
}

void pyboard_init(void) {
  common_init_gpio();

  // Setup CAN1 pins: PB8 (RX/Y3), PB9 (TX/Y4)
  set_gpio_alternate(GPIOB, 8, GPIO_AF9_CAN1);
  set_gpio_alternate(GPIOB, 9, GPIO_AF9_CAN1);

  // Setup LED pins
  set_gpio_output(GPIOA, 13, 0);  // Red LED
  set_gpio_output(GPIOA, 14, 0);  // Green LED
  set_gpio_output(GPIOA, 15, 0);  // Yellow LED
  set_gpio_output(GPIOB, 4, 0);   // Blue LED

  // Force harness status to NORMAL for flowpilot compatibility
  // (Pyboard has no harness detection hardware)
  car_harness_status = HARNESS_STATUS_NORMAL;

  // Disable LEDs initially
  pyboard_set_led(LED_RED, false);
  pyboard_set_led(LED_GREEN, false);
  pyboard_set_led(LED_BLUE, false);

  // Set normal CAN mode
  pyboard_set_can_mode(CAN_MODE_NORMAL);
}

void pyboard_board_tick(bool ignition, bool usb_enum, bool heartbeat_seen) {
  UNUSED(ignition);
  UNUSED(usb_enum);
  UNUSED(heartbeat_seen);
}

const harness_configuration pyboard_harness_config = {
  .has_harness = false
};

const board board_pyboard = {
  .board_type = "Pyboard",
  .harness_config = &pyboard_harness_config,
  .has_gps = false,
  .has_hw_gmlan = false,
  .has_obd = false,
  .has_lin = false,
  .has_rtc_battery = true,  // Pyboard has RTC with battery backup
  .fan_max_rpm = 0U,
  .init = pyboard_init,
  .enable_can_transceiver = pyboard_enable_can_transceiver,
  .enable_can_transceivers = pyboard_enable_can_transceivers,
  .set_led = pyboard_set_led,
  .set_gps_mode = pyboard_set_gps_mode,
  .set_can_mode = pyboard_set_can_mode,
  .check_ignition = pyboard_check_ignition,
  .read_current = pyboard_read_current,
  .set_ir_power = unused_set_ir_power,
  .set_fan_enabled = unused_set_fan_enabled,
  .set_phone_power = unused_set_phone_power,
  .set_clock_source_mode = unused_set_clock_source_mode,
  .set_siren = unused_set_siren,
  .board_tick = pyboard_board_tick,
};
