// SPDX-License-Identifier: Apache-2.0
#include "battery.h"
#include "adc_manager.h"
#include "safety.h"
#include "pin_definitions.h"
#include "robot_params.h"
#include "payload_hotplug.h"

#ifdef CONFIG_ROBOT_DISPLAY_ENABLED
#include "display.h"
#endif

#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "battery";

static portMUX_TYPE batt_spinlock = portMUX_INITIALIZER_UNLOCKED;
static adc_cali_handle_t cali_handle;
static float voltage_avg = 0.0f;
static float readings[BATT_ADC_SAMPLES];
static int reading_idx = 0;
static bool initialized = false;

#define BATT_CRITICAL_SHUTDOWN_MS  5000
#define BATT_RECOVERY_COUNT       10
static uint32_t critical_start_tick = 0;
static bool shutdown_initiated = false;
static bool critical_estop_triggered = false;
static uint8_t recovery_counter = 0;

esp_err_t battery_init(void)
{
    adc_oneshot_unit_handle_t adc_handle = adc_manager_get_handle();

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = BATT_ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_12,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc_handle, BATT_ADC_CHANNEL, &chan_cfg));
#ifdef CONFIG_ROBOT_DUAL_BATTERY
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc_handle, BATT_PACK2_ADC_CHANNEL, &chan_cfg));
#endif

    adc_cali_curve_fitting_config_t cali_cfg = {
        .unit_id = ADC_UNIT_1,
        .atten = BATT_ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_12,
    };
    adc_cali_create_scheme_curve_fitting(&cali_cfg, &cali_handle);

    // Prefill moving average with first real ADC reading (not nominal)
    int raw_init = 0;
    adc_manager_read(BATT_ADC_CHANNEL, &raw_init);
    int mv_init = 0;
    adc_cali_raw_to_voltage(cali_handle, raw_init, &mv_init);
    float first_reading = ((float)mv_init / 1000.0f) * BATT_VOLTAGE_DIVIDER;
    if (first_reading < 1.0f) {
        first_reading = BATT_CELLS_SERIES * BATT_CELL_NOMINAL_V;
    }

    for (int i = 0; i < BATT_ADC_SAMPLES; i++) {
        readings[i] = first_reading;
    }
    voltage_avg = first_reading;
    initialized = true;

    ESP_LOGI(TAG, "Battery ADC initialized (%dS, divider=%.1f)",
             BATT_CELLS_SERIES, BATT_VOLTAGE_DIVIDER);
    return ESP_OK;
}

float battery_read_voltage(void)
{
    if (!initialized) return 0.0f;

    int raw = 0;
    if (adc_manager_read(BATT_ADC_CHANNEL, &raw) != ESP_OK) {
        portENTER_CRITICAL(&batt_spinlock);
        float v = voltage_avg;
        portEXIT_CRITICAL(&batt_spinlock);
        return v;
    }

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
            recovery_counter = 0;
            if (critical_start_tick == 0) {
                critical_start_tick = xTaskGetTickCount();
            }

            uint32_t elapsed = (xTaskGetTickCount() - critical_start_tick) * portTICK_PERIOD_MS;

            if (!critical_estop_triggered) {
                critical_estop_triggered = true;
                ESP_LOGE(TAG, "CRITICAL: Battery %.2fV - triggering safety stop", voltage_avg);
#ifdef CONFIG_ROBOT_DISPLAY_ENABLED
                display_log_fault(FAULT_SRC_BATTERY, 1, "BATT CRITICAL");
#endif
                safety_trigger_estop();
            }

            if (elapsed >= BATT_CRITICAL_SHUTDOWN_MS && !shutdown_initiated) {
                shutdown_initiated = true;
                ESP_LOGE(TAG, "CRITICAL sustained %lums - initiating low-power shutdown",
                         (unsigned long)elapsed);
                payload_power_off();
#ifdef CONFIG_PI5_POWER_ENABLED
                gpio_set_level(PI5_RELAY_GPIO, 0);
#endif
                esp_wifi_stop();
            }
        } else {
            if (++recovery_counter >= BATT_RECOVERY_COUNT) {
                critical_start_tick = 0;
                shutdown_initiated = false;
                critical_estop_triggered = false;
                recovery_counter = 0;
            }
        }

        vTaskDelay(period);
    }
}

// --- Multi-pack extension ---

#ifdef CONFIG_ROBOT_DUAL_BATTERY
static float s_pack2_voltage = 0.0f;

static float battery_pack2_read_voltage_raw(void)
{
    int raw = 0;
    adc_manager_read(BATT_PACK2_ADC_CHANNEL, &raw);
    int mv = 0;
    adc_cali_raw_to_voltage(cali_handle, raw, &mv);
    return ((float)mv / 1000.0f) * BATT_VOLTAGE_DIVIDER;
}
#endif

bool battery_pack_is_present(uint8_t pack_idx)
{
    if (pack_idx == 0) return initialized;
#ifdef CONFIG_ROBOT_DUAL_BATTERY
    if (pack_idx == 1) {
        float v_raw = battery_pack2_read_voltage_raw();
        return (v_raw * 1000.0f) > BATT_PACK_PRESENT_THRESHOLD_MV;
    }
#endif
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
#ifdef CONFIG_ROBOT_DUAL_BATTERY
    if (pack_idx == 1) {
        if (!battery_pack_is_present(1)) return 0.0f;
        s_pack2_voltage = battery_pack2_read_voltage_raw();
        return s_pack2_voltage;
    }
#endif
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
