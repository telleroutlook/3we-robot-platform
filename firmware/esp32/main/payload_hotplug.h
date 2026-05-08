// SPDX-License-Identifier: Apache-2.0
#ifndef PAYLOAD_HOTPLUG_H
#define PAYLOAD_HOTPLUG_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

typedef enum {
    PAYLOAD_STATE_ABSENT = 0,
    PAYLOAD_STATE_DETECTED,
    PAYLOAD_STATE_IDENTIFYING,
    PAYLOAD_STATE_POWERING,
    PAYLOAD_STATE_READY,
    PAYLOAD_STATE_FAULT,
    PAYLOAD_STATE_REMOVING
} payload_state_t;

typedef struct {
    char payload_id[17];
    char name[33];
    uint16_t power_5v_ma;
    uint16_t power_12v_ma;
    uint8_t capabilities;
    uint8_t gpio_mask;
} payload_descriptor_t;

typedef void (*payload_event_callback_t)(payload_state_t state,
                                         const payload_descriptor_t *desc);

esp_err_t payload_hotplug_init(void);
payload_state_t payload_get_state(void);
const payload_descriptor_t *payload_get_descriptor(void);
void payload_register_callback(payload_event_callback_t cb);
esp_err_t payload_power_off(void);
void payload_hotplug_task(void *params);

#endif // PAYLOAD_HOTPLUG_H
