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
#define NVS_KEY_RELAY_FAULT "relay_flt"
#define DEFAULT_SPEED_LIMIT 1.0f

static portMUX_TYPE safety_spinlock = portMUX_INITIALIZER_UNLOCKED;
static volatile safety_state_t state = SAFETY_NORMAL;
static volatile int64_t last_watchdog_feed = 0;
static safety_callback_t user_callback = NULL;
static float speed_limit_mps = DEFAULT_SPEED_LIMIT;
static volatile uint8_t relay_fault_count = 0;

static void persist_relay_fault(void);

static void notify_state_change(safety_state_t snapshot)
{
    safety_callback_t cb = user_callback;
    if (cb) cb(snapshot);
}

static void IRAM_ATTR estop_isr(void *arg)
{
    portENTER_CRITICAL_ISR(&safety_spinlock);
    state = SAFETY_ESTOPPED;
    portEXIT_CRITICAL_ISR(&safety_spinlock);
}

esp_err_t safety_init(void)
{
    state = SAFETY_NORMAL;
    relay_fault_count = 0;
    user_callback = NULL;
    speed_limit_mps = DEFAULT_SPEED_LIMIT;

    gpio_config_t io_cfg = {
        .pin_bit_mask = (1ULL << ESTOP_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    ESP_ERROR_CHECK(gpio_config(&io_cfg));

    // Configure dual-channel relay feedback inputs
    gpio_config_t fb_cfg = {
        .pin_bit_mask = (1ULL << SAFETY_RELAY_FB) | (1ULL << SAFETY_RELAY_FB2),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&fb_cfg));

    esp_err_t isr_ret = gpio_install_isr_service(0);
    if (isr_ret != ESP_OK && isr_ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "ISR service install failed: %s", esp_err_to_name(isr_ret));
        return isr_ret;
    }
    esp_err_t isr_add_ret = gpio_isr_handler_add(ESTOP_GPIO, estop_isr, NULL);
    if (isr_add_ret != ESP_OK) {
        ESP_LOGE(TAG, "E-stop ISR registration failed: %s - relying on polling only",
                 esp_err_to_name(isr_add_ret));
    }

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
        uint8_t fault_flag = 0;
        if (nvs_get_u8(nvs, NVS_KEY_RELAY_FAULT, &fault_flag) == ESP_OK && fault_flag != 0) {
            state = SAFETY_RELAY_FAULT;
            ESP_LOGE(TAG, "Persistent relay fault flag set - physical service required");
        }
        nvs_close(nvs);
    }

    ESP_LOGI(TAG, "Safety system initialized (E-stop GPIO=%d, speed_limit=%.2f m/s)",
             ESTOP_GPIO, speed_limit_mps);
    return ESP_OK;
}

safety_state_t safety_get_state(void)
{
    portENTER_CRITICAL(&safety_spinlock);
    safety_state_t s = state;
    portEXIT_CRITICAL(&safety_spinlock);
    return s;
}

bool safety_is_estopped(void)
{
    portENTER_CRITICAL(&safety_spinlock);
    bool estopped = (state != SAFETY_NORMAL);
    portEXIT_CRITICAL(&safety_spinlock);
    return estopped;
}

bool safety_is_relay_faulted(void)
{
    portENTER_CRITICAL(&safety_spinlock);
    bool faulted = (state == SAFETY_RELAY_FAULT);
    portEXIT_CRITICAL(&safety_spinlock);
    return faulted;
}

#ifndef TESTABLE_WEAK
#define TESTABLE_WEAK
#endif

TESTABLE_WEAK void safety_trigger_estop(void)
{
    portENTER_CRITICAL(&safety_spinlock);
    if (state == SAFETY_NORMAL) {
        state = SAFETY_ESTOPPED;
        portEXIT_CRITICAL(&safety_spinlock);
        motor_stop_all();
        notify_state_change(SAFETY_ESTOPPED);
        ESP_LOGW(TAG, "Software E-stop triggered");
    } else {
        portEXIT_CRITICAL(&safety_spinlock);
    }
}

