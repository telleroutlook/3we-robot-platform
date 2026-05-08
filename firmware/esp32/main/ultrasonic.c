// SPDX-License-Identifier: Apache-2.0
#include "ultrasonic.h"
#include "pin_definitions.h"
#include "robot_params.h"

#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <string.h>

static const char *TAG = "ultrasonic";

static const uint8_t echo_pins[US_COUNT] = {
    [US_FRONT] = US_ECHO_FRONT,
    [US_BACK]  = US_ECHO_BACK,
    [US_LEFT]  = US_ECHO_LEFT,
    [US_RIGHT] = US_ECHO_RIGHT,
};

static float last_distance[US_COUNT];

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
        gpio_config_t echo_cfg = {
            .pin_bit_mask = (1ULL << echo_pins[i]),
            .mode = GPIO_MODE_INPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
        };
        gpio_config(&echo_cfg);
        last_distance[i] = US_MAX_RANGE_M;
    }

    ESP_LOGI(TAG, "Ultrasonic sensors initialized (trig=%d)", US_TRIG);
    return ESP_OK;
}

esp_err_t ultrasonic_read(ultrasonic_id_t id, float *distance_m)
{
    if (id >= US_COUNT || !distance_m) return ESP_ERR_INVALID_ARG;

    // Send trigger pulse
    gpio_set_level(US_TRIG, 1);
    esp_rom_delay_us(US_TRIGGER_PULSE_US);
    gpio_set_level(US_TRIG, 0);

    // Wait for echo to go high
    int64_t start = esp_timer_get_time();
    while (gpio_get_level(echo_pins[id]) == 0) {
        if ((esp_timer_get_time() - start) > US_TIMEOUT_US) {
            *distance_m = US_MAX_RANGE_M;
            return ESP_ERR_TIMEOUT;
        }
    }

    // Measure echo pulse width
    int64_t echo_start = esp_timer_get_time();
    while (gpio_get_level(echo_pins[id]) == 1) {
        if ((esp_timer_get_time() - echo_start) > US_TIMEOUT_US) {
            *distance_m = US_MAX_RANGE_M;
            return ESP_ERR_TIMEOUT;
        }
    }
    int64_t echo_end = esp_timer_get_time();

    float pulse_us = (float)(echo_end - echo_start);
    *distance_m = (pulse_us * 0.000343f) / 2.0f;

    if (*distance_m < US_MIN_RANGE_M) *distance_m = US_MIN_RANGE_M;
    if (*distance_m > US_MAX_RANGE_M) *distance_m = US_MAX_RANGE_M;

    return ESP_OK;
}

float ultrasonic_get_last(ultrasonic_id_t id)
{
    if (id >= US_COUNT) return US_MAX_RANGE_M;
    return last_distance[id];
}

void ultrasonic_task(void *params)
{
    const TickType_t period = pdMS_TO_TICKS(1000 / ULTRASONIC_PUBLISH_HZ);
    ultrasonic_id_t current = US_FRONT;

    while (1) {
        float dist;
        if (ultrasonic_read(current, &dist) == ESP_OK) {
            last_distance[current] = dist;
        }

        current = (current + 1) % US_COUNT;
        vTaskDelay(period / US_COUNT);
    }
}
