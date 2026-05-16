// SPDX-License-Identifier: Apache-2.0
#include "thermal_monitor.h"
#include "i2c_bus.h"
#include "motor_control.h"
#include "safety.h"
#include "pin_definitions.h"

#ifdef CONFIG_THERMAL_NTC_ENABLED
#include "adc_manager.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#endif

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

// Calibration for 0.02 ohm shunt resistor, 16A max (PGA=÷8, ±320mV)
#define INA219_CALIBRATION  20480
#define SHUNT_RESISTANCE    0.02f

// Thermal model: estimate temperature from power dissipation
// Rth_ja ~= 40°C/W for typical motor driver package + PCB
#define THERMAL_RESISTANCE  40.0f
#define AMBIENT_TEMP_C      25.0f

// NTC thermistor parameters (10K B3950)
#ifdef CONFIG_THERMAL_NTC_ENABLED
#if defined(CONFIG_CURRENT_SENSE_ENABLED)
#error "NTC (ADC_CH5) and current sense FR (ADC_CH5) share GPIO 6 — cannot coexist"
#endif
#define NTC_R25             10000.0f // Resistance at 25°C
#define NTC_BETA            3950.0f  // B-value
#define NTC_SERIES_R        10000.0f // Series resistor in voltage divider
#define NTC_ADC_CHANNEL     ADC_CHANNEL_5  // Placeholder — confirm with PCB
#define NTC_ADC_ATTEN       ADC_ATTEN_DB_11
static adc_cali_handle_t ntc_cali_handle;
#endif

// Escalate to THERMAL_WARNING if I2C fails this many consecutive cycles
#define I2C_FAILURE_ESCALATION_COUNT 6
#define I2C_RECOVERY_ATTEMPT_COUNT   3

static thermal_state_t state = THERMAL_OK;
static thermal_callback_t user_callback = NULL;
static thermal_reading_t last_reading;
static uint8_t i2c_consecutive_failures;
static portMUX_TYPE thermal_spinlock = portMUX_INITIALIZER_UNLOCKED;

static esp_err_t ina219_write_reg(uint8_t reg, uint16_t value)
{
    uint8_t buf[3] = { reg, (value >> 8) & 0xFF, value & 0xFF };
    if (!i2c_bus_lock()) return ESP_ERR_TIMEOUT;
    esp_err_t err = i2c_master_write_to_device(I2C_NUM_0, INA219_ADDR, buf, 3, pdMS_TO_TICKS(50));
    i2c_bus_unlock();
    return err;
}

static esp_err_t ina219_read_reg(uint8_t reg, uint16_t *value)
{
    uint8_t data[2];
    if (!i2c_bus_lock()) return ESP_ERR_TIMEOUT;
    esp_err_t err = i2c_master_write_read_device(I2C_NUM_0, INA219_ADDR,
                                                  &reg, 1, data, 2, pdMS_TO_TICKS(50));
    i2c_bus_unlock();
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

#ifdef CONFIG_THERMAL_NTC_ENABLED
    adc_oneshot_unit_handle_t adc_handle = adc_manager_get_handle();
    if (adc_handle) {
        adc_oneshot_chan_cfg_t chan_cfg = {
            .atten = NTC_ADC_ATTEN,
            .bitwidth = ADC_BITWIDTH_12,
        };
        adc_oneshot_config_channel(adc_handle, NTC_ADC_CHANNEL, &chan_cfg);

        adc_cali_curve_fitting_config_t cali_cfg = {
            .unit_id = ADC_UNIT_1,
            .atten = NTC_ADC_ATTEN,
            .bitwidth = ADC_BITWIDTH_12,
        };
        adc_cali_create_scheme_curve_fitting(&cali_cfg, &ntc_cali_handle);
        ESP_LOGI(TAG, "NTC thermistor ADC initialized");
    }
#endif

    ESP_LOGI(TAG, "Thermal monitor initialized (INA219 at 0x%02X)", INA219_ADDR);
    return ESP_OK;
}

thermal_state_t thermal_get_state(void)
{
    portENTER_CRITICAL(&thermal_spinlock);
    thermal_state_t s = state;
    portEXIT_CRITICAL(&thermal_spinlock);
    return s;
}