esp_err_t safety_reset(void)
{
    if (gpio_get_level(ESTOP_GPIO) == 0) {
        ESP_LOGW(TAG, "Cannot reset: E-stop button still pressed");
        return ESP_ERR_INVALID_STATE;
    }

    portENTER_CRITICAL(&safety_spinlock);
    if (state == SAFETY_RELAY_FAULT) {
        portEXIT_CRITICAL(&safety_spinlock);
        ESP_LOGE(TAG, "Cannot reset: relay hardware fault - physical service required");
        return ESP_ERR_INVALID_STATE;
    }
    if (state != SAFETY_ESTOPPED) {
        portEXIT_CRITICAL(&safety_spinlock);
        return ESP_ERR_INVALID_STATE;
    }
    state = SAFETY_RECOVERY_PENDING;
    portEXIT_CRITICAL(&safety_spinlock);
    notify_state_change(SAFETY_RECOVERY_PENDING);
    ESP_LOGI(TAG, "Safety recovery pending - awaiting confirmation");
    return ESP_OK;
}

esp_err_t safety_confirm_reset(void)
{
    if (gpio_get_level(ESTOP_GPIO) == 0) {
        portENTER_CRITICAL(&safety_spinlock);
        state = SAFETY_ESTOPPED;
        portEXIT_CRITICAL(&safety_spinlock);
        notify_state_change(SAFETY_ESTOPPED);
        ESP_LOGW(TAG, "Confirm failed: E-stop pressed during recovery");
        return ESP_ERR_INVALID_STATE;
    }

    int64_t now = esp_timer_get_time();
    portENTER_CRITICAL(&safety_spinlock);
    if (state != SAFETY_RECOVERY_PENDING) {
        portEXIT_CRITICAL(&safety_spinlock);
        return ESP_ERR_INVALID_STATE;
    }
    state = SAFETY_NORMAL;
    last_watchdog_feed = now;
    portEXIT_CRITICAL(&safety_spinlock);
    notify_state_change(SAFETY_NORMAL);
    ESP_LOGI(TAG, "Safety reset confirmed - returning to normal operation");
    return ESP_OK;
}

void safety_register_callback(safety_callback_t cb)
{
    portENTER_CRITICAL(&safety_spinlock);
    user_callback = cb;
    portEXIT_CRITICAL(&safety_spinlock);
}

