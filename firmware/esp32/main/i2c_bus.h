// SPDX-License-Identifier: Apache-2.0
#ifndef I2C_BUS_H
#define I2C_BUS_H

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>

esp_err_t i2c_bus_init(void);
SemaphoreHandle_t i2c_bus_get_mutex(void);

// MCP23017 register-level helpers (shared by payload_hotplug, payload_power)
esp_err_t mcp23017_write_bit(uint8_t device_addr, uint8_t reg_addr, uint8_t bit, bool value);
esp_err_t mcp23017_read_register(uint8_t device_addr, uint8_t reg_addr, uint8_t *out);

#define I2C_BUS_LOCK_TIMEOUT pdMS_TO_TICKS(200)

static inline bool i2c_bus_lock(void)
{
    SemaphoreHandle_t mtx = i2c_bus_get_mutex();
    if (mtx == NULL) return false;
    return xSemaphoreTake(mtx, I2C_BUS_LOCK_TIMEOUT) == pdTRUE;
}

static inline void i2c_bus_unlock(void)
{
    SemaphoreHandle_t mtx = i2c_bus_get_mutex();
    if (mtx != NULL) {
        xSemaphoreGive(mtx);
    }
}

#endif // I2C_BUS_H