esp_err_t thermal_get_reading(thermal_reading_t *reading)
{
    if (!reading) return ESP_ERR_INVALID_ARG;
    portENTER_CRITICAL(&thermal_spinlock);
    *reading = last_reading;
    portEXIT_CRITICAL(&thermal_spinlock);
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

    // Use the higher of INA219 estimate and NTC direct measurement
    r->effective_temp_c = fmaxf(r->estimated_temp_c, r->ntc_temp_c);

    thermal_state_t new_state;
    if (r->effective_temp_c >= THERMAL_SHUTDOWN_TEMP_C) {
        new_state = THERMAL_SHUTDOWN;
    } else if (r->effective_temp_c >= THERMAL_CRITICAL_TEMP_C ||
        fabsf(r->current_ma) > (THERMAL_CURRENT_MAX_A * 1000.0f)) {
        new_state = THERMAL_CRITICAL;
    } else if (r->effective_temp_c >= THERMAL_WARNING_TEMP_C) {
        new_state = THERMAL_WARNING;
    } else if (state == THERMAL_WARNING &&
               r->effective_temp_c > (THERMAL_WARNING_TEMP_C - THERMAL_HYSTERESIS_C)) {
        new_state = THERMAL_WARNING;
    } else {
        new_state = THERMAL_OK;
    }

    if (new_state != state) {
        portENTER_CRITICAL(&thermal_spinlock);
        state = new_state;
        portEXIT_CRITICAL(&thermal_spinlock);
        if (state == THERMAL_SHUTDOWN) {
            safety_trigger_estop();
            ESP_LOGE(TAG, "THERMAL SHUTDOWN: temp=%.1f°C — system must power off",
                     r->effective_temp_c);
        } else if (state == THERMAL_CRITICAL) {
            safety_trigger_estop();
            ESP_LOGE(TAG, "THERMAL CRITICAL: temp=%.1f°C, current=%.0fmA — E-stop triggered",
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

        uint8_t read_failures = 0;

        if (ina219_read_reg(INA219_REG_BUS_V, &raw) == ESP_OK) {
            reading.bus_voltage_v = ((raw >> 3) * 4) / 1000.0f;
        } else {
            read_failures++;
        }

        if (ina219_read_reg(INA219_REG_SHUNT_V, &raw) == ESP_OK) {
            reading.shunt_voltage_mv = (int16_t)raw * 0.01f;
        } else {
            read_failures++;
        }

        if (ina219_read_reg(INA219_REG_CURRENT, &raw) == ESP_OK) {
            reading.current_ma = (int16_t)raw * 0.1f;
        } else {
            read_failures++;
        }

        if (ina219_read_reg(INA219_REG_POWER, &raw) == ESP_OK) {
            reading.power_mw = raw * 2.0f;
        } else {
            read_failures++;
        }

        if (read_failures > 0) {
            if (i2c_consecutive_failures < UINT8_MAX) {
                i2c_consecutive_failures++;
            }
            if (i2c_consecutive_failures == I2C_RECOVERY_ATTEMPT_COUNT) {
                ESP_LOGW(TAG, "I2C failures (%u) — attempting bus recovery",
                         i2c_consecutive_failures);
                if (i2c_bus_recover() == ESP_OK) {
                    vTaskDelay(pdMS_TO_TICKS(10));
                    ina219_write_reg(INA219_REG_CONFIG, 0x8000);
                    vTaskDelay(pdMS_TO_TICKS(5));
                    ina219_write_reg(INA219_REG_CALIB, INA219_CALIBRATION);
                    ina219_write_reg(INA219_REG_CONFIG, INA219_CONFIG);
                }
            }
            if (i2c_consecutive_failures >= I2C_FAILURE_ESCALATION_COUNT &&
                state < THERMAL_WARNING) {
                ESP_LOGW(TAG, "I2C sensor failure (%u consecutive) — escalating to THERMAL_WARNING",
                         i2c_consecutive_failures);
                portENTER_CRITICAL(&thermal_spinlock);
                state = THERMAL_WARNING;
                portEXIT_CRITICAL(&thermal_spinlock);
                if (user_callback) user_callback(state, &reading);
            }
        } else {
            i2c_consecutive_failures = 0;
        }

#ifdef CONFIG_THERMAL_NTC_ENABLED
        // Read NTC thermistor via ADC
        adc_oneshot_unit_handle_t adc_handle = adc_manager_get_handle();
        if (adc_handle && ntc_cali_handle) {
            int adc_raw = 0;
            if (adc_oneshot_read(adc_handle, NTC_ADC_CHANNEL, &adc_raw) == ESP_OK) {
                int voltage_mv = 0;
                adc_cali_raw_to_voltage(ntc_cali_handle, adc_raw, &voltage_mv);
                float v = (float)voltage_mv / 1000.0f;
                if (v > 0.01f && v < 3.29f) {
                    float resistance = NTC_SERIES_R * v / (3.3f - v);
                    float log_r = logf(resistance / NTC_R25);
                    float inv_t = (1.0f / 298.15f) + (1.0f / NTC_BETA) * log_r;
                    reading.ntc_temp_c = (1.0f / inv_t) - 273.15f;
                }
            }
        }
#endif

        update_thermal_state(&reading);
        portENTER_CRITICAL(&thermal_spinlock);
        last_reading = reading;
        portEXIT_CRITICAL(&thermal_spinlock);

        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
