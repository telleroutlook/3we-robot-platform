// SPDX-License-Identifier: Apache-2.0
#ifndef DISPLAY_H
#define DISPLAY_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

typedef enum {
    DISPLAY_PAGE_HOME = 0,
    DISPLAY_PAGE_MOTION,
    DISPLAY_PAGE_FAULTS,
    DISPLAY_PAGE_SYSTEM,
    DISPLAY_PAGE_NETWORK,
    DISPLAY_PAGE_COUNT
} display_page_t;

typedef enum {
    FAULT_SRC_SAFETY = 0,
    FAULT_SRC_THERMAL,
    FAULT_SRC_DRV_FRONT,
    FAULT_SRC_DRV_REAR,
    FAULT_SRC_BATTERY,
    FAULT_SRC_OTA
} display_fault_source_t;

#define DISPLAY_FAULT_LOG_SIZE   3
#define DISPLAY_BTN_DEBOUNCE_MS  50
#define DISPLAY_LONG_PRESS_MS    3000

typedef struct {
    uint32_t timestamp_ms;
    uint8_t  source;
    uint8_t  code;
    char     msg[20];
} display_fault_entry_t;

esp_err_t display_init(void);
void display_task(void *params);
void display_log_fault(display_fault_source_t source, uint8_t code, const char *msg);
display_page_t display_get_current_page(void);

#endif // DISPLAY_H
