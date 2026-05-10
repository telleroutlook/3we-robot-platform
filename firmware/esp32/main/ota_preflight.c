// SPDX-License-Identifier: Apache-2.0
#include "ota_preflight.h"
#include "battery.h"
#include "safety.h"
#include "motor_control.h"
#include "thermal_monitor.h"

#include "esp_log.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "nvs.h"

#include <string.h>

static const char *TAG = "ota_preflight";

#define NVS_NAMESPACE_OTA   "ota_state"
#define NVS_KEY_BOOT_FAILS  "boot_fails"

ota_preflight_result_t ota_preflight_check(void)
{
    ota_preflight_result_t result = {0};
    result.overall_pass = true;
    result.fail_reason[0] = '\0';

    // Check 1: Battery level
    result.battery_pct = battery_get_percentage();
    result.battery_ok = (result.battery_pct >= OTA_PREFLIGHT_MIN_BATTERY_PCT);
    if (!result.battery_ok) {
        result.overall_pass = false;
        snprintf(result.fail_reason, sizeof(result.fail_reason),
                 "Battery too low: %d%% (min %d%%)",
                 result.battery_pct, OTA_PREFLIGHT_MIN_BATTERY_PCT);
        ESP_LOGW(TAG, "%s", result.fail_reason);
        return result;
    }

    // Check 2: WiFi signal strength
    wifi_ap_record_t ap_info;
    esp_err_t wifi_err = esp_wifi_sta_get_ap_info(&ap_info);
    if (wifi_err == ESP_OK) {
        result.wifi_rssi = ap_info.rssi;
        result.wifi_ok = (ap_info.rssi >= OTA_PREFLIGHT_MIN_WIFI_RSSI);
    } else {
        result.wifi_rssi = -127;
        result.wifi_ok = false;
    }
    if (!result.wifi_ok) {
        result.overall_pass = false;
        snprintf(result.fail_reason, sizeof(result.fail_reason),
                 "WiFi signal weak: %d dBm (min %d dBm)",
                 (int)result.wifi_rssi, OTA_PREFLIGHT_MIN_WIFI_RSSI);
        ESP_LOGW(TAG, "%s", result.fail_reason);
        return result;
    }

    // Check 3: Safety state
    safety_state_t safety = safety_get_state();
    result.safety_ok = (safety == SAFETY_NORMAL);
    if (!result.safety_ok) {
        result.overall_pass = false;
        snprintf(result.fail_reason, sizeof(result.fail_reason),
                 "Safety not normal (state=%d)", (int)safety);
        ESP_LOGW(TAG, "%s", result.fail_reason);
        return result;
    }

    // Check 4: Motors idle
    result.motors_idle = motor_is_stopped();
    if (!result.motors_idle) {
        result.overall_pass = false;
        snprintf(result.fail_reason, sizeof(result.fail_reason),
                 "Motors not idle - stop robot before OTA");
        ESP_LOGW(TAG, "%s", result.fail_reason);
        return result;
    }

    // Check 5: Thermal state
    thermal_state_t thermal = thermal_get_state();
    result.thermal_ok = (thermal != THERMAL_CRITICAL && thermal != THERMAL_SHUTDOWN);
    if (!result.thermal_ok) {
        result.overall_pass = false;
        snprintf(result.fail_reason, sizeof(result.fail_reason),
                 "Thermal state critical - cool down before OTA");
        ESP_LOGW(TAG, "%s", result.fail_reason);
        return result;
    }

    ESP_LOGI(TAG, "Preflight passed: batt=%d%%, rssi=%d, safety=OK, motors=idle, thermal=OK",
             result.battery_pct, (int)result.wifi_rssi);
    return result;
}

uint8_t ota_preflight_get_boot_fail_count(void)
{
    nvs_handle_t nvs;
    uint8_t count = 0;
    if (nvs_open(NVS_NAMESPACE_OTA, NVS_READONLY, &nvs) == ESP_OK) {
        nvs_get_u8(nvs, NVS_KEY_BOOT_FAILS, &count);
        nvs_close(nvs);
    }
    return count;
}

void ota_preflight_increment_boot_fail(void)
{
    nvs_handle_t nvs;
    if (nvs_open(NVS_NAMESPACE_OTA, NVS_READWRITE, &nvs) == ESP_OK) {
        uint8_t count = 0;
        nvs_get_u8(nvs, NVS_KEY_BOOT_FAILS, &count);
        count++;
        nvs_set_u8(nvs, NVS_KEY_BOOT_FAILS, count);
        nvs_commit(nvs);
        nvs_close(nvs);
        ESP_LOGW(TAG, "Boot failure count incremented to %d", count);
    }
}

void ota_preflight_clear_boot_fail(void)
{
    nvs_handle_t nvs;
    if (nvs_open(NVS_NAMESPACE_OTA, NVS_READWRITE, &nvs) == ESP_OK) {
        nvs_set_u8(nvs, NVS_KEY_BOOT_FAILS, 0);
        nvs_commit(nvs);
        nvs_close(nvs);
    }
}
