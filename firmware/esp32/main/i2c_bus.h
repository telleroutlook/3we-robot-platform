// SPDX-License-Identifier: Apache-2.0
#ifndef I2C_BUS_H
#define I2C_BUS_H

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_err.h"

esp_err_t i2c_bus_init(void);
SemaphoreHandle_t i2c_bus_get_mutex(void);

#define I2C_BUS_LOCK_TIMEOUT pdMS_TO_TICKS(200)

static inline bool i2c_bus_lock(void)
{
    SemaphoreHandle_t mtx = i2c_bus_get_mutex();
    return xSemaphoreTake(mtx, I2C_BUS_LOCK_TIMEOUT) == pdTRUE;
}

static inline void i2c_bus_unlock(void)
{
    xSemaphoreGive(i2c_bus_get_mutex());
}

#endif // I2C_BUS_H
