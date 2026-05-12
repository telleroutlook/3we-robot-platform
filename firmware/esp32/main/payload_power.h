// SPDX-License-Identifier: Apache-2.0
#ifndef PAYLOAD_POWER_H
#define PAYLOAD_POWER_H

#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>

#define POWER_RAIL_MAX  4

typedef enum {
    POWER_RAIL_OFF = 0,
    POWER_RAIL_RAMPING,
    POWER_RAIL_ON,
    POWER_RAIL_FAULT,
} power_rail_state_t;

typedef struct {
    const char *name;
    uint8_t mcp23017_addr;
    uint8_t mcp23017_reg;
    uint8_t mcp23017_bit;
    uint16_t max_current_ma;
    uint16_t soft_start_delay_ms;
    uint16_t overcurrent_duration_ms;
    bool enabled;
} power_rail_config_t;

typedef struct {
    power_rail_state_t state;
    uint16_t current_ma;
    int64_t state_change_time_us;
} power_rail_status_t;

esp_err_t payload_power_init(const power_rail_config_t *configs, int num_rails);
esp_err_t payload_power_enable_rail(int rail_index);
esp_err_t payload_power_disable_rail(int rail_index);
esp_err_t payload_power_disable_all(void);
power_rail_state_t payload_power_get_state(int rail_index);
esp_err_t payload_power_get_status(int rail_index, power_rail_status_t *out);
int payload_power_get_rail_count(void);

#endif // PAYLOAD_POWER_H
