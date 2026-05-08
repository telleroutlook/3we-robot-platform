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

#endif // SAFETY_H
