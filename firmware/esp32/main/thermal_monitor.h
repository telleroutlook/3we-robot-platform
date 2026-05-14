// SPDX-License-Identifier: Apache-2.0
#ifndef THERMAL_MONITOR_H
#define THERMAL_MONITOR_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

#define THERMAL_WARNING_TEMP_C  70.0f
#define THERMAL_CRITICAL_TEMP_C 85.0f
#define THERMAL_SHUTDOWN_TEMP_C 95.0f
#define THERMAL_CURRENT_MAX_A   3.0f
#define THERMAL_HYSTERESIS_C    10.0f

typedef enum {
    THERMAL_OK = 0,
    THERMAL_WARNING,
    THERMAL_CRITICAL,
    THERMAL_SHUTDOWN
} thermal_state_t;

typedef struct {
    float bus_voltage_v;
    float shunt_voltage_mv;
    float current_ma;
    float power_mw;
    float estimated_temp_c;
    float ntc_temp_c;
    float effective_temp_c;
    thermal_state_t state;
} thermal_reading_t;

typedef void (*thermal_callback_t)(thermal_state_t state, const thermal_reading_t *reading);

esp_err_t thermal_monitor_init(void);
thermal_state_t thermal_get_state(void);
esp_err_t thermal_get_reading(thermal_reading_t *reading);
void thermal_register_callback(thermal_callback_t cb);
void thermal_monitor_task(void *params);

#endif // THERMAL_MONITOR_H
