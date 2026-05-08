// SPDX-License-Identifier: Apache-2.0
#include "safety.h"
#include "motor_control.h"
#include "pin_definitions.h"
#include "robot_params.h"

#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <math.h>
#include <string.h>

static const char *TAG = "safety";

#define NVS_NAMESPACE       "safety"
#define NVS_KEY_SPEED_LIM   "spd_lim"
#define DEFAULT_SPEED_LIMIT 1.0f

static portMUX_TYPE safety_spinlock = portMUX_INITIALIZER_UNLOCKED;
static volatile safety_state_t state = SAFETY_NORMAL;
static volatile int64_t last_watchdog_feed = 0;
static safety_callback_t user_callback = NULL;
static float speed_limit_mps = DEFAULT_SPEED_LIMIT;

static void notify_state_change(void)
{
    if (user_callback) user_callback(state);
}

static void IRAM_ATTR estop_isr(void *arg)
{
    portENTER_CRITICAL_ISR(&safety_spinlock);
    state = SAFETY_ESTOPPED;
    portEXIT_CRITICAL_ISR(&safety_spinlock);
}

esp_err_t safety_init(void)
{
    gpio_config_t io_cfg = {
        .pin_bit_mask = (1ULL << ESTOP_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    ESP_ERROR_CHECK(gpio_config(&io_cfg));

    gpio_install_isr_service(0);
    gpio_isr_handler_add(ESTOP_GPIO, estop_isr, NULL);

    // Check initial state (NC button: low = pressed/stopped)
    if (gpio_get_level(ESTOP_GPIO) == 0) {
        state = SAFETY_ESTOPPED;
        ESP_LOGW(TAG, "E-stop active at boot");
    }

    last_watchdog_feed = esp_timer_get_time();

    // Load persisted speed limit from NVS
    nvs_handle_t nvs;
    if (nvs_open(NVS_NAMESPACE, NVS_READONLY, &nvs) == ESP_OK) {
        uint32_t raw = 0;
        if (nvs_get_u32(nvs, NVS_KEY_SPEED_LIM, &raw) == ESP_OK) {
            float loaded;
            memcpy(&loaded, &raw, sizeof(loaded));
            if (loaded > 0.0f && loaded <= SPEED_LIMIT_HARD_CAP_MPS) {
                speed_limit_mps = loaded;
            }
        }
        nvs_close(nvs);
    }

    ESP_LOGI(TAG, "Safety system initialized (E-stop GPIO=%d, speed_limit=%.2f m/s)",
             ESTOP_GPIO, speed_limit_mps);
    return ESP_OK;
}

safety_state_t safety_get_state(void)
{
    return state;
}

bool safety_is_estopped(void)
{
    return state != SAFETY_NORMAL;
}

void safety_trigger_estop(void)
{
    portENTER_CRITICAL(&safety_spinlock);
    if (state == SAFETY_NORMAL) {
        state = SAFETY_ESTOPPED;
        portEXIT_CRITICAL(&safety_spinlock);
        motor_stop_all();
        notify_state_change();
        ESP_LOGW(TAG, "Software E-stop triggered");
    } else {
        portEXIT_CRITICAL(&safety_spinlock);
    }
}

esp_err_t safety_reset(void)
{
    // Only allow reset if physical button is released (high)
    if (gpio_get_level(ESTOP_GPIO) == 0) {
        ESP_LOGW(TAG, "Cannot reset: E-stop button still pressed");
        return ESP_ERR_INVALID_STATE;
    }

    portENTER_CRITICAL(&safety_spinlock);
    state = SAFETY_NORMAL;
    last_watchdog_feed = esp_timer_get_time();
    portEXIT_CRITICAL(&safety_spinlock);
    notify_state_change();
    ESP_LOGI(TAG, "Safety reset - returning to normal operation");
    return ESP_OK;
}

void safety_register_callback(safety_callback_t cb)
{
    user_callback = cb;
}

void safety_feed_watchdog(void)
{
    last_watchdog_feed = esp_timer_get_time();
}

void safety_task(void *params)
{
    while (1) {
        // Check hardware E-stop (debounced via ISR + periodic poll)
        portENTER_CRITICAL(&safety_spinlock);
        safety_state_t current_state = state;
        portEXIT_CRITICAL(&safety_spinlock);

        if (gpio_get_level(ESTOP_GPIO) == 0 && current_state == SAFETY_NORMAL) {
            vTaskDelay(pdMS_TO_TICKS(ESTOP_DEBOUNCE_MS));
            if (gpio_get_level(ESTOP_GPIO) == 0) {
                portENTER_CRITICAL(&safety_spinlock);
                state = SAFETY_ESTOPPED;
                portEXIT_CRITICAL(&safety_spinlock);
                motor_stop_all();
                notify_state_change();
                ESP_LOGW(TAG, "Hardware E-stop detected");
            }
        }

        // Watchdog: if control loop stalls, stop motors
        if (current_state == SAFETY_NORMAL) {
            int64_t elapsed = esp_timer_get_time() - last_watchdog_feed;
            if (elapsed > (WATCHDOG_TIMEOUT_MS * 1000LL)) {
                portENTER_CRITICAL(&safety_spinlock);
                state = SAFETY_ESTOPPED;
                portEXIT_CRITICAL(&safety_spinlock);
                motor_stop_all();
                notify_state_change();
                ESP_LOGW(TAG, "Watchdog timeout - control loop stalled");
            }
        }

        vTaskDelay(pdMS_TO_TICKS(20));
    }
}

esp_err_t safety_relay_selftest(void)
{
    // Configure feedback pin as input
    gpio_config_t fb_cfg = {
        .pin_bit_mask = (1ULL << SAFETY_RELAY_FB),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&fb_cfg));

    // With E-stop NOT pressed (NC circuit closed), relay should be energized
    // Feedback pin should read HIGH when relay is properly engaged
    if (gpio_get_level(ESTOP_GPIO) != 0) {
        vTaskDelay(pdMS_TO_TICKS(50));
        int fb_level = gpio_get_level(SAFETY_RELAY_FB);
        if (fb_level == 0) {
            ESP_LOGE(TAG, "SELF-TEST FAILED: Relay not energized despite E-stop released");
            state = SAFETY_ESTOPPED;
            return ESP_ERR_INVALID_STATE;
        }
        ESP_LOGI(TAG, "Relay self-test PASSED (feedback=HIGH, relay energized)");
    } else {
        // E-stop is pressed at boot — relay should be de-energized
        vTaskDelay(pdMS_TO_TICKS(50));
        int fb_level = gpio_get_level(SAFETY_RELAY_FB);
        if (fb_level != 0) {
            ESP_LOGE(TAG, "SELF-TEST FAILED: Relay energized despite E-stop pressed");
            return ESP_ERR_INVALID_STATE;
        }
        ESP_LOGI(TAG, "Relay self-test PASSED (feedback=LOW, E-stop active)");
    }

    return ESP_OK;
}

esp_err_t safety_set_speed_limit(float limit_mps)
{
    if (limit_mps <= 0.0f || limit_mps > SPEED_LIMIT_HARD_CAP_MPS) {
        ESP_LOGW(TAG, "Speed limit %.2f out of range (0, %.1f]", limit_mps, SPEED_LIMIT_HARD_CAP_MPS);
        return ESP_ERR_INVALID_ARG;
    }

    speed_limit_mps = limit_mps;

    // Persist to NVS
    nvs_handle_t nvs;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (err == ESP_OK) {
        uint32_t raw;
        memcpy(&raw, &limit_mps, sizeof(raw));
        nvs_set_u32(nvs, NVS_KEY_SPEED_LIM, raw);
        nvs_commit(nvs);
        nvs_close(nvs);
    }

    ESP_LOGI(TAG, "Speed limit set to %.2f m/s (persisted)", speed_limit_mps);
    return ESP_OK;
}

float safety_get_speed_limit(void)
{
    return speed_limit_mps;
}

float safety_clamp_speed(float requested_mps)
{
    if (requested_mps > speed_limit_mps) return speed_limit_mps;
    if (requested_mps < -speed_limit_mps) return -speed_limit_mps;
    return requested_mps;
}

