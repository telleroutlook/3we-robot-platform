// SPDX-License-Identifier: Apache-2.0
#include "wifi_provision.h"

#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"

#include <string.h>

static const char *TAG = "wifi_prov";

#define NVS_NAMESPACE   "wifi"
#define NVS_KEY_SSID    "ssid"
#define NVS_KEY_PASS    "password"

esp_err_t wifi_provision_get_credentials(wifi_credentials_t *creds)
{
    if (!creds) return ESP_ERR_INVALID_ARG;

    memset(creds, 0, sizeof(*creds));

    nvs_handle_t nvs;
    bool from_nvs = false;

    if (nvs_open(NVS_NAMESPACE, NVS_READONLY, &nvs) == ESP_OK) {
        size_t ssid_len = WIFI_CRED_MAX_LEN;
        size_t pass_len = WIFI_CRED_MAX_LEN;

        if (nvs_get_str(nvs, NVS_KEY_SSID, creds->ssid, &ssid_len) == ESP_OK &&
            strlen(creds->ssid) > 0) {
            nvs_get_str(nvs, NVS_KEY_PASS, creds->password, &pass_len);
            from_nvs = true;
        }
        nvs_close(nvs);
    }

    if (from_nvs) {
        ESP_LOGI(TAG, "Wi-Fi credentials loaded from NVS");
        return ESP_OK;
    }

#ifdef CONFIG_WIFI_SSID
    strncpy(creds->ssid, CONFIG_WIFI_SSID, WIFI_CRED_MAX_LEN - 1);
#ifdef CONFIG_WIFI_PASSWORD
    strncpy(creds->password, CONFIG_WIFI_PASSWORD, WIFI_CRED_MAX_LEN - 1);
#endif
    if (strlen(creds->ssid) > 0) {
        ESP_LOGW(TAG, "Using Kconfig Wi-Fi credentials (development fallback)");
        return ESP_OK;
    }
#endif

    ESP_LOGE(TAG, "No Wi-Fi credentials available - provision via NVS");
    return ESP_ERR_NOT_FOUND;
}