void safety_feed_watchdog(void)
{
    int64_t now = esp_timer_get_time();
    portENTER_CRITICAL(&safety_spinlock);
    int64_t elapsed = now - last_watchdog_feed;
    if (state == SAFETY_NORMAL && elapsed > (WATCHDOG_TIMEOUT_MS * 1000LL)) {
        state = SAFETY_ESTOPPED;
        portEXIT_CRITICAL(&safety_spinlock);
        motor_stop_all();
        notify_state_change(SAFETY_ESTOPPED);
        ESP_LOGW(TAG, "Watchdog timeout - control loop stalled");
        return;
    }
    last_watchdog_feed = now;
    portEXIT_CRITICAL(&safety_spinlock);
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
                notify_state_change(SAFETY_ESTOPPED);
                ESP_LOGW(TAG, "Hardware E-stop detected");
            }
        }

        // Continuous relay feedback monitoring (dual-channel for CE PL d Cat 3)
        int relay_fb = gpio_get_level(SAFETY_RELAY_FB);
        int relay_fb2 = gpio_get_level(SAFETY_RELAY_FB2);

        // Dual-channel consistency check: both channels must agree
        if (relay_fb != relay_fb2) {
            portENTER_CRITICAL(&safety_spinlock);
            relay_fault_count++;
            uint8_t fault_count = relay_fault_count;
            state = SAFETY_ESTOPPED;
            portEXIT_CRITICAL(&safety_spinlock);
            motor_stop_all();
            notify_state_change(SAFETY_ESTOPPED);
            ESP_LOGE(TAG, "RELAY FAULT: dual-channel mismatch (CH1=%d, CH2=%d)", relay_fb, relay_fb2);
            if (fault_count >= 3) {
                portENTER_CRITICAL(&safety_spinlock);
                state = SAFETY_RELAY_FAULT;
                portEXIT_CRITICAL(&safety_spinlock);
                notify_state_change(SAFETY_RELAY_FAULT);
                persist_relay_fault();
                ESP_LOGE(TAG, "RELAY FAULT ESCALATED: channel inconsistency - service required");
            }
        }

        portENTER_CRITICAL(&safety_spinlock);
        current_state = state;
        if (current_state == SAFETY_NORMAL && relay_fb == 0) {
            relay_fault_count++;
            uint8_t fault_count = relay_fault_count;
            state = SAFETY_ESTOPPED;
            portEXIT_CRITICAL(&safety_spinlock);
            motor_stop_all();
            notify_state_change(SAFETY_ESTOPPED);
            ESP_LOGE(TAG, "RELAY FAULT: relay unexpectedly de-energized in NORMAL state");
            if (fault_count >= 3) {
                portENTER_CRITICAL(&safety_spinlock);
                state = SAFETY_RELAY_FAULT;
                portEXIT_CRITICAL(&safety_spinlock);
                notify_state_change(SAFETY_RELAY_FAULT);
                persist_relay_fault();
                ESP_LOGE(TAG, "RELAY FAULT ESCALATED: hardware damage suspected - service required");
            }
        } else if (current_state == SAFETY_ESTOPPED && relay_fb != 0) {
            relay_fault_count++;
            uint8_t fault_count = relay_fault_count;
            portEXIT_CRITICAL(&safety_spinlock);
            ESP_LOGE(TAG, "RELAY FAULT: relay energized while E-stopped - possible welded contact");
            if (fault_count >= 3) {
                portENTER_CRITICAL(&safety_spinlock);
                state = SAFETY_RELAY_FAULT;
                portEXIT_CRITICAL(&safety_spinlock);
                notify_state_change(SAFETY_RELAY_FAULT);
                persist_relay_fault();
                ESP_LOGE(TAG, "RELAY FAULT ESCALATED: welded contact confirmed - service required");
            }
        } else if (current_state == SAFETY_RELAY_FAULT) {
            portEXIT_CRITICAL(&safety_spinlock);
            motor_stop_all();
        } else {
            relay_fault_count = 0;
            portEXIT_CRITICAL(&safety_spinlock);
        }

        // Watchdog: if control loop stalls, stop motors
        portENTER_CRITICAL(&safety_spinlock);
        current_state = state;
        portEXIT_CRITICAL(&safety_spinlock);
        if (current_state == SAFETY_NORMAL) {
            portENTER_CRITICAL(&safety_spinlock);
            int64_t last_feed = last_watchdog_feed;
            portEXIT_CRITICAL(&safety_spinlock);
            int64_t elapsed = esp_timer_get_time() - last_feed;
            if (elapsed > (WATCHDOG_TIMEOUT_MS * 1000LL)) {
                portENTER_CRITICAL(&safety_spinlock);
                state = SAFETY_ESTOPPED;
                portEXIT_CRITICAL(&safety_spinlock);
                motor_stop_all();
                notify_state_change(SAFETY_ESTOPPED);
                ESP_LOGW(TAG, "Watchdog timeout - control loop stalled");
            }
        }

        vTaskDelay(pdMS_TO_TICKS(20));
    }
}

