// SPDX-License-Identifier: Apache-2.0
#ifndef OTA_PREFLIGHT_H
#define OTA_PREFLIGHT_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

#define OTA_PREFLIGHT_MIN_BATTERY_PCT       50
#define OTA_PREFLIGHT_MIN_WIFI_RSSI         (-70)
#define OTA_PREFLIGHT_VALIDATION_TIMEOUT_MS 30000
#define OTA_PREFLIGHT_MAX_BOOT_FAILURES     3

typedef struct {
    bool battery_ok;
    bool wifi_ok;
    bool safety_ok;
    bool motors_idle;
    bool thermal_ok;
    bool overall_pass;
    uint8_t battery_pct;
    int8_t wifi_rssi;
    char fail_reason[64];
} ota_preflight_result_t;

ota_preflight_result_t ota_preflight_check(void);

uint8_t ota_preflight_get_boot_fail_count(void);
void ota_preflight_increment_boot_fail(void);
void ota_preflight_clear_boot_fail(void);

#endif // OTA_PREFLIGHT_H
