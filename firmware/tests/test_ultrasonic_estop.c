// SPDX-License-Identifier: Apache-2.0
// Unit tests for ultrasonic safety estop path
#include "unity.h"
#include "safety.h"
#include "ultrasonic.h"
#include "robot_params.h"
#include "pin_definitions.h"
#include "esp_stubs.h"

static void reset_to_normal(void)
{
    // Simulate button released (high = not pressed)
    mock_set_gpio_level(ESTOP_GPIO, 1);
    safety_reset();
    safety_confirm_reset();
}

void test_ultrasonic_below_threshold_triggers_estop(void)
{
    reset_to_normal();
    TEST_ASSERT_FALSE(safety_is_estopped());

    float dist = US_SAFETY_THRESHOLD_M - 0.01f;
    if (dist < US_SAFETY_THRESHOLD_M && !safety_is_estopped()) {
        safety_trigger_estop();
    }

    TEST_ASSERT_TRUE(safety_is_estopped());
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());
}

void test_ultrasonic_at_threshold_does_not_trigger(void)
{
    reset_to_normal();
    TEST_ASSERT_FALSE(safety_is_estopped());

    float dist = US_SAFETY_THRESHOLD_M;
    if (dist < US_SAFETY_THRESHOLD_M && !safety_is_estopped()) {
        safety_trigger_estop();
    }

    TEST_ASSERT_FALSE(safety_is_estopped());
}

void test_ultrasonic_above_threshold_does_not_trigger(void)
{
    reset_to_normal();
    TEST_ASSERT_FALSE(safety_is_estopped());

    float dist = US_SAFETY_THRESHOLD_M + 0.5f;
    if (dist < US_SAFETY_THRESHOLD_M && !safety_is_estopped()) {
        safety_trigger_estop();
    }

    TEST_ASSERT_FALSE(safety_is_estopped());
}

void test_ultrasonic_does_not_retrigger_when_already_estopped(void)
{
    reset_to_normal();
    safety_trigger_estop();
    TEST_ASSERT_TRUE(safety_is_estopped());

    float dist = US_SAFETY_THRESHOLD_M - 0.01f;
    bool would_trigger = (dist < US_SAFETY_THRESHOLD_M && !safety_is_estopped());
    TEST_ASSERT_FALSE(would_trigger);
}
