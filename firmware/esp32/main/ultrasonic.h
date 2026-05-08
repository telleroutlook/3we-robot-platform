// SPDX-License-Identifier: Apache-2.0
#ifndef ULTRASONIC_H
#define ULTRASONIC_H

#include "esp_err.h"

typedef enum {
    US_FRONT = 0,
    US_BACK,
    US_LEFT,
    US_RIGHT,
    US_COUNT
} ultrasonic_id_t;

esp_err_t ultrasonic_init(void);
esp_err_t ultrasonic_read(ultrasonic_id_t id, float *distance_m);
float ultrasonic_get_last(ultrasonic_id_t id);
void ultrasonic_task(void *params);

#endif // ULTRASONIC_H
