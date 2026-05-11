// SPDX-License-Identifier: Apache-2.0
#pragma once

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

#define CURRENT_SENSE_CHANNELS  4

typedef struct {
    float current_ma[CURRENT_SENSE_CHANNELS];
    float total_current_ma;
    uint32_t overcurrent_flags;
} current_reading_t;

typedef enum {
    CURRENT_OK = 0,
    CURRENT_SOFT_LIMIT,
    CURRENT_HARD_LIMIT,
} current_state_t;

esp_err_t current_sense_init(void);
esp_err_t current_sense_read(current_reading_t *reading);
current_state_t current_sense_get_state(int channel);
void current_sense_update(void);
