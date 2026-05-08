// SPDX-License-Identifier: Apache-2.0
#ifndef BATTERY_H
#define BATTERY_H

#include "esp_err.h"

typedef enum {
    BATT_OK = 0,
    BATT_LOW,
    BATT_CRITICAL
} battery_state_t;

esp_err_t battery_init(void);
float battery_read_voltage(void);
uint8_t battery_get_percentage(void);
battery_state_t battery_get_state(void);
void battery_task(void *params);

#endif // BATTERY_H
