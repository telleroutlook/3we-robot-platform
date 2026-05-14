// SPDX-License-Identifier: Apache-2.0
#include "wifi_provision.h"

#include "esp_log.h"
#include "esp_wifi.h"
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

#if defined(CONFIG_WIFI_SSID) && !defined(CONFIG_PRODUCTION_BUILD)
    strncpy(creds->ssid, CONFIG_WIFI_SSID, WIFI_CRED_MAX_LEN - 1); // nosemgrep
#ifdef CONFIG_WIFI_PASSWORD
    strncpy(creds->password, CONFIG_WIFI_PASSWORD, WIFI_CRED_MAX_LEN - 1); // nosemgrep
#endif
    if (strlen(creds->ssid) > 0) {
        ESP_LOGW(TAG, "Using Kconfig Wi-Fi credentials (development fallback)");
        return ESP_OK;
    }
#endif

    ESP_LOGE(TAG, "No Wi-Fi credentials available - provision via NVS");
    return ESP_ERR_NOT_FOUND;
}

esp_err_t wifi_provision_store_credentials(const char *ssid, const char *password)
{
    if (!ssid || strlen(ssid) == 0) return ESP_ERR_INVALID_ARG;

    nvs_handle_t nvs;
    esp_err_t ret = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (ret != ESP_OK) return ret;

    ret = nvs_set_str(nvs, NVS_KEY_SSID, ssid);
    if (ret != ESP_OK) {
        nvs_close(nvs);
        return ret;
    }

    ret = nvs_set_str(nvs, NVS_KEY_PASS, password ? password : "");
    if (ret != ESP_OK) {
        nvs_close(nvs);
        return ret;
    }

    ret = nvs_commit(nvs);
    nvs_close(nvs);

    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Wi-Fi credentials stored for SSID: %s", ssid);
    }
    return ret;
}

esp_err_t wifi_provision_start_sta(void)
{
    wifi_credentials_t creds;
    esp_err_t ret = wifi_provision_get_credentials(&creds);
    if (ret != ESP_OK) return ret;

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));

    wifi_config_t sta_cfg = {0};
    strncpy((char *)sta_cfg.sta.ssid, creds.ssid, sizeof(sta_cfg.sta.ssid) - 1); // nosemgrep
    strncpy((char *)sta_cfg.sta.password, creds.password, sizeof(sta_cfg.sta.password) - 1); // nosemgrep

    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &sta_cfg));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_connect());

    ESP_LOGI(TAG, "STA mode started, connecting to: %s", creds.ssid);
    return ESP_OK;
}
