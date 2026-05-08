// SPDX-License-Identifier: Apache-2.0
#ifndef SAFETY_H
#define SAFETY_H

#include "esp_err.h"
#include <stdbool.h>

typedef enum {
    SAFETY_NORMAL = 0,
    SAFETY_ESTOPPED,
    SAFETY_RECOVERY_PENDING
} safety_state_t;

typedef void (*safety_callback_t)(safety_state_t state);

esp_err_t safety_init(void);
safety_state_t safety_get_state(void);
bool safety_is_estopped(void);
void safety_trigger_estop(void);
esp_err_t safety_reset(void);
void safety_register_callback(safety_callback_t cb);
void safety_feed_watchdog(void);
void safety_task(void *params);

// Safety relay self-test (run at startup)
esp_err_t safety_relay_selftest(void);

// Speed limiter (persisted to NVS)
#define SPEED_LIMIT_HARD_CAP_MS  1.2f
esp_err_t safety_set_speed_limit(float limit_ms);
float safety_get_speed_limit(void);
float safety_clamp_speed(float requested_ms);

#endif // SAFETY_H
