// SPDX-License-Identifier: Apache-2.0
#include "battery.h"
#include "adc_manager.h"
#include "safety.h"
#include "pin_definitions.h"
#include "robot_params.h"

#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "battery";

static portMUX_TYPE batt_spinlock = portMUX_INITIALIZER_UNLOCKED;
static adc_cali_handle_t cali_handle;
static float voltage_avg = 0.0f;
static float readings[BATT_ADC_SAMPLES];
static int reading_idx = 0;
static bool initialized = false;

esp_err_t battery_init(void)
{
    adc_oneshot_unit_handle_t adc_handle = adc_manager_get_handle();

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = BATT_ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_12,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc_handle, BATT_ADC_CHANNEL, &chan_cfg));
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc_handle, BATT_PACK2_ADC_CHANNEL, &chan_cfg));

    adc_cali_curve_fitting_config_t cali_cfg = {
        .unit_id = ADC_UNIT_1,
        .atten = BATT_ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_12,
    };
    adc_cali_create_scheme_curve_fitting(&cali_cfg, &cali_handle);

    for (int i = 0; i < BATT_ADC_SAMPLES; i++) {
        readings[i] = BATT_CELLS_SERIES * BATT_CELL_NOMINAL_V;
    }
    voltage_avg = BATT_CELLS_SERIES * BATT_CELL_NOMINAL_V;
    initialized = true;

    ESP_LOGI(TAG, "Battery ADC initialized (%dS, divider=%.1f)",
             BATT_CELLS_SERIES, BATT_VOLTAGE_DIVIDER);
    return ESP_OK;
}

float battery_read_voltage(void)
{
    if (!initialized) return 0.0f;

    int raw = 0;
    adc_oneshot_read(adc_manager_get_handle(), BATT_ADC_CHANNEL, &raw);

    int mv = 0;
    adc_cali_raw_to_voltage(cali_handle, raw, &mv);

    float voltage = ((float)mv / 1000.0f) * BATT_VOLTAGE_DIVIDER;

    portENTER_CRITICAL(&batt_spinlock);
    readings[reading_idx] = voltage;
    reading_idx = (reading_idx + 1) % BATT_ADC_SAMPLES;

    float sum = 0.0f;
    for (int i = 0; i < BATT_ADC_SAMPLES; i++) sum += readings[i];
    voltage_avg = sum / BATT_ADC_SAMPLES;
    portEXIT_CRITICAL(&batt_spinlock);

    return voltage_avg;
}

uint8_t battery_get_percentage(void)
{
    portENTER_CRITICAL(&batt_spinlock);
    float v = voltage_avg;
    portEXIT_CRITICAL(&batt_spinlock);
    float cell_v = v / BATT_CELLS_SERIES;
    if (cell_v >= BATT_CELL_FULL_V) return 100;
    if (cell_v <= BATT_CELL_CRITICAL_V) return 0;

    float range = BATT_CELL_FULL_V - BATT_CELL_CRITICAL_V;
    return (uint8_t)(((cell_v - BATT_CELL_CRITICAL_V) / range) * 100.0f);
}

battery_state_t battery_get_state(void)
{
    portENTER_CRITICAL(&batt_spinlock);
    float v = voltage_avg;
    portEXIT_CRITICAL(&batt_spinlock);
    float cell_v = v / BATT_CELLS_SERIES;
    if (cell_v <= BATT_CELL_CRITICAL_V) return BATT_CRITICAL;
    if (cell_v <= BATT_CELL_LOW_V) return BATT_LOW;
    return BATT_OK;
}

void battery_task(void *params)
{
    const TickType_t period = pdMS_TO_TICKS(1000 / BATTERY_PUBLISH_HZ);

    while (1) {
        battery_read_voltage();

        if (battery_get_state() == BATT_CRITICAL) {
            ESP_LOGE(TAG, "CRITICAL: Battery %.2fV - triggering safety stop", voltage_avg);
            safety_trigger_estop();
        }

        vTaskDelay(period);
    }
}

// --- Multi-pack extension ---

static float s_pack2_voltage = 0.0f;

static float battery_pack2_read_voltage_raw(void)
{
    int raw = 0;
    adc_oneshot_read(adc_manager_get_handle(), BATT_PACK2_ADC_CHANNEL, &raw);
    int mv = 0;
    adc_cali_raw_to_voltage(cali_handle, raw, &mv);
    return ((float)mv / 1000.0f) * BATT_VOLTAGE_DIVIDER;
}

bool battery_pack_is_present(uint8_t pack_idx)
{
    if (pack_idx == 0) return initialized;
    if (pack_idx == 1) {
        float v_raw = battery_pack2_read_voltage_raw();
        return (v_raw * 1000.0f) > BATT_PACK_PRESENT_THRESHOLD_MV;
    }
    return false;
}

float battery_pack_get_voltage(uint8_t pack_idx)
{
    if (pack_idx == 0) {
        portENTER_CRITICAL(&batt_spinlock);
        float v = voltage_avg;
        portEXIT_CRITICAL(&batt_spinlock);
        return v;
    }
    if (pack_idx == 1) {
        if (!battery_pack_is_present(1)) return 0.0f;
        s_pack2_voltage = battery_pack2_read_voltage_raw();
        return s_pack2_voltage;
    }
    return 0.0f;
}

static uint8_t voltage_to_percentage(float pack_voltage)
{
    float cell_v = pack_voltage / BATT_CELLS_SERIES;
    if (cell_v >= BATT_CELL_FULL_V) return 100;
    if (cell_v <= BATT_CELL_CRITICAL_V) return 0;
    float range = BATT_CELL_FULL_V - BATT_CELL_CRITICAL_V;
    return (uint8_t)(((cell_v - BATT_CELL_CRITICAL_V) / range) * 100.0f);
}

static battery_state_t voltage_to_state(float pack_voltage)
{
    float cell_v = pack_voltage / BATT_CELLS_SERIES;
    if (cell_v <= BATT_CELL_CRITICAL_V) return BATT_CRITICAL;
    if (cell_v <= BATT_CELL_LOW_V) return BATT_LOW;
    return BATT_OK;
}

battery_system_state_t battery_get_system_state(void)
{
    battery_system_state_t sys = {0};

    for (uint8_t i = 0; i < BATT_PACKS_MAX; i++) {
        sys.packs[i].present = battery_pack_is_present(i);
        if (sys.packs[i].present) {
            sys.packs[i].voltage = battery_pack_get_voltage(i);
            sys.packs[i].percentage = voltage_to_percentage(sys.packs[i].voltage);
            sys.packs[i].state = voltage_to_state(sys.packs[i].voltage);
            sys.num_packs_present++;
        }
    }

    if (sys.num_packs_present == 0) {
        sys.total_percentage = 0;
        sys.worst_state = BATT_CRITICAL;
        return sys;
    }

    uint16_t sum_pct = 0;
    sys.worst_state = BATT_OK;
    for (uint8_t i = 0; i < BATT_PACKS_MAX; i++) {
        if (!sys.packs[i].present) continue;
        sum_pct += sys.packs[i].percentage;
        if (sys.packs[i].state > sys.worst_state) {
            sys.worst_state = sys.packs[i].state;
        }
    }
    sys.total_percentage = (uint8_t)(sum_pct / sys.num_packs_present);

    return sys;
}
