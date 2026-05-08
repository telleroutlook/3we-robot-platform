// SPDX-License-Identifier: Apache-2.0
#ifndef ENCODER_H
#define ENCODER_H

#include "esp_err.h"
#include "motor_control.h"

esp_err_t encoder_init(void);
int32_t encoder_get_count(motor_id_t id);
float encoder_get_speed_rps(motor_id_t id);
void encoder_update(void);

#endif // ENCODER_H
