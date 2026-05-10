// SPDX-License-Identifier: Apache-2.0
#ifndef BATTERY_H
#define BATTERY_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

typedef enum {
    BATT_OK = 0,
    BATT_LOW,
    BATT_CRITICAL
} battery_state_t;

// Single-pack API (backwards compatible)
esp_err_t battery_init(void);
float battery_read_voltage(void);
uint8_t battery_get_percentage(void);
battery_state_t battery_get_state(void);
void battery_task(void *params);

// Multi-pack extension
#define BATT_PACKS_MAX              2
#define BATT_PACK_PRESENT_THRESHOLD_MV  1000  // >1.0V on ADC = pack present

typedef struct {
    bool present;
    float voltage;
    uint8_t percentage;
    battery_state_t state;
} battery_pack_state_t;

typedef struct {
    uint8_t num_packs_present;
    battery_pack_state_t packs[BATT_PACKS_MAX];
    uint8_t total_percentage;       // Weighted average across present packs
    battery_state_t worst_state;    // Most critical state across all packs
} battery_system_state_t;

battery_system_state_t battery_get_system_state(void);
bool battery_pack_is_present(uint8_t pack_idx);
float battery_pack_get_voltage(uint8_t pack_idx);

#endif // BATTERY_H
