// SPDX-License-Identifier: Apache-2.0
#include "payload_power.h"
#include "i2c_bus.h"
#include "esp_log.h"
#include "esp_timer.h"

static const char *TAG = "payload_power";

static power_rail_config_t s_configs[POWER_RAIL_MAX];
static power_rail_status_t s_status[POWER_RAIL_MAX];
static int s_num_rails = 0;
static bool s_initialized = false;

esp_err_t payload_power_init(const power_rail_config_t *configs, int num_rails)
{
    if (configs == NULL || num_rails <= 0 || num_rails > POWER_RAIL_MAX) {
        return ESP_ERR_INVALID_ARG;
    }

    for (int i = 0; i < num_rails; i++) {
        s_configs[i] = configs[i];
        s_status[i].state = POWER_RAIL_OFF;
        s_status[i].current_ma = 0;
        s_status[i].state_change_time_us = esp_timer_get_time();
    }

    s_num_rails = num_rails;
    s_initialized = true;

    ESP_LOGI(TAG, "Power rail controller initialized (%d rails)", num_rails);
    return ESP_OK;
}

esp_err_t payload_power_enable_rail(int rail_index)
{
    if (!s_initialized || rail_index < 0 || rail_index >= s_num_rails) {
        return ESP_ERR_INVALID_ARG;
    }

    const power_rail_config_t *cfg = &s_configs[rail_index];
    if (!cfg->enabled) {
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t err = mcp23017_write_bit(cfg->mcp23017_addr, cfg->mcp23017_reg,
                                        cfg->mcp23017_bit, true);
    if (err != ESP_OK) {
        s_status[rail_index].state = POWER_RAIL_FAULT;
        s_status[rail_index].state_change_time_us = esp_timer_get_time();
        ESP_LOGE(TAG, "Failed to enable %s rail: 0x%x", cfg->name, err);
        return err;
    }

    s_status[rail_index].state = POWER_RAIL_RAMPING;
    s_status[rail_index].state_change_time_us = esp_timer_get_time();
    ESP_LOGI(TAG, "%s rail enabled (ramping, %dms soft-start)",
             cfg->name, cfg->soft_start_delay_ms);
    return ESP_OK;
}

esp_err_t payload_power_disable_rail(int rail_index)
{
    if (!s_initialized || rail_index < 0 || rail_index >= s_num_rails) {
        return ESP_ERR_INVALID_ARG;
    }

    const power_rail_config_t *cfg = &s_configs[rail_index];

    esp_err_t err = mcp23017_write_bit(cfg->mcp23017_addr, cfg->mcp23017_reg,
                                        cfg->mcp23017_bit, false);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to disable %s rail: 0x%x", cfg->name, err);
        return err;
    }

    s_status[rail_index].state = POWER_RAIL_OFF;
    s_status[rail_index].state_change_time_us = esp_timer_get_time();
    return ESP_OK;
}

esp_err_t payload_power_disable_all(void)
{
    if (!s_initialized) return ESP_ERR_INVALID_STATE;

    esp_err_t first_err = ESP_OK;
    for (int i = s_num_rails - 1; i >= 0; i--) {
        esp_err_t err = payload_power_disable_rail(i);
        if (err != ESP_OK && first_err == ESP_OK) first_err = err;
    }

    ESP_LOGI(TAG, "All power rails disabled");
    return first_err;
}

power_rail_state_t payload_power_get_state(int rail_index)
{
    if (!s_initialized || rail_index < 0 || rail_index >= s_num_rails) {
        return POWER_RAIL_OFF;
    }

    power_rail_status_t *st = &s_status[rail_index];

    if (st->state == POWER_RAIL_RAMPING) {
        int64_t elapsed = esp_timer_get_time() - st->state_change_time_us;
        int64_t required = (int64_t)s_configs[rail_index].soft_start_delay_ms * 1000;
        if (elapsed >= required) {
            st->state = POWER_RAIL_ON;
            st->state_change_time_us = esp_timer_get_time();
        }
    }

    return st->state;
}

esp_err_t payload_power_get_status(int rail_index, power_rail_status_t *out)
{
    if (out == NULL || !s_initialized || rail_index < 0 || rail_index >= s_num_rails) {
        return ESP_ERR_INVALID_ARG;
    }

    payload_power_get_state(rail_index);
    *out = s_status[rail_index];
    return ESP_OK;
}

int payload_power_get_rail_count(void)
{
    return s_num_rails;
}
