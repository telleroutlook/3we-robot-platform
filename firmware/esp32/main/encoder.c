// SPDX-License-Identifier: Apache-2.0
#include "encoder.h"
#include "pin_definitions.h"
#include "robot_params.h"

#include "driver/pulse_cnt.h"
#include "esp_log.h"
#include "esp_timer.h"

#include <stdlib.h>

static const char *TAG = "encoder";

typedef struct {
    uint8_t gpio_a;
    uint8_t gpio_b;
} encoder_pins_t;

static const encoder_pins_t enc_pins[MOTOR_COUNT] = {
    [MOTOR_FL] = { ENC_FL_A, ENC_FL_B },
    [MOTOR_FR] = { ENC_FR_A, ENC_FR_B },
    [MOTOR_RL] = { ENC_RL_A, ENC_RL_B },
    [MOTOR_RR] = { ENC_RR_A, ENC_RR_B },
};

static pcnt_unit_handle_t pcnt_units[MOTOR_COUNT];
static float speed_rps[MOTOR_COUNT];
static int64_t last_update_us;
static portMUX_TYPE encoder_spinlock = portMUX_INITIALIZER_UNLOCKED;

static void encoder_validate_config(void);

esp_err_t encoder_init(void)
{
    for (int i = 0; i < MOTOR_COUNT; i++) {
        pcnt_unit_config_t unit_cfg = {
            .high_limit = 32767,
            .low_limit = -32767,
        };
        ESP_ERROR_CHECK(pcnt_new_unit(&unit_cfg, &pcnt_units[i]));

        pcnt_chan_config_t chan_a_cfg = {
            .edge_gpio_num = enc_pins[i].gpio_a,
            .level_gpio_num = enc_pins[i].gpio_b,
        };
        pcnt_channel_handle_t chan_a;
        ESP_ERROR_CHECK(pcnt_new_channel(pcnt_units[i], &chan_a_cfg, &chan_a));
        pcnt_channel_set_edge_action(chan_a,
            PCNT_CHANNEL_EDGE_ACTION_DECREASE,
            PCNT_CHANNEL_EDGE_ACTION_INCREASE);
        pcnt_channel_set_level_action(chan_a,
            PCNT_CHANNEL_LEVEL_ACTION_KEEP,
            PCNT_CHANNEL_LEVEL_ACTION_INVERSE);

        pcnt_chan_config_t chan_b_cfg = {
            .edge_gpio_num = enc_pins[i].gpio_b,
            .level_gpio_num = enc_pins[i].gpio_a,
        };
        pcnt_channel_handle_t chan_b;
        ESP_ERROR_CHECK(pcnt_new_channel(pcnt_units[i], &chan_b_cfg, &chan_b));
        pcnt_channel_set_edge_action(chan_b,
            PCNT_CHANNEL_EDGE_ACTION_INCREASE,
            PCNT_CHANNEL_EDGE_ACTION_DECREASE);
        pcnt_channel_set_level_action(chan_b,
            PCNT_CHANNEL_LEVEL_ACTION_KEEP,
            PCNT_CHANNEL_LEVEL_ACTION_INVERSE);

        pcnt_glitch_filter_config_t filter_cfg = { .max_glitch_ns = 1000 };
        pcnt_unit_set_glitch_filter(pcnt_units[i], &filter_cfg);

        pcnt_unit_enable(pcnt_units[i]);
        pcnt_unit_clear_count(pcnt_units[i]);
        pcnt_unit_start(pcnt_units[i]);

        speed_rps[i] = 0.0f;
    }

    ESP_LOGI(TAG, "Encoders initialized (PCNT, %d CPR)", ENCODER_CPR);

    encoder_validate_config();

    last_update_us = esp_timer_get_time();

    return ESP_OK;
}

#define MIN_RAW_CPR  12

static void encoder_validate_config(void)
{
    uint16_t raw_cpr = (uint16_t)((float)ENCODER_CPR / (float)GEAR_RATIO);
    if (raw_cpr < MIN_RAW_CPR) {
        ESP_LOGW(TAG, "Raw encoder CPR %d < minimum %d — high-speed PID may oscillate",
                 raw_cpr, MIN_RAW_CPR);
    }

    for (int i = 0; i < MOTOR_COUNT; i++) {
        int count = 0;
        pcnt_unit_get_count(pcnt_units[i], &count);
        if (abs(count) > 2) {
            ESP_LOGW(TAG, "Motor %d encoder non-zero at boot (%d) — check wiring", i, count);
        }
    }
}

int32_t encoder_get_count(motor_id_t id)
{
    if (id >= MOTOR_COUNT) return 0;
    int count = 0;
    pcnt_unit_get_count(pcnt_units[id], &count);
    return (int32_t)count;
}

float encoder_get_speed_rps(motor_id_t id)
{
    if (id >= MOTOR_COUNT) return 0.0f;
    portENTER_CRITICAL(&encoder_spinlock);
    float val = speed_rps[id];
    portEXIT_CRITICAL(&encoder_spinlock);
    return val;
}

void encoder_update(void)
{
    int64_t now = esp_timer_get_time();
    float dt = (float)(now - last_update_us) / 1000000.0f;
    if (dt <= 0.0f) dt = 1.0f / (float)CONTROL_FREQ_HZ;
    last_update_us = now;

    for (int i = 0; i < MOTOR_COUNT; i++) {
        int count = 0;
        portENTER_CRITICAL(&encoder_spinlock);
        pcnt_unit_get_count(pcnt_units[i], &count);
        pcnt_unit_clear_count(pcnt_units[i]);
        speed_rps[i] = ((float)count / (float)ENCODER_CPR) / dt;
        portEXIT_CRITICAL(&encoder_spinlock);
    }
}
