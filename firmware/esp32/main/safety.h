// SPDX-License-Identifier: Apache-2.0
#ifndef SAFETY_H
#define SAFETY_H

#include "esp_err.h"
#include <stdbool.h>

typedef enum {
    SAFETY_NORMAL = 0,
    SAFETY_ESTOPPED,
    SAFETY_RECOVERY_PENDING,
    SAFETY_RELAY_FAULT
} safety_state_t;

typedef void (*safety_callback_t)(safety_state_t state);

esp_err_t safety_init(void);
safety_state_t safety_get_state(void);
bool safety_is_estopped(void);
void safety_trigger_estop(void);
esp_err_t safety_reset(void);
esp_err_t safety_confirm_reset(void);
void safety_register_callback(safety_callback_t cb);
void safety_feed_watchdog(void);
void safety_check_watchdog(void);
void safety_check_recovery_timeout(void);
void safety_process_deferred_stop(void);
void safety_task(void *params);

// Safety relay self-test (run at startup)
esp_err_t safety_relay_selftest(void);

// Returns true if relay hardware is faulted (requires physical service)
bool safety_is_relay_faulted(void);

// Clear relay fault flag in NVS (called after physical service intervention)
esp_err_t safety_clear_relay_fault(void);

// Speed limiter (persisted to NVS)
#define SPEED_LIMIT_HARD_CAP_MPS  1.2f  // meters per second
esp_err_t safety_set_speed_limit(float limit_mps);
float safety_get_speed_limit(void);
float safety_clamp_speed(float requested_mps);
void safety_clamp_velocity(float *vx, float *vy);

#endif // SAFETY_H
