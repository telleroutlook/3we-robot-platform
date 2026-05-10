// SPDX-License-Identifier: Apache-2.0
#include "charging_detect.h"
#include "adc_manager.h"
#include "pin_definitions.h"

#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_log.h"

static const char *TAG = "charging";

static adc_cali_handle_t s_cali_handle = NULL;
static int s_last_voltage_mv = 0;
static bool s_initialized = false;

esp_err_t charging_detect_init(void)
{
    adc_oneshot_unit_handle_t handle = adc_manager_get_handle();
    if (handle == NULL) return ESP_ERR_INVALID_STATE;

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = CHARGE_ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_12,
    };
    esp_err_t err = adc_oneshot_config_channel(handle, CHARGE_ADC_CHANNEL, &chan_cfg);
    if (err != ESP_OK) return err;

    adc_cali_curve_fitting_config_t cali_cfg = {
        .unit_id = ADC_UNIT_1,
        .atten = CHARGE_ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_12,
    };
    err = adc_cali_create_scheme_curve_fitting(&cali_cfg, &s_cali_handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "ADC calibration scheme not available - using raw values");
        s_cali_handle = NULL;
    }

    s_initialized = true;
    ESP_LOGI(TAG, "Charging detect initialized (threshold=%dmV)", CHARGE_CONTACT_THRESHOLD_MV);
    return ESP_OK;
}

int charging_detect_get_voltage_mv(void)
{
    if (!s_initialized) return 0;

    int raw = 0;
    esp_err_t err = adc_oneshot_read(adc_manager_get_handle(), CHARGE_ADC_CHANNEL, &raw);
    if (err != ESP_OK) return s_last_voltage_mv;

    if (s_cali_handle != NULL) {
        int mv = 0;
        if (adc_cali_raw_to_voltage(s_cali_handle, raw, &mv) == ESP_OK) {
            s_last_voltage_mv = mv;
            return mv;
        }
    }

    s_last_voltage_mv = raw * 3300 / 4095;
    return s_last_voltage_mv;
}

bool charging_detect_is_connected(void)
{
    return charging_detect_get_voltage_mv() >= CHARGE_CONTACT_THRESHOLD_MV;
}
