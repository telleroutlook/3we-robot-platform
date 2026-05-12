// SPDX-License-Identifier: Apache-2.0
#include "i2c_bus.h"
#include "pin_definitions.h"

#include "driver/i2c.h"
#include "esp_log.h"

#ifndef TESTABLE_WEAK
#define TESTABLE_WEAK
#endif

static const char *TAG = "i2c_bus";
static SemaphoreHandle_t i2c_mutex = NULL;

TESTABLE_WEAK esp_err_t i2c_bus_init(void)
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

TESTABLE_WEAK SemaphoreHandle_t i2c_bus_get_mutex(void)
{
    return i2c_mutex;
}

TESTABLE_WEAK esp_err_t mcp23017_write_bit(uint8_t device_addr, uint8_t reg_addr, uint8_t bit, bool value)
{
    uint8_t reg_val = 0;

    if (!i2c_bus_lock()) return ESP_ERR_TIMEOUT;

    esp_err_t err = i2c_master_write_read_device(I2C_NUM_0, device_addr, &reg_addr, 1,
                                                  &reg_val, 1, pdMS_TO_TICKS(50));
    if (err != ESP_OK) {
        i2c_bus_unlock();
        return err;
    }

    if (value) reg_val |= (1 << bit);
    else reg_val &= ~(1 << bit);

    uint8_t buf[2] = { reg_addr, reg_val };
    err = i2c_master_write_to_device(I2C_NUM_0, device_addr, buf, 2, pdMS_TO_TICKS(50));
    i2c_bus_unlock();
    return err;
}

TESTABLE_WEAK esp_err_t mcp23017_read_register(uint8_t device_addr, uint8_t reg_addr, uint8_t *out)
{
    if (out == NULL) return ESP_ERR_INVALID_ARG;

    if (!i2c_bus_lock()) return ESP_ERR_TIMEOUT;

    esp_err_t err = i2c_master_write_read_device(I2C_NUM_0, device_addr, &reg_addr, 1,
                                                  out, 1, pdMS_TO_TICKS(50));
    i2c_bus_unlock();
    return err;
}
