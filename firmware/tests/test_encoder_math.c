// SPDX-License-Identifier: Apache-2.0
// Unit tests for encoder speed calculation
#include "unity.h"
#include "encoder.h"
#include "motor_control.h"
#include "robot_params.h"
#include "esp_stubs.h"

#define FLOAT_TOLERANCE 0.001f
#define TICK_20MS       20000  // 20ms in microseconds

void test_encoder_zero_delta_gives_zero_speed(void)
{
    mock_reset_pcnt();
    mock_set_timer(0);
    encoder_init();

    mock_set_pcnt_count(MOTOR_FL, 0);
    mock_set_pcnt_count(MOTOR_FR, 0);
    mock_set_pcnt_count(MOTOR_RL, 0);
    mock_set_pcnt_count(MOTOR_RR, 0);

    encoder_update();
    mock_set_timer(TICK_20MS);
    encoder_update();

    for (int i = 0; i < MOTOR_COUNT; i++) {
        TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, encoder_get_speed_rps(i));
    }
}

void test_encoder_positive_delta_gives_positive_speed(void)
{
    mock_reset_pcnt();
    mock_set_timer(0);
    encoder_init();

    // First call to establish baseline
    mock_set_pcnt_count(MOTOR_FL, 0);
    encoder_update();

    // Second call with 1440 counts after 20ms
    mock_set_timer(TICK_20MS);
    mock_set_pcnt_count(MOTOR_FL, ENCODER_CPR);
    encoder_update();

    // Expected: (1440 / 1440) / 0.02 = 50 RPS
    float expected_rps = (float)ENCODER_CPR / (float)ENCODER_CPR / 0.02f;
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, expected_rps, encoder_get_speed_rps(MOTOR_FL));
}

void test_encoder_negative_delta_gives_negative_speed(void)
{
    mock_reset_pcnt();
    mock_set_timer(0);
    encoder_init();

    mock_set_pcnt_count(MOTOR_FR, 0);
    encoder_update();

    mock_set_timer(TICK_20MS);
    mock_set_pcnt_count(MOTOR_FR, -720);
    encoder_update();

    // Expected: (-720 / 1440) / 0.02 = -25 RPS
    float expected_rps = (-720.0f / (float)ENCODER_CPR) / 0.02f;
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, expected_rps, encoder_get_speed_rps(MOTOR_FR));
}

void test_encoder_fractional_revolution(void)
{
    mock_reset_pcnt();
    mock_set_timer(0);
    encoder_init();

    mock_set_pcnt_count(MOTOR_RL, 0);
    encoder_update();

    // 360 counts = quarter revolution after 20ms
    mock_set_timer(TICK_20MS);
    mock_set_pcnt_count(MOTOR_RL, 360);
    encoder_update();

    float expected_rps = (360.0f / (float)ENCODER_CPR) / 0.02f;
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, expected_rps, encoder_get_speed_rps(MOTOR_RL));
}

void test_encoder_get_count(void)
{
    mock_reset_pcnt();
    encoder_init();

    mock_set_pcnt_count(MOTOR_RR, 12345);
    TEST_ASSERT_EQUAL_INT32(12345, encoder_get_count(MOTOR_RR));
}

void test_encoder_invalid_id_returns_zero(void)
{
    TEST_ASSERT_EQUAL_INT32(0, encoder_get_count(MOTOR_COUNT));
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, encoder_get_speed_rps(MOTOR_COUNT));
}
