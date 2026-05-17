// SPDX-License-Identifier: Apache-2.0
// Unit tests for safety_clamp_speed() and safety_clamp_velocity()
#include "unity.h"
#include "safety.h"
#include <math.h>

#define FLOAT_TOLERANCE 0.0001f

void test_clamp_within_range_positive(void)
{
    float result = safety_clamp_speed(0.5f);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.5f, result);
}

void test_clamp_within_range_negative(void)
{
    float result = safety_clamp_speed(-0.5f);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, -0.5f, result);
}

void test_clamp_zero(void)
{
    float result = safety_clamp_speed(0.0f);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, result);
}

void test_clamp_above_limit(void)
{
    float result = safety_clamp_speed(5.0f);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, safety_get_speed_limit(), result);
}

void test_clamp_below_negative_limit(void)
{
    float result = safety_clamp_speed(-5.0f);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, -safety_get_speed_limit(), result);
}

void test_clamp_at_exact_limit(void)
{
    float limit = safety_get_speed_limit();
    float result = safety_clamp_speed(limit);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, limit, result);
}

void test_clamp_at_exact_negative_limit(void)
{
    float limit = safety_get_speed_limit();
    float result = safety_clamp_speed(-limit);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, -limit, result);
}

void test_set_speed_limit_valid(void)
{
    esp_err_t err = safety_set_speed_limit(0.8f);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.8f, safety_get_speed_limit());

    // Verify clamping uses new limit
    float result = safety_clamp_speed(1.0f);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.8f, result);

    // Restore default
    safety_set_speed_limit(1.0f);
}

void test_set_speed_limit_rejects_zero(void)
{
    esp_err_t err = safety_set_speed_limit(0.0f);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

void test_set_speed_limit_rejects_negative(void)
{
    esp_err_t err = safety_set_speed_limit(-0.5f);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

void test_set_speed_limit_rejects_above_hard_cap(void)
{
    esp_err_t err = safety_set_speed_limit(SPEED_LIMIT_HARD_CAP_MPS + 1.0f);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

void test_clamp_velocity_diagonal_exceeds_limit(void)
{
    safety_set_speed_limit(1.0f);
    float vx = 0.9f, vy = 0.9f;
    safety_clamp_velocity(&vx, &vy);
    float mag = sqrtf(vx * vx + vy * vy);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 1.0f, mag);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, vx, vy);
}

void test_clamp_velocity_single_axis_same_as_scalar(void)
{
    safety_set_speed_limit(1.0f);
    float vx = 1.5f, vy = 0.0f;
    safety_clamp_velocity(&vx, &vy);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 1.0f, vx);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, vy);
}

void test_clamp_velocity_within_limit_unchanged(void)
{
    safety_set_speed_limit(1.0f);
    float vx = 0.3f, vy = 0.4f;
    safety_clamp_velocity(&vx, &vy);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.3f, vx);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.4f, vy);
}

void test_clamp_velocity_zero_vector(void)
{
    safety_set_speed_limit(1.0f);
    float vx = 0.0f, vy = 0.0f;
    safety_clamp_velocity(&vx, &vy);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, vx);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, vy);
}

void test_clamp_velocity_preserves_direction(void)
{
    safety_set_speed_limit(1.0f);
    float vx = 0.6f, vy = 0.8f;
    safety_clamp_velocity(&vx, &vy);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.6f, vx);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.8f, vy);
}

void test_clamp_velocity_negative_components(void)
{
    safety_set_speed_limit(1.0f);
    float vx = -0.9f, vy = -0.9f;
    safety_clamp_velocity(&vx, &vy);
    float mag = sqrtf(vx * vx + vy * vy);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 1.0f, mag);
    TEST_ASSERT_TRUE(vx < 0.0f);
    TEST_ASSERT_TRUE(vy < 0.0f);
}