esp_err_t safety_relay_selftest(void)
{
    // Configure feedback pins as input (may already be configured in init)
    gpio_config_t fb_cfg = {
        .pin_bit_mask = (1ULL << SAFETY_RELAY_FB) | (1ULL << SAFETY_RELAY_FB2),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&fb_cfg));

    // With E-stop NOT pressed (NC circuit closed), relay should be energized
    // Both feedback pins should read HIGH when relay is properly engaged
    if (gpio_get_level(ESTOP_GPIO) != 0) {
        vTaskDelay(pdMS_TO_TICKS(50));
        int fb_level = gpio_get_level(SAFETY_RELAY_FB);
        int fb2_level = gpio_get_level(SAFETY_RELAY_FB2);
        if (fb_level == 0 || fb2_level == 0) {
            ESP_LOGE(TAG, "SELF-TEST FAILED: Relay not energized (CH1=%d, CH2=%d)", fb_level, fb2_level);
            portENTER_CRITICAL(&safety_spinlock);
            relay_fault_count++;
            if (relay_fault_count >= 3) {
                state = SAFETY_RELAY_FAULT;
            }
            portEXIT_CRITICAL(&safety_spinlock);
            if (relay_fault_count >= 3) {
                persist_relay_fault();
            }
            return ESP_ERR_INVALID_STATE;
        }
        portENTER_CRITICAL(&safety_spinlock);
        relay_fault_count = 0;
        portEXIT_CRITICAL(&safety_spinlock);
        ESP_LOGI(TAG, "Relay self-test PASSED (CH1=%d, CH2=%d, relay energized)", fb_level, fb2_level);
    } else {
        // E-stop is pressed at boot — relay should be de-energized
        vTaskDelay(pdMS_TO_TICKS(50));
        int fb_level = gpio_get_level(SAFETY_RELAY_FB);
        int fb2_level = gpio_get_level(SAFETY_RELAY_FB2);
        if (fb_level != 0 || fb2_level != 0) {
            ESP_LOGE(TAG, "SELF-TEST FAILED: Relay energized despite E-stop (CH1=%d, CH2=%d)",
                     fb_level, fb2_level);
            portENTER_CRITICAL(&safety_spinlock);
            relay_fault_count++;
            if (relay_fault_count >= 3) {
                state = SAFETY_RELAY_FAULT;
            }
            portEXIT_CRITICAL(&safety_spinlock);
            if (relay_fault_count >= 3) {
                persist_relay_fault();
            }
            return ESP_ERR_INVALID_STATE;
        }
        portENTER_CRITICAL(&safety_spinlock);
        relay_fault_count = 0;
        portEXIT_CRITICAL(&safety_spinlock);
        ESP_LOGI(TAG, "Relay self-test PASSED (CH1=%d, CH2=%d, E-stop active)", fb_level, fb2_level);
    }

    return ESP_OK;
}

static void persist_relay_fault(void)
{
    nvs_handle_t nvs;
    if (nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs) == ESP_OK) {
        nvs_set_u8(nvs, NVS_KEY_RELAY_FAULT, 1);
        nvs_commit(nvs);
        nvs_close(nvs);
    }
}

esp_err_t safety_clear_relay_fault(void)
{
    portENTER_CRITICAL(&safety_spinlock);
    if (state != SAFETY_RELAY_FAULT) {
        portEXIT_CRITICAL(&safety_spinlock);
        return ESP_ERR_INVALID_STATE;
    }
    state = SAFETY_ESTOPPED;
    relay_fault_count = 0;
    portEXIT_CRITICAL(&safety_spinlock);

    nvs_handle_t nvs;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (err == ESP_OK) {
        nvs_erase_key(nvs, NVS_KEY_RELAY_FAULT);
        nvs_commit(nvs);
        nvs_close(nvs);
    }

    notify_state_change(SAFETY_ESTOPPED);
    ESP_LOGI(TAG, "Relay fault cleared - moved to ESTOPPED (manual reset still required)");
    return ESP_OK;
}

esp_err_t safety_set_speed_limit(float limit_mps)
{
    if (limit_mps <= 0.0f || limit_mps > SPEED_LIMIT_HARD_CAP_MPS) {
        ESP_LOGW(TAG, "Speed limit %.2f out of range (0, %.1f]", limit_mps, SPEED_LIMIT_HARD_CAP_MPS);
        return ESP_ERR_INVALID_ARG;
    }

    portENTER_CRITICAL(&safety_spinlock);
    speed_limit_mps = limit_mps;
    portEXIT_CRITICAL(&safety_spinlock);

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
    portENTER_CRITICAL(&safety_spinlock);
    float limit = speed_limit_mps;
    portEXIT_CRITICAL(&safety_spinlock);
    return limit;
}

float safety_clamp_speed(float requested_mps)
{
    portENTER_CRITICAL(&safety_spinlock);
    float limit = speed_limit_mps;
    portEXIT_CRITICAL(&safety_spinlock);
    if (requested_mps > limit) return limit;
    if (requested_mps < -limit) return -limit;
    return requested_mps;
}

