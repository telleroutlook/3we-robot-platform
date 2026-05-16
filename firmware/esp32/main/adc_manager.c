// SPDX-License-Identifier: Apache-2.0
#include "adc_manager.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

static const char *TAG = "adc_mgr";
static adc_oneshot_unit_handle_t s_handle = NULL;
static bool s_initialized = false;
static SemaphoreHandle_t s_mutex = NULL;

esp_err_t adc_manager_init(void)
{
    if (s_initialized) return ESP_OK;

    adc_oneshot_unit_init_cfg_t unit_cfg = {
        .unit_id = ADC_UNIT_1,
    };
    esp_err_t err = adc_oneshot_new_unit(&unit_cfg, &s_handle);
    if (err != ESP_OK) return err;

    s_mutex = xSemaphoreCreateMutex();

    s_initialized = true;
    ESP_LOGI(TAG, "ADC_UNIT_1 initialized");
    return ESP_OK;
}

adc_oneshot_unit_handle_t adc_manager_get_handle(void)
{
    return s_handle;
}

esp_err_t adc_manager_read(int channel, int *out_raw)
{
    if (!s_initialized) return ESP_ERR_INVALID_STATE;
    if (xSemaphoreTake(s_mutex, pdMS_TO_TICKS(50)) != pdTRUE) {
        return ESP_ERR_TIMEOUT;
    }
    esp_err_t err = adc_oneshot_read(s_handle, channel, out_raw);
    xSemaphoreGive(s_mutex);
    return err;
}
