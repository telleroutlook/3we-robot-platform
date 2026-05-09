// SPDX-License-Identifier: Apache-2.0
#ifndef MOTOR_CONTROL_H
#define MOTOR_CONTROL_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

typedef enum {
    MOTOR_FL = 0,
    MOTOR_FR,
    MOTOR_RL,
    MOTOR_RR,
    MOTOR_COUNT
} motor_id_t;

typedef struct {
    float vx;       // Forward velocity (m/s)
    float vy;       // Lateral velocity (m/s, positive = left)
    float omega;    // Angular velocity (rad/s, positive = CCW)
} cmd_vel_t;

typedef struct {
    float speeds[MOTOR_COUNT];  // Commanded duty cycle (-1.0 to 1.0)
} motor_output_t;

esp_err_t motor_init(void);
void motor_set_speed(motor_id_t id, float speed_pct);
motor_output_t motor_mecanum_drive(const cmd_vel_t *cmd);
void motor_stop_all(void);
bool motor_is_stopped(void);

#endif // MOTOR_CONTROL_H
