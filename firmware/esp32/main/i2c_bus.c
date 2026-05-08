// SPDX-License-Identifier: Apache-2.0
#include "i2c_bus.h"
#include "esp_log.h"

static const char *TAG = "i2c_bus";
static SemaphoreHandle_t i2c_mutex = NULL;

esp_err_t i2c_bus_init(void)
{
    if (i2c_mutex != NULL) return ESP_OK;

    i2c_mutex = xSemaphoreCreateMutex();
    if (i2c_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to create I2C bus mutex");
        return ESP_ERR_NO_MEM;
    }

    ESP_LOGI(TAG, "I2C bus mutex initialized");
    return ESP_OK;
}

SemaphoreHandle_t i2c_bus_get_mutex(void)
{
    return i2c_mutex;
}
