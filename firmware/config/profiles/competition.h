// SPDX-License-Identifier: Apache-2.0
#pragma once

// Standard version - Competition configuration
// Activated via CONFIG_ROBOT_PROFILE_COMPETITION in Kconfig
//
// Hardware requirements:
//   - N20 motor with 1:30 gear ratio
//   - Magnetic encoder with >=12 CPR (raw)
//   - 48mm Mecanum wheels
//   - 300x250mm chassis (standard-version competition variant)

#define COMPETITION_GEAR_RATIO          30
#define COMPETITION_MAX_MOTOR_RPM       500
#define COMPETITION_ENCODER_PPR         360     // 12-line x 30 gear = 360 PPR

#define COMPETITION_WHEEL_RADIUS_MM     24.0f
#define COMPETITION_TRACK_WIDTH_MM      200.0f
#define COMPETITION_WHEELBASE_MM        180.0f

#define COMPETITION_MAX_VEL_LINEAR      0.8f    // m/s
#define COMPETITION_MAX_VEL_ANGULAR     2.5f    // rad/s
#define COMPETITION_ACCEL_LIMIT         2.0f    // m/s²
#define COMPETITION_DECEL_LIMIT         3.0f    // m/s² (braking faster than accel)

#define COMPETITION_US_THRESHOLD_M      0.03f   // 3cm (controlled competition environment)
#define COMPETITION_CMD_TIMEOUT_MS      200     // Shorter timeout for faster response

#define COMPETITION_PID_KP              1.8f
#define COMPETITION_PID_KI              1.2f
#define COMPETITION_PID_KD              0.02f
