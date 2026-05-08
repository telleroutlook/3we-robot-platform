// SPDX-License-Identifier: Apache-2.0
#include "thermal_monitor.h"
#include "motor_control.h"
#include "pin_definitions.h"

#include "driver/i2c.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <string.h>
#include <math.h>

static const char *TAG = "thermal";

// INA219 registers
#define INA219_REG_CONFIG   0x00
#define INA219_REG_SHUNT_V 0x01
#define INA219_REG_BUS_V   0x02
#define INA219_REG_POWER   0x03
#define INA219_REG_CURRENT 0x04
#define INA219_REG_CALIB   0x05

// INA219 config: 32V range, 320mV shunt, 12-bit, continuous
#define INA219_CONFIG       0x399F

// Calibration for 0.1 ohm shunt resistor, 3.2A max
#define INA219_CALIBRATION  4096
#define SHUNT_RESISTANCE    0.1f

// Thermal model: estimate temperature from power dissipation
// Rth_ja ~= 40°C/W for typical motor driver package + PCB
#define THERMAL_RESISTANCE  40.0f
#define AMBIENT_TEMP_C      25.0f

static thermal_state_t state = THERMAL_OK;
static thermal_callback_t user_callback = NULL;
static thermal_reading_t last_reading;

static esp_err_t ina219_write_reg(uint8_t reg, uint16_t value)
{
    uint8_t buf[3] = { reg, (value >> 8) & 0xFF, value & 0xFF };
    return i2c_master_write_to_device(I2C_NUM_0, INA219_ADDR, buf, 3, pdMS_TO_TICKS(50));
}

static esp_err_t ina219_read_reg(uint8_t reg, uint16_t *value)
{
    uint8_t data[2];
    esp_err_t err = i2c_master_write_read_device(I2C_NUM_0, INA219_ADDR,
                                                  &reg, 1, data, 2, pdMS_TO_TICKS(50));
    if (err == ESP_OK) {
        *value = ((uint16_t)data[0] << 8) | data[1];
    }
    return err;
}

esp_err_t thermal_monitor_init(void)
{
    // Reset INA219
    esp_err_t err = ina219_write_reg(INA219_REG_CONFIG, 0x8000);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "INA219 reset failed (addr 0x%02X)", INA219_ADDR);
        return err;
    }
    vTaskDelay(pdMS_TO_TICKS(5));

    // Set calibration register
    err = ina219_write_reg(INA219_REG_CALIB, INA219_CALIBRATION);
    if (err != ESP_OK) return err;

    // Configure measurement mode
    err = ina219_write_reg(INA219_REG_CONFIG, INA219_CONFIG);
    if (err != ESP_OK) return err;

    state = THERMAL_OK;
    memset(&last_reading, 0, sizeof(last_reading));
    ESP_LOGI(TAG, "Thermal monitor initialized (INA219 at 0x%02X)", INA219_ADDR);
    return ESP_OK;
}

thermal_state_t thermal_get_state(void)
{
    return state;
}

esp_err_t thermal_get_reading(thermal_reading_t *reading)
{
    if (!reading) return ESP_ERR_INVALID_ARG;
    *reading = last_reading;
    return ESP_OK;
}

void thermal_register_callback(thermal_callback_t cb)
{
    user_callback = cb;
}

static void update_thermal_state(thermal_reading_t *r)
{
    // Estimate junction temperature from power dissipation
    float power_w = r->power_mw / 1000.0f;
    r->estimated_temp_c = AMBIENT_TEMP_C + (power_w * THERMAL_RESISTANCE);

    thermal_state_t new_state;
    if (r->estimated_temp_c >= THERMAL_CRITICAL_TEMP_C ||
        fabsf(r->current_ma) > (THERMAL_CURRENT_MAX_A * 1000.0f)) {
        new_state = THERMAL_SHUTDOWN;
    } else if (r->estimated_temp_c >= THERMAL_WARNING_TEMP_C) {
        new_state = THERMAL_WARNING;
    } else {
        new_state = THERMAL_OK;
    }

    if (new_state != state) {
        state = new_state;
        if (state == THERMAL_SHUTDOWN) {
            motor_stop_all();
            ESP_LOGE(TAG, "THERMAL SHUTDOWN: temp=%.1f°C, current=%.0fmA",
                     r->estimated_temp_c, r->current_ma);
        } else if (state == THERMAL_WARNING) {
            ESP_LOGW(TAG, "Thermal warning: temp=%.1f°C", r->estimated_temp_c);
        } else {
            ESP_LOGI(TAG, "Thermal state normal");
        }
        if (user_callback) user_callback(state, r);
    }

    r->state = state;
}

void thermal_monitor_task(void *params)
{
    uint16_t raw;
    thermal_reading_t reading;

    while (1) {
        memset(&reading, 0, sizeof(reading));

        // Read bus voltage (bits 15-3 are voltage, LSB = 4mV)
        if (ina219_read_reg(INA219_REG_BUS_V, &raw) == ESP_OK) {
            reading.bus_voltage_v = ((raw >> 3) * 4) / 1000.0f;
        }

        // Read shunt voltage (LSB = 10µV)
        if (ina219_read_reg(INA219_REG_SHUNT_V, &raw) == ESP_OK) {
            reading.shunt_voltage_mv = (int16_t)raw * 0.01f;
        }

        // Read current (LSB depends on calibration)
        if (ina219_read_reg(INA219_REG_CURRENT, &raw) == ESP_OK) {
            reading.current_ma = (int16_t)raw * 0.1f;
        }

        // Read power
        if (ina219_read_reg(INA219_REG_POWER, &raw) == ESP_OK) {
            reading.power_mw = raw * 2.0f;
        }

        update_thermal_state(&reading);
        last_reading = reading;

        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
