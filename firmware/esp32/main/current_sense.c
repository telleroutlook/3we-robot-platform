// SPDX-License-Identifier: Apache-2.0
#include "current_sense.h"
#include "pin_definitions.h"
#include "robot_params.h"
#include "safety.h"
#include "adc_manager.h"

#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"

#include <math.h>
#include <string.h>

static const char *TAG = "current_sense";

static portMUX_TYPE cs_spinlock = portMUX_INITIALIZER_UNLOCKED;

#define ACS712_SENSITIVITY_MV_PER_A  185.0f  // ACS712-05B: 185 mV/A
#define ACS712_ZERO_CURRENT_MV       2500.0f // 2.5V at 0A (5V supply / 2)
#define SOFT_LIMIT_MA                3000.0f
#define HARD_LIMIT_MA                8000.0f
#define SOFT_LIMIT_DURATION_MS       100
#define HARD_LIMIT_DURATION_MS       20

static const int adc_channels[CURRENT_SENSE_CHANNELS] = {
    ADC_CHANNEL_4, ADC_CHANNEL_5, ADC_CHANNEL_6, ADC_CHANNEL_7,
};

static adc_cali_handle_t cali_handle;
static current_reading_t last_reading;
static current_state_t channel_state[CURRENT_SENSE_CHANNELS];
static int64_t overcurrent_start_us[CURRENT_SENSE_CHANNELS];

esp_err_t current_sense_init(void)
{
    adc_oneshot_unit_handle_t adc_handle = adc_manager_get_handle();
    if (!adc_handle) {
        ESP_LOGE(TAG, "ADC manager not initialized");
        return ESP_ERR_INVALID_STATE;
    }

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = CURRENT_SENSE_ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_12,
    };

    for (int i = 0; i < CURRENT_SENSE_CHANNELS; i++) {
        ESP_ERROR_CHECK(adc_oneshot_config_channel(adc_handle, adc_channels[i], &chan_cfg));
        channel_state[i] = CURRENT_OK;
        overcurrent_start_us[i] = 0;
    }

    adc_cali_curve_fitting_config_t cali_cfg = {
        .unit_id = ADC_UNIT_1,
        .atten = CURRENT_SENSE_ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_12,
    };
    ESP_ERROR_CHECK(adc_cali_create_scheme_curve_fitting(&cali_cfg, &cali_handle));

    memset(&last_reading, 0, sizeof(last_reading));
    ESP_LOGI(TAG, "ACS712 current sensing initialized (%d channels)", CURRENT_SENSE_CHANNELS);
    return ESP_OK;
}

esp_err_t current_sense_read(current_reading_t *reading)
{
    if (!reading) return ESP_ERR_INVALID_ARG;
    portENTER_CRITICAL(&cs_spinlock);
    *reading = last_reading;
    portEXIT_CRITICAL(&cs_spinlock);
    return ESP_OK;
}

current_state_t current_sense_get_state(int channel)
{
    if (channel < 0 || channel >= CURRENT_SENSE_CHANNELS) return CURRENT_OK;
    portENTER_CRITICAL(&cs_spinlock);
    current_state_t s = channel_state[channel];
    portEXIT_CRITICAL(&cs_spinlock);
    return s;
}

void current_sense_update(void)
{
    adc_oneshot_unit_handle_t adc_handle = adc_manager_get_handle();
    if (!adc_handle) return;

    int64_t now_us = esp_timer_get_time();
    float total = 0.0f;
    uint32_t flags = 0;
    current_reading_t reading;
    current_state_t new_states[CURRENT_SENSE_CHANNELS];

    for (int i = 0; i < CURRENT_SENSE_CHANNELS; i++) {
        new_states[i] = channel_state[i];

        int raw = 0;
        adc_manager_read(adc_channels[i], &raw);

        int voltage_mv = 0;
        adc_cali_raw_to_voltage(cali_handle, raw, &voltage_mv);

        float current_ma = ((float)voltage_mv - ACS712_ZERO_CURRENT_MV) / ACS712_SENSITIVITY_MV_PER_A * 1000.0f;
        current_ma = fabsf(current_ma);

        reading.current_ma[i] = current_ma;
        total += current_ma;

        if (current_ma >= HARD_LIMIT_MA) {
            if (overcurrent_start_us[i] == 0) {
                overcurrent_start_us[i] = now_us;
            } else if ((now_us - overcurrent_start_us[i]) >= (HARD_LIMIT_DURATION_MS * 1000)) {
                new_states[i] = CURRENT_HARD_LIMIT;
                flags |= (1u << i);
                safety_trigger_estop();
                ESP_LOGE(TAG, "Motor %d HARD overcurrent %.0f mA — E-STOP", i, current_ma);
            }
        } else if (current_ma >= SOFT_LIMIT_MA) {
            if (overcurrent_start_us[i] == 0) {
                overcurrent_start_us[i] = now_us;
            } else if ((now_us - overcurrent_start_us[i]) >= (SOFT_LIMIT_DURATION_MS * 1000)) {
                new_states[i] = CURRENT_SOFT_LIMIT;
                flags |= (1u << i);
                ESP_LOGW(TAG, "Motor %d soft overcurrent %.0f mA — limiting", i, current_ma);
            }
        } else {
            overcurrent_start_us[i] = 0;
            new_states[i] = CURRENT_OK;
        }
    }

    reading.total_current_ma = total;
    reading.overcurrent_flags = flags;

    portENTER_CRITICAL(&cs_spinlock);
    last_reading = reading;
    for (int i = 0; i < CURRENT_SENSE_CHANNELS; i++) {
        channel_state[i] = new_states[i];
    }
    portEXIT_CRITICAL(&cs_spinlock);
}
