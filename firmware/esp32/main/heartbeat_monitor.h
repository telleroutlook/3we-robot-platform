// SPDX-License-Identifier: Apache-2.0
#ifndef HEARTBEAT_MONITOR_H
#define HEARTBEAT_MONITOR_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

#define HEARTBEAT_TIMEOUT_MS        5000
#define HEARTBEAT_MAX_RESETS        3
#define HEARTBEAT_RESET_WINDOW_MS   (30 * 60 * 1000)  // 30 minutes
#define HEARTBEAT_RELAY_PULSE_MS    3000               // Hold relay off for 3s

typedef enum {
    HB_STATE_WAITING = 0,
    HB_STATE_ACTIVE,
    HB_STATE_TIMEOUT,
    HB_STATE_SAFE_MODE
} heartbeat_state_t;

typedef struct {
    heartbeat_state_t state;
    int64_t last_heartbeat_us;
    uint8_t reset_count;
    int64_t first_reset_us;
} heartbeat_status_t;

esp_err_t heartbeat_monitor_init(void);
void heartbeat_feed(void);
heartbeat_state_t heartbeat_get_state(void);
heartbeat_status_t heartbeat_get_status(void);
void heartbeat_monitor_task(void *params);

#endif // HEARTBEAT_MONITOR_H
