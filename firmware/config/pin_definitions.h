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
// Strapping pins (avoid): GPIO 0, 3, 45, 46
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

// Safety / E-stop (dedicated pins, no sharing)
#define ESTOP_GPIO          41  // NC button, active-low when pressed
#define SAFETY_RELAY_FB     42  // Relay feedback (verify relay state)

// Payload bus control (via MCP23017 I2C expander)
#define MCP23017_ADDR       0x20
#define PAYLOAD_5V_EN_BIT   0   // GPA0 on MCP23017
#define PAYLOAD_12V_EN_BIT  1   // GPA1 on MCP23017
#define PAYLOAD_VBAT_EN_BIT 2   // GPA2 on MCP23017
#define PAYLOAD_DETECT_BIT  3   // GPA3 on MCP23017 (input)

// CAN bus (MCP2515 + TJA1050, Industrial SKU only)
// Uses dedicated SPI pins that don't conflict with motor/sensor GPIOs
#define CAN_SPI_HOST        SPI3_HOST
#define CAN_MOSI            35
#define CAN_MISO            37
#define CAN_SCLK            36
#define CAN_CS              34
#define CAN_INT             33

#endif // PIN_DEFINITIONS_H
