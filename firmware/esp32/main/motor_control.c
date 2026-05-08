// SPDX-License-Identifier: Apache-2.0
#include "motor_control.h"
#include "pin_definitions.h"
#include "robot_params.h"

#include "driver/ledc.h"
#include "esp_log.h"

#include <math.h>

static const char *TAG = "motor";

typedef struct {
    uint8_t in1_gpio;
    uint8_t in2_gpio;
    ledc_channel_t in1_ch;
    ledc_channel_t in2_ch;
} motor_config_t;

static const motor_config_t motors[MOTOR_COUNT] = {
    [MOTOR_FL] = { MOTOR_FL_IN1, MOTOR_FL_IN2, MOTOR_FL_IN1_CH, MOTOR_FL_IN2_CH },
    [MOTOR_FR] = { MOTOR_FR_IN1, MOTOR_FR_IN2, MOTOR_FR_IN1_CH, MOTOR_FR_IN2_CH },
    [MOTOR_RL] = { MOTOR_RL_IN1, MOTOR_RL_IN2, MOTOR_RL_IN1_CH, MOTOR_RL_IN2_CH },
    [MOTOR_RR] = { MOTOR_RR_IN1, MOTOR_RR_IN2, MOTOR_RR_IN1_CH, MOTOR_RR_IN2_CH },
};

static bool stopped = true;

esp_err_t motor_init(void)
{
    ledc_timer_config_t timer_cfg = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = PWM_RESOLUTION_BITS,
        .timer_num = LEDC_TIMER_0,
        .freq_hz = PWM_FREQUENCY_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ESP_ERROR_CHECK(ledc_timer_config(&timer_cfg));

    for (int i = 0; i < MOTOR_COUNT; i++) {
        ledc_channel_config_t ch1 = {
            .speed_mode = LEDC_LOW_SPEED_MODE,
            .channel = motors[i].in1_ch,
            .timer_sel = LEDC_TIMER_0,
            .gpio_num = motors[i].in1_gpio,
            .duty = 0,
            .hpoint = 0,
        };
        ESP_ERROR_CHECK(ledc_channel_config(&ch1));

        ledc_channel_config_t ch2 = {
            .speed_mode = LEDC_LOW_SPEED_MODE,
            .channel = motors[i].in2_ch,
            .timer_sel = LEDC_TIMER_0,
            .gpio_num = motors[i].in2_gpio,
            .duty = 0,
            .hpoint = 0,
        };
        ESP_ERROR_CHECK(ledc_channel_config(&ch2));
    }

    ESP_LOGI(TAG, "Motor control initialized (%d Hz PWM, %d-bit)",
             PWM_FREQUENCY_HZ, PWM_RESOLUTION_BITS);
    return ESP_OK;
}

void motor_set_speed(motor_id_t id, float speed_pct)
{
    if (id >= MOTOR_COUNT) return;

    float clamped = fmaxf(-1.0f, fminf(1.0f, speed_pct));
    uint32_t duty = (uint32_t)(fabsf(clamped) * PWM_MAX_DUTY);

    if (clamped >= 0.0f) {
        ledc_set_duty(LEDC_LOW_SPEED_MODE, motors[id].in1_ch, duty);
        ledc_set_duty(LEDC_LOW_SPEED_MODE, motors[id].in2_ch, 0);
    } else {
        ledc_set_duty(LEDC_LOW_SPEED_MODE, motors[id].in1_ch, 0);
        ledc_set_duty(LEDC_LOW_SPEED_MODE, motors[id].in2_ch, duty);
    }
    ledc_update_duty(LEDC_LOW_SPEED_MODE, motors[id].in1_ch);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, motors[id].in2_ch);

    stopped = false;
}

motor_output_t motor_mecanum_drive(const cmd_vel_t *cmd)
{
    motor_output_t out;

    float vx = cmd->vx;
    float vy = cmd->vy;
    float wz = cmd->omega;
    float k = LX + LY;

    float raw[MOTOR_COUNT] = {
        vx - vy - wz * k,  // Front Left
        vx + vy + wz * k,  // Front Right
        vx + vy - wz * k,  // Rear Left
        vx - vy + wz * k,  // Rear Right
    };

    // Normalize to [-1, 1] if any wheel exceeds max velocity
    float max_val = 0.0f;
    for (int i = 0; i < MOTOR_COUNT; i++) {
        float absval = fabsf(raw[i]);
        if (absval > max_val) max_val = absval;
    }

    float scale = 1.0f;
    if (max_val > MAX_LINEAR_VEL) {
        scale = MAX_LINEAR_VEL / max_val;
    }

    for (int i = 0; i < MOTOR_COUNT; i++) {
        out.speeds[i] = (raw[i] * scale) / MAX_LINEAR_VEL;
        motor_set_speed((motor_id_t)i, out.speeds[i]);
    }

    return out;
}

void motor_stop_all(void)
{
    for (int i = 0; i < MOTOR_COUNT; i++) {
        ledc_set_duty(LEDC_LOW_SPEED_MODE, motors[i].in1_ch, 0);
        ledc_set_duty(LEDC_LOW_SPEED_MODE, motors[i].in2_ch, 0);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, motors[i].in1_ch);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, motors[i].in2_ch);
    }
    stopped = true;
}

bool motor_is_stopped(void)
{
    return stopped;
}
