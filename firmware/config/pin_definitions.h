// SPDX-License-Identifier: Apache-2.0
#ifndef PIN_DEFINITIONS_H
#define PIN_DEFINITIONS_H

// Motor GPIOs (DRV8833 x2, dual H-bridge)
#define MOTOR_FL_IN1        13
#define MOTOR_FL_IN2        14
#define MOTOR_FR_IN1        27
#define MOTOR_FR_IN2        4
#define MOTOR_RL_IN1        32
#define MOTOR_RL_IN2        33
#define MOTOR_RR_IN1        25
#define MOTOR_RR_IN2        15

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
#define US_ECHO_FRONT       34
#define US_ECHO_BACK        35
#define US_ECHO_LEFT        36
#define US_ECHO_RIGHT       39

// Quadrature encoders (A/B channels per wheel)
#define ENC_FL_A            26
#define ENC_FL_B            18
#define ENC_FR_A            23
#define ENC_FR_B            19
#define ENC_RL_A            5
#define ENC_RL_B            0
#define ENC_RR_A            2
#define ENC_RR_B            15

// I2C bus (IMU + power monitor)
#define I2C_SDA             21
#define I2C_SCL             22
#define I2C_FREQ_HZ        400000

// IMU I2C address
#define IMU_ADDR            0x28  // BNO055 default
#define IMU_ADDR_ALT        0x29  // BNO055 alternate

// Power monitor (INA219)
#define INA219_ADDR         0x40

// micro-ROS UART
#define UROS_UART_NUM       UART_NUM_1
#define UROS_TX             17
#define UROS_RX             16
#define UROS_BAUD           921600

// Battery ADC
#define BATT_ADC_GPIO       34  // Shared with US_ECHO_FRONT (muxed)
#define BATT_ADC_CHANNEL    ADC1_CHANNEL_6
#define BATT_ADC_ATTEN      ADC_ATTEN_DB_11

// Safety / E-stop
#define ESTOP_GPIO          36  // NC button, active-low when pressed
#define SAFETY_RELAY_FB     39  // Relay feedback (verify relay state)

// Payload bus control (via MCP23017 I2C expander)
#define MCP23017_ADDR       0x20
#define PAYLOAD_5V_EN_BIT   0   // GPA0 on MCP23017
#define PAYLOAD_12V_EN_BIT  1   // GPA1 on MCP23017
#define PAYLOAD_VBAT_EN_BIT 2   // GPA2 on MCP23017
#define PAYLOAD_DETECT_BIT  3   // GPA3 on MCP23017 (input)

// CAN bus (MCP2515 + TJA1050, Industrial SKU only)
#define CAN_SPI_HOST        SPI3_HOST
#define CAN_MOSI            11
#define CAN_MISO            13
#define CAN_SCLK            12
#define CAN_CS              10
#define CAN_INT             9

#endif // PIN_DEFINITIONS_H
