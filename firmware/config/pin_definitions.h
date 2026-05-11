// SPDX-License-Identifier: Apache-2.0
#ifndef PIN_DEFINITIONS_H
#define PIN_DEFINITIONS_H

#ifdef ESP_PLATFORM
#include "hal/spi_types.h"
#endif

// =============================================================================
// ESP32-S3 Pin Assignment — Robot Platform
// =============================================================================
// GPIO range: 0–48 (all bidirectional except strapping pins)
// Strapping pins (avoid unless PCB provides correct pull resistors): GPIO 0, 3, 45, 46
// USB pins (avoid if using USB-JTAG): GPIO 19, 20
// SPI flash (avoid): GPIO 26–32 (octal SPI), GPIO 33–37 (quad SPI on some modules)
// ADC1: GPIO 1–10; ADC2: GPIO 11–20 (ADC2 unavailable when WiFi active)
// =============================================================================

// Motor GPIOs (DRV8833 x2, dual H-bridge)
#define MOTOR_FL_IN1        13
#define MOTOR_FL_IN2        14
#define MOTOR_FR_IN1        21
#define MOTOR_FR_IN2        47
#define MOTOR_RL_IN1        48
#define MOTOR_RL_IN2        38
#define MOTOR_RR_IN1        39
#define MOTOR_RR_IN2        40

// LEDC PWM channel assignments
#define MOTOR_FL_IN1_CH     0
#define MOTOR_FL_IN2_CH     1
#define MOTOR_FR_IN1_CH     2
#define MOTOR_FR_IN2_CH     3
#define MOTOR_RL_IN1_CH     4
#define MOTOR_RL_IN2_CH     5
#define MOTOR_RR_IN1_CH     6
#define MOTOR_RR_IN2_CH     7

// Ultrasonic sensors (HC-SR04, shared trigger)
#define US_TRIG             12
#define US_ECHO_FRONT       11
#define US_ECHO_BACK        10
#define US_ECHO_LEFT        9
#define US_ECHO_RIGHT       18

// Quadrature encoders (A/B channels per wheel)
#define ENC_FL_A            5
#define ENC_FL_B            6
#define ENC_FR_A            7
#define ENC_FR_B            15
#define ENC_RL_A            16
#define ENC_RL_B            17
#define ENC_RR_A            8
#define ENC_RR_B            4

// I2C bus (IMU + power monitor + MCP23017)
#define I2C_SDA             1
#define I2C_SCL             2
#define I2C_FREQ_HZ        400000

// IMU I2C address
#define IMU_ADDR            0x28  // BNO055 default
#define IMU_ADDR_ALT        0x29  // BNO055 alternate

// Power monitor (INA219)
#define INA219_ADDR         0x40

// micro-ROS UART
#define UROS_UART_NUM       UART_NUM_1
#define UROS_TX             43
#define UROS_RX             44
#define UROS_BAUD           921600

// Battery ADC (dedicated pin, ADC1)
#define BATT_ADC_GPIO       3
#define BATT_ADC_CHANNEL    ADC_CHANNEL_2   // ESP32-S3: GPIO 3 = ADC1_CH2
#define BATT_ADC_ATTEN      ADC_ATTEN_DB_11

// Battery pack 2 ADC (extended battery SKU)
// WARNING: GPIO 4 is shared with ENC_RR_B. Only one can be active at a time.
// Multi-pack battery sensing requires the extended encoder wiring (ENC_RR_B on GPIO 15
// via alternate routing) or a dedicated ADC-only build with 3-wheel encoder feedback.
#ifndef CONFIG_ROBOT_DUAL_BATTERY
#define BATT_PACK2_ADC_GPIO     4
#define BATT_PACK2_ADC_CHANNEL  ADC_CHANNEL_3   // ESP32-S3: GPIO 4 = ADC1_CH3
#else
// When dual-battery is enabled, ENC_RR_B must use alternate GPIO.
// See Kconfig CONFIG_ENC_RR_B_ALT_GPIO for reroute.
#define BATT_PACK2_ADC_GPIO     4
#define BATT_PACK2_ADC_CHANNEL  ADC_CHANNEL_3
#endif

