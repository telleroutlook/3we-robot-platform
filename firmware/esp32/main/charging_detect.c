// SPDX-License-Identifier: Apache-2.0
#include "charging_detect.h"
#include "adc_manager.h"
#include "pin_definitions.h"

#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_log.h"

#ifdef CONFIG_ROBOT_DOCKING_DIGITAL_DETECT
#include "driver/gpio.h"
#endif

static const char *TAG = "charging";

static adc_cali_handle_t s_cali_handle = NULL;
static int s_last_voltage_mv = 0;
static bool s_initialized = false;
static bool s_connected = false;

#ifdef CONFIG_ROBOT_DOCKING_DIGITAL_DETECT
static bool digital_detect_asserted(void)
{
    return gpio_get_level(CHARGE_DIGITAL_DETECT_GPIO) == 0;
}
#endif

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

#ifdef CONFIG_ROBOT_DOCKING_DIGITAL_DETECT
    gpio_config_t io_cfg = {
        .pin_bit_mask = (1ULL << CHARGE_DIGITAL_DETECT_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    err = gpio_config(&io_cfg);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Digital detect GPIO config failed: 0x%x", err);
    }
#endif

    s_initialized = true;
    s_connected = false;
    ESP_LOGI(TAG, "Charging detect initialized (threshold=%dmV)", CHARGE_CONTACT_THRESHOLD_MV);
    return ESP_OK;
}

int charging_detect_get_voltage_mv(void)
{
    if (!s_initialized) return 0;

    int raw = 0;
    esp_err_t err = adc_manager_read(CHARGE_ADC_CHANNEL, &raw);
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
    int mv = charging_detect_get_voltage_mv();
    if (s_connected) {
        if (mv < CHARGE_CONTACT_RELEASE_MV) s_connected = false;
    } else {
        if (mv >= CHARGE_CONTACT_THRESHOLD_MV) s_connected = true;
    }

    bool analog = s_connected;

#ifdef CONFIG_ROBOT_DOCKING_DIGITAL_DETECT
    return analog || digital_detect_asserted();
#else
    return analog;
#endif
}

charge_detect_method_t charging_detect_get_method(void)
{
    bool analog = charging_detect_get_voltage_mv() >= CHARGE_CONTACT_THRESHOLD_MV;

#ifdef CONFIG_ROBOT_DOCKING_DIGITAL_DETECT
    bool digital = digital_detect_asserted();
    if (analog && digital) return CHARGE_DETECT_BOTH;
    if (analog) return CHARGE_DETECT_ANALOG;
    if (digital) return CHARGE_DETECT_DIGITAL;
#else
    if (analog) return CHARGE_DETECT_ANALOG;
#endif

    return CHARGE_DETECT_NONE;
}
