// SPDX-License-Identifier: Apache-2.0
#include "i2c_bus.h"
#include "pin_definitions.h"

#include "driver/i2c.h"
#include "driver/gpio.h"
#include "esp_log.h"
#ifndef UNIT_TEST_BUILD
#include "esp_rom_sys.h"
#endif

#ifndef TESTABLE_WEAK
#define TESTABLE_WEAK
#endif

static const char *TAG = "i2c_bus";
static SemaphoreHandle_t i2c_mutex = NULL;

TESTABLE_WEAK esp_err_t i2c_bus_recover(void)
{
    ESP_LOGW(TAG, "Attempting I2C bus recovery (9 SCL clocks)");

    if (!xSemaphoreTake(i2c_mutex, pdMS_TO_TICKS(500))) {
        ESP_LOGE(TAG, "Cannot acquire I2C mutex for recovery");
        return ESP_ERR_TIMEOUT;
    }

    i2c_driver_delete(I2C_NUM_0);

    gpio_config_t scl_cfg = {
        .pin_bit_mask = (1ULL << I2C_SCL),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
    };
    gpio_config(&scl_cfg);

    gpio_config_t sda_cfg = {
        .pin_bit_mask = (1ULL << I2C_SDA),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
    };
    gpio_config(&sda_cfg);

    for (int i = 0; i < 9; i++) {
        gpio_set_level(I2C_SCL, 0);
        esp_rom_delay_us(5);
        gpio_set_level(I2C_SCL, 1);
        esp_rom_delay_us(5);
        if (gpio_get_level(I2C_SDA) == 1) break;
    }

    // Generate STOP condition
    gpio_set_level(I2C_SCL, 0);
    gpio_config_t sda_out = {
        .pin_bit_mask = (1ULL << I2C_SDA),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
    };
    gpio_config(&sda_out);
    gpio_set_level(I2C_SDA, 0);
    esp_rom_delay_us(5);
    gpio_set_level(I2C_SCL, 1);
    esp_rom_delay_us(5);
    gpio_set_level(I2C_SDA, 1);

    // Re-init I2C driver
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_SDA,
        .scl_io_num = I2C_SCL,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_FREQ_HZ,
    };
    esp_err_t err = i2c_param_config(I2C_NUM_0, &conf);
    if (err != ESP_OK) return err;
    err = i2c_driver_install(I2C_NUM_0, I2C_MODE_MASTER, 0, 0, 0);
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "I2C bus recovered successfully");
    }
    xSemaphoreGive(i2c_mutex);
    return err;
}

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
