// SPDX-License-Identifier: Apache-2.0
#include "heartbeat_monitor.h"
#include "pin_definitions.h"

#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "heartbeat";

static portMUX_TYPE hb_spinlock = portMUX_INITIALIZER_UNLOCKED;
static volatile int64_t s_last_heartbeat_us = 0;
static volatile int64_t s_init_time_us = 0;
static volatile heartbeat_state_t s_state = HB_STATE_WAITING;
static uint8_t s_reset_count = 0;
static int64_t s_first_reset_us = 0;

esp_err_t heartbeat_monitor_init(void)
{
#ifndef CONFIG_PI5_POWER_ENABLED
    ESP_LOGI(TAG, "Pi5 power management disabled (Basic SKU)");
    s_state = HB_STATE_SAFE_MODE;
    return ESP_OK;
#else
    gpio_config_t io_cfg = {
        .pin_bit_mask = (1ULL << PI5_RELAY_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&io_cfg);
    if (err != ESP_OK) return err;

    gpio_set_level(PI5_RELAY_GPIO, 1); // Relay ON (Pi5 powered)
    s_last_heartbeat_us = esp_timer_get_time();
    s_init_time_us = s_last_heartbeat_us;
    s_state = HB_STATE_WAITING;
    s_reset_count = 0;

    ESP_LOGI(TAG, "Heartbeat monitor initialized (timeout=%dms, max_resets=%d)",
             HEARTBEAT_TIMEOUT_MS, HEARTBEAT_MAX_RESETS);
    return ESP_OK;
#endif // CONFIG_PI5_POWER_ENABLED
}

void heartbeat_feed(void)
{
    portENTER_CRITICAL(&hb_spinlock);
    s_last_heartbeat_us = esp_timer_get_time();
    if (s_state == HB_STATE_TIMEOUT) {
        s_state = HB_STATE_ACTIVE;
    } else if (s_state == HB_STATE_WAITING) {
        int64_t since_init = s_last_heartbeat_us - s_init_time_us;
        if (since_init >= (int64_t)HEARTBEAT_BOOT_GRACE_MS * 1000) {
            s_state = HB_STATE_ACTIVE;
        }
    }
    portEXIT_CRITICAL(&hb_spinlock);
}

heartbeat_state_t heartbeat_get_state(void)
{
    portENTER_CRITICAL(&hb_spinlock);
    heartbeat_state_t st = s_state;
    portEXIT_CRITICAL(&hb_spinlock);
    return st;
}

heartbeat_status_t heartbeat_get_status(void)
{
    portENTER_CRITICAL(&hb_spinlock);
    heartbeat_status_t status = {
        .state = s_state,
        .last_heartbeat_us = s_last_heartbeat_us,
        .reset_count = s_reset_count,
        .first_reset_us = s_first_reset_us,
    };
    portEXIT_CRITICAL(&hb_spinlock);
    return status;
}

#ifdef CONFIG_PI5_POWER_ENABLED
static void power_cycle_pi5(void)
{
    ESP_LOGW(TAG, "Power-cycling Pi 5 (reset #%d)", s_reset_count + 1);
    gpio_set_level(PI5_RELAY_GPIO, 0); // Relay OFF
    vTaskDelay(pdMS_TO_TICKS(HEARTBEAT_RELAY_PULSE_MS));
    gpio_set_level(PI5_RELAY_GPIO, 1); // Relay ON

    int64_t now = esp_timer_get_time();

    // Check window expiry BEFORE incrementing to avoid off-by-one on boundary
    if (s_reset_count > 0) {
        int64_t elapsed_us = now - s_first_reset_us;
        if (elapsed_us > (int64_t)HEARTBEAT_RESET_WINDOW_MS * 1000) {
            s_reset_count = 0;
            s_first_reset_us = now;
        }
    }

    if (s_reset_count == 0) {
        s_first_reset_us = now;
    }
    s_reset_count++;

    if (s_reset_count >= HEARTBEAT_MAX_RESETS) {
        ESP_LOGE(TAG, "Max resets reached (%d in %ld min) - entering safe mode",
                 HEARTBEAT_MAX_RESETS, (long)(HEARTBEAT_RESET_WINDOW_MS / 60000));
        s_state = HB_STATE_SAFE_MODE;
    } else {
        s_state = HB_STATE_WAITING;
        s_last_heartbeat_us = esp_timer_get_time();
        s_init_time_us = s_last_heartbeat_us;
    }
}
#endif // CONFIG_PI5_POWER_ENABLED

void heartbeat_monitor_task(void *params)
{
    (void)params;

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));

        portENTER_CRITICAL(&hb_spinlock);
        heartbeat_state_t current_state = s_state;
        int64_t last_hb = s_last_heartbeat_us;
        portEXIT_CRITICAL(&hb_spinlock);

        if (current_state == HB_STATE_SAFE_MODE) {
            continue;
        }

        if (current_state == HB_STATE_WAITING) {
            continue;
        }

        int64_t now = esp_timer_get_time();
        int64_t elapsed_ms = (now - last_hb) / 1000;

        if (elapsed_ms > HEARTBEAT_TIMEOUT_MS) {
            ESP_LOGW(TAG, "Heartbeat timeout (%lld ms > %d ms)",
                     (long long)elapsed_ms, HEARTBEAT_TIMEOUT_MS);
            portENTER_CRITICAL(&hb_spinlock);
            s_state = HB_STATE_TIMEOUT;
            portEXIT_CRITICAL(&hb_spinlock);
#ifdef CONFIG_PI5_POWER_ENABLED
            power_cycle_pi5();
#endif
        }
    }
}
