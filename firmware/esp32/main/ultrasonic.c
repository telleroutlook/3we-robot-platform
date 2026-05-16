// SPDX-License-Identifier: Apache-2.0
#include "ultrasonic.h"
#include "safety.h"
#include "pin_definitions.h"
#include "robot_params.h"

#include "driver/gpio.h"
#include "driver/rmt_rx.h"
#include "driver/rmt_tx.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

#include <string.h>

static const char *TAG = "ultrasonic";

static const uint8_t echo_pins[US_COUNT] = {
    [US_FRONT] = US_ECHO_FRONT,
    [US_BACK]  = US_ECHO_BACK,
    [US_LEFT]  = US_ECHO_LEFT,
    [US_RIGHT] = US_ECHO_RIGHT,
};

static float last_distance[US_COUNT];
static portMUX_TYPE distance_spinlock = portMUX_INITIALIZER_UNLOCKED;

static rmt_channel_handle_t rx_channels[US_COUNT];
static rmt_receive_config_t rx_config;
static rmt_symbol_word_t rx_symbols[US_COUNT][64];
static SemaphoreHandle_t rx_done_sem[US_COUNT];

static bool rmt_rx_done_callback(rmt_channel_handle_t channel,
                                 const rmt_rx_done_event_data_t *edata,
                                 void *user_data)
{
    BaseType_t high_task_wakeup = pdFALSE;
    SemaphoreHandle_t sem = (SemaphoreHandle_t)user_data;
    xSemaphoreGiveFromISR(sem, &high_task_wakeup);
    return high_task_wakeup == pdTRUE;
}

esp_err_t ultrasonic_init(void)
{
    gpio_config_t trig_cfg = {
        .pin_bit_mask = (1ULL << US_TRIG),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
    };
    gpio_config(&trig_cfg);
    gpio_set_level(US_TRIG, 0);

    for (int i = 0; i < US_COUNT; i++) {
        last_distance[i] = US_MAX_RANGE_M;

        rx_done_sem[i] = xSemaphoreCreateBinary();

        rmt_rx_channel_config_t rx_chan_cfg = {
            .gpio_num = echo_pins[i],
            .clk_src = RMT_CLK_SRC_DEFAULT,
            .resolution_hz = 1000000,  // 1 µs resolution
            .mem_block_symbols = 64,
        };
        ESP_ERROR_CHECK(rmt_new_rx_channel(&rx_chan_cfg, &rx_channels[i]));

        rmt_rx_event_callbacks_t cbs = {
            .on_recv_done = rmt_rx_done_callback,
        };
        ESP_ERROR_CHECK(rmt_rx_register_event_callbacks(rx_channels[i], &cbs, rx_done_sem[i]));
        ESP_ERROR_CHECK(rmt_enable(rx_channels[i]));
    }

    rx_config.signal_range_min_ns = 1000;
    rx_config.signal_range_max_ns = US_TIMEOUT_US * 1000;

    ESP_LOGI(TAG, "Ultrasonic sensors initialized with RMT (trig=%d)", US_TRIG);
    return ESP_OK;
}

esp_err_t ultrasonic_read(ultrasonic_id_t id, float *distance_m)
{
    if (id >= US_COUNT || !distance_m) return ESP_ERR_INVALID_ARG;

    ESP_ERROR_CHECK(rmt_receive(rx_channels[id], rx_symbols[id],
                                sizeof(rx_symbols[id]), &rx_config));

    // Send trigger pulse
    gpio_set_level(US_TRIG, 1);
    esp_rom_delay_us(US_TRIGGER_PULSE_US);
    gpio_set_level(US_TRIG, 0);

    // Wait for RMT capture to complete (interrupt-driven)
    if (xSemaphoreTake(rx_done_sem[id], pdMS_TO_TICKS(30)) != pdTRUE) {
        *distance_m = US_MAX_RANGE_M;
        return ESP_ERR_TIMEOUT;
    }

    // Parse captured symbols: look for the echo pulse (high duration)
    uint32_t pulse_us = 0;
    for (int s = 0; s < 64 && rx_symbols[id][s].duration0 != 0; s++) {
        if (rx_symbols[id][s].level0 == 1) {
            pulse_us = rx_symbols[id][s].duration0;
            break;
        }
        if (rx_symbols[id][s].level1 == 1) {
            pulse_us = rx_symbols[id][s].duration1;
            break;
        }
    }

    if (pulse_us == 0) {
        *distance_m = US_MAX_RANGE_M;
        return ESP_ERR_TIMEOUT;
    }

    *distance_m = ((float)pulse_us * 0.000343f) / 2.0f;

    // Reject cross-echo multipath from shared trigger firing all sensors simultaneously
    if (*distance_m < US_CROSS_ECHO_MIN_M) {
        *distance_m = US_MAX_RANGE_M;
        return ESP_ERR_INVALID_RESPONSE;
    }

    if (*distance_m > US_MAX_RANGE_M) *distance_m = US_MAX_RANGE_M;

    return ESP_OK;
}

float ultrasonic_get_last(ultrasonic_id_t id)
{
    if (id >= US_COUNT) return US_MAX_RANGE_M;
    portENTER_CRITICAL(&distance_spinlock);
    float val = last_distance[id];
    portEXIT_CRITICAL(&distance_spinlock);
    return val;
}

void ultrasonic_task(void *params)
{
    (void)params;
    ultrasonic_id_t current = US_FRONT;

    while (1) {
        float dist;
        if (ultrasonic_read(current, &dist) == ESP_OK) {
            portENTER_CRITICAL(&distance_spinlock);
            last_distance[current] = dist;
            portEXIT_CRITICAL(&distance_spinlock);
            if (dist < US_SAFETY_THRESHOLD_M && !safety_is_estopped()) {
                ESP_LOGW(TAG, "Obstacle at %.3fm on sensor %d - triggering estop",
                         dist, current);
                safety_trigger_estop();
            }
        }

        current = (current + 1) % US_COUNT;

        // Guard delay between sensors: shared trigger pin means all sensors
        // echo simultaneously. Wait for max echo return time before next trigger
        // to prevent stale echo capture on the next sensor's RMT channel.
        vTaskDelay(pdMS_TO_TICKS(30));
    }
}
