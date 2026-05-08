// SPDX-License-Identifier: Apache-2.0
#include "i2c_bus.h"
#include "pin_definitions.h"

#include "driver/i2c.h"
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

    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_SDA,
        .scl_io_num = I2C_SCL,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_FREQ_HZ,
    };
    ESP_ERROR_CHECK(i2c_param_config(I2C_NUM_0, &conf));
    ESP_ERROR_CHECK(i2c_driver_install(I2C_NUM_0, I2C_MODE_MASTER, 0, 0, 0));

    ESP_LOGI(TAG, "I2C bus initialized (SDA=%d, SCL=%d, freq=%d Hz)",
             I2C_SDA, I2C_SCL, I2C_FREQ_HZ);
    return ESP_OK;
}

SemaphoreHandle_t i2c_bus_get_mutex(void)
{
    return i2c_mutex;
}
