// SPDX-License-Identifier: Apache-2.0
#ifndef ROBOT_PARAMS_H
#define ROBOT_PARAMS_H

// Chassis geometry (mm)
#define WHEEL_RADIUS_MM         24.0f
#define WHEEL_SEPARATION_MM    200.0f   // Track width (left-right center distance)
#define WHEELBASE_MM           180.0f   // Front-rear axle distance
#define ROLLER_ANGLE_DEG        45.0f

// Derived (meters)
#define WHEEL_RADIUS            (WHEEL_RADIUS_MM / 1000.0f)
#define LX                      (WHEELBASE_MM / 2000.0f)
#define LY                      (WHEEL_SEPARATION_MM / 2000.0f)

// Encoder
#define ENCODER_CPR             1440    // Counts per revolution (360 PPR * 4 edges)
#define GEAR_RATIO              90      // 1:90 reduction

// Motor limits
#define MAX_MOTOR_RPM           150     // Output shaft RPM after gearbox
#define MAX_LINEAR_VEL          0.37f   // m/s (derived from wheel_radius * max_rpm)
#define MAX_ANGULAR_VEL         3.0f    // rad/s

// PWM
#define PWM_FREQUENCY_HZ        20000
#define PWM_RESOLUTION_BITS     8
#define PWM_MAX_DUTY            ((1 << PWM_RESOLUTION_BITS) - 1)

// PID defaults (velocity control)
#define PID_KP_DEFAULT          1.2f
#define PID_KI_DEFAULT          0.8f
#define PID_KD_DEFAULT          0.01f
#define PID_INTEGRAL_LIMIT      100.0f

// Control loop
#define CONTROL_FREQ_HZ         50
#define CONTROL_PERIOD_MS       (1000 / CONTROL_FREQ_HZ)

// Safety
#define CMD_VEL_TIMEOUT_MS      500     // Stop motors if no command received
#define WATCHDOG_TIMEOUT_MS     1000    // System watchdog
#define ESTOP_DEBOUNCE_MS       50

// Battery
#define BATT_CELLS_SERIES       2       // 2S configuration
#define BATT_CELL_FULL_V        4.2f
#define BATT_CELL_NOMINAL_V     3.7f
#define BATT_CELL_LOW_V         3.3f    // Warning threshold
#define BATT_CELL_CRITICAL_V    3.0f    // Shutdown threshold
#define BATT_VOLTAGE_DIVIDER    3.0f    // Divider ratio (10k + 20k)
#define BATT_ADC_SAMPLES        8       // Moving average window

// Ultrasonic
#define US_MAX_RANGE_M          4.0f
#define US_MIN_RANGE_M          0.02f
#define US_TRIGGER_PULSE_US     10
#define US_TIMEOUT_US           25000   // ~4.3m max
#define US_SAFETY_THRESHOLD_M   0.05f   // Emergency stop distance

// micro-ROS publish rates
#define ODOM_PUBLISH_HZ         50
#define ULTRASONIC_PUBLISH_HZ   10
#define BATTERY_PUBLISH_HZ      1
#define WHEEL_SPEED_PUBLISH_HZ  50

#endif // ROBOT_PARAMS_H