// Safety / E-stop (dedicated pins, no sharing)
#define ESTOP_GPIO          41  // NC button, active-low when pressed
#define SAFETY_RELAY_FB     42  // Relay feedback channel 1 (verify relay state)
#define SAFETY_RELAY_FB2    22  // Relay feedback channel 2 (dual-channel redundancy for CE PL d)

// Pi 5 power relay (heartbeat watchdog)
// NOTE: GPIO 45 is VDD_SPI strapping pin. PCB pulls to 3.3V via 10k at boot
// to select 3.3V flash voltage. Relay is NMOS-driven so GPIO idle-low is safe.
#define PI5_RELAY_GPIO      45  // Controls Pi 5 power via relay (active-high = ON)

// External watchdog IC feed (TPS3813)
// NOTE: GPIO 46 is boot-mode strapping pin. PCB pulls low via 10k at boot
// (normal SPI boot). TPS3813 WDI input is high-impedance so no conflict.
#define EXT_WDT_FEED_GPIO   46  // Toggle to feed external WDT — stops toggling = HW reset

// Charging contact detection (ADC1, pogo pin voltage sense)
// Note: shares GPIO 9 with US_ECHO_LEFT — docking builds must omit side ultrasonics
#ifdef CONFIG_ROBOT_DOCKING_ENABLED
#define CHARGE_ADC_GPIO     9   // ADC1_CH8 on ESP32-S3
#define CHARGE_ADC_CHANNEL  ADC_CHANNEL_8
#define CHARGE_ADC_ATTEN    ADC_ATTEN_DB_11  // ESP-IDF 5.x (was ADC_ATTEN_DB_12 in 4.x)
#endif

// Payload bus control (via MCP23017 I2C expander)
#define MCP23017_ADDR       0x20
#define PAYLOAD_5V_EN_BIT   0   // GPA0 on MCP23017
#define PAYLOAD_12V_EN_BIT  1   // GPA1 on MCP23017
#define PAYLOAD_VBAT_EN_BIT 2   // GPA2 on MCP23017
#define PAYLOAD_DETECT_BIT  3   // GPA3 on MCP23017 (input)

// CAN bus (MCP2515 + TJA1050, Industrial SKU only)
// GPIO 33–37 are occupied by PSRAM on ESP32-S3-WROOM-1-N8R8 — must avoid.
// Industrial SKU omits the HC-SR04 ultrasonic array (uses LiDAR instead),
// freeing those GPIOs for CAN SPI.
// Defines are always available (tests, canbus driver compilation) but the
// driver is only initialized at runtime when CONFIG_ROBOT_SKU_INDUSTRIAL is set.
#define CAN_SPI_HOST        SPI2_HOST
#define CAN_MOSI            11  // was US_ECHO_FRONT on Basic/Standard
#define CAN_MISO            10  // was US_ECHO_BACK on Basic/Standard
#define CAN_SCLK            12  // was US_TRIG on Basic/Standard
#define CAN_CS              18  // was US_ECHO_RIGHT on Basic/Standard
#define CAN_INT              9  // was US_ECHO_LEFT on Basic/Standard

// =============================================================================
// Industrial SKU: BTS7960 Motor Driver Configuration
// =============================================================================
// BTS7960 module pinout: RPWM (forward PWM), LPWM (reverse PWM), R_EN, L_EN.
// R_EN and L_EN are active-high enables — tied HIGH on the Industrial PCB via
// pull-up resistors, so only RPWM/LPWM need GPIO control (same 2-pin-per-motor
// topology as DRV8833 IN1/IN2). The existing motor_config_t struct works for both.
// Industrial PWM frequency is 15 kHz (BTS7960 optimal range: 10–25 kHz).
#ifdef CONFIG_ROBOT_SKU_INDUSTRIAL
// Industrial uses the same motor GPIOs but at 15 kHz PWM.
// Motor pin mapping is identical to DRV8833 layout (RPWM=IN1, LPWM=IN2).
// BTS7960 R_EN/L_EN pins are hardware-pulled HIGH (not software-controlled).
#define BTS7960_EN_ACTIVE   1  // Flag: enables are hardware-tied, no GPIO needed
#endif

#endif // PIN_DEFINITIONS_H
