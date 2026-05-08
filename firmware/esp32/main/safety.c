// SPDX-License-Identifier: Apache-2.0
#include "safety.h"
#include "motor_control.h"
#include "pin_definitions.h"
#include "robot_params.h"

#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "safety";

static volatile safety_state_t state = SAFETY_NORMAL;
static volatile int64_t last_watchdog_feed = 0;
static safety_callback_t user_callback = NULL;

static void notify_state_change(void)
{
    if (user_callback) user_callback(state);
}

static void IRAM_ATTR estop_isr(void *arg)
{
    state = SAFETY_ESTOPPED;
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
    ESP_LOGI(TAG, "Safety system initialized (E-stop GPIO=%d)", ESTOP_GPIO);
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
    if (state == SAFETY_NORMAL) {
        state = SAFETY_ESTOPPED;
        motor_stop_all();
        notify_state_change();
        ESP_LOGW(TAG, "Software E-stop triggered");
    }
}

esp_err_t safety_reset(void)
{
    // Only allow reset if physical button is released (high)
    if (gpio_get_level(ESTOP_GPIO) == 0) {
        ESP_LOGW(TAG, "Cannot reset: E-stop button still pressed");
        return ESP_ERR_INVALID_STATE;
    }

    state = SAFETY_NORMAL;
    last_watchdog_feed = esp_timer_get_time();
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
        if (gpio_get_level(ESTOP_GPIO) == 0 && state == SAFETY_NORMAL) {
            vTaskDelay(pdMS_TO_TICKS(ESTOP_DEBOUNCE_MS));
            if (gpio_get_level(ESTOP_GPIO) == 0) {
                state = SAFETY_ESTOPPED;
                motor_stop_all();
                notify_state_change();
                ESP_LOGW(TAG, "Hardware E-stop detected");
            }
        }

        // Watchdog: if control loop stalls, stop motors
        if (state == SAFETY_NORMAL) {
            int64_t elapsed = esp_timer_get_time() - last_watchdog_feed;
            if (elapsed > (WATCHDOG_TIMEOUT_MS * 1000LL)) {
                state = SAFETY_ESTOPPED;
                motor_stop_all();
                notify_state_change();
                ESP_LOGW(TAG, "Watchdog timeout - control loop stalled");
            }
        }

        vTaskDelay(pdMS_TO_TICKS(20));
    }
}
