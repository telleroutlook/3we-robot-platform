// SPDX-License-Identifier: Apache-2.0
// Test runner — entry point for all unit tests
#include "unity.h"

// test_kinematics.c
extern void test_mecanum_zero_input_gives_zero_output(void);
extern void test_mecanum_pure_forward(void);
extern void test_mecanum_pure_backward(void);
extern void test_mecanum_pure_strafe_left(void);
extern void test_mecanum_pure_strafe_right(void);
extern void test_mecanum_rotation_ccw(void);
extern void test_mecanum_normalization(void);
extern void test_mecanum_half_speed_forward(void);
extern void test_mecanum_diagonal_motion(void);

// test_safety_clamp.c
extern void test_clamp_within_range_positive(void);
extern void test_clamp_within_range_negative(void);
extern void test_clamp_zero(void);
extern void test_clamp_above_limit(void);
extern void test_clamp_below_negative_limit(void);
extern void test_clamp_at_exact_limit(void);
extern void test_clamp_at_exact_negative_limit(void);
extern void test_set_speed_limit_valid(void);
extern void test_set_speed_limit_rejects_zero(void);
extern void test_set_speed_limit_rejects_negative(void);
extern void test_set_speed_limit_rejects_above_hard_cap(void);

// test_encoder_math.c
extern void test_encoder_zero_delta_gives_zero_speed(void);
extern void test_encoder_positive_delta_gives_positive_speed(void);
extern void test_encoder_negative_delta_gives_negative_speed(void);
extern void test_encoder_fractional_revolution(void);
extern void test_encoder_get_count(void);
extern void test_encoder_invalid_id_returns_zero(void);

// test_battery_pct.c
extern void test_battery_full_charge(void);
extern void test_battery_critical_voltage(void);
extern void test_battery_below_critical(void);
extern void test_battery_above_full(void);
extern void test_battery_mid_range(void);
extern void test_battery_low_threshold(void);
extern void test_battery_ok_state(void);
extern void test_battery_critical_state(void);
extern void test_battery_not_initialized_returns_zero(void);

int main(void)
{
    UNITY_BEGIN();

    // Kinematics
    RUN_TEST(test_mecanum_zero_input_gives_zero_output);
    RUN_TEST(test_mecanum_pure_forward);
    RUN_TEST(test_mecanum_pure_backward);
    RUN_TEST(test_mecanum_pure_strafe_left);
    RUN_TEST(test_mecanum_pure_strafe_right);
    RUN_TEST(test_mecanum_rotation_ccw);
    RUN_TEST(test_mecanum_normalization);
    RUN_TEST(test_mecanum_half_speed_forward);
    RUN_TEST(test_mecanum_diagonal_motion);

    // Safety speed clamping
    RUN_TEST(test_clamp_within_range_positive);
    RUN_TEST(test_clamp_within_range_negative);
    RUN_TEST(test_clamp_zero);
    RUN_TEST(test_clamp_above_limit);
    RUN_TEST(test_clamp_below_negative_limit);
    RUN_TEST(test_clamp_at_exact_limit);
    RUN_TEST(test_clamp_at_exact_negative_limit);
    RUN_TEST(test_set_speed_limit_valid);
    RUN_TEST(test_set_speed_limit_rejects_zero);
    RUN_TEST(test_set_speed_limit_rejects_negative);
    RUN_TEST(test_set_speed_limit_rejects_above_hard_cap);

    // Encoder math
    RUN_TEST(test_encoder_zero_delta_gives_zero_speed);
    RUN_TEST(test_encoder_positive_delta_gives_positive_speed);
    RUN_TEST(test_encoder_negative_delta_gives_negative_speed);
    RUN_TEST(test_encoder_fractional_revolution);
    RUN_TEST(test_encoder_get_count);
    RUN_TEST(test_encoder_invalid_id_returns_zero);

    // Battery percentage
    RUN_TEST(test_battery_full_charge);
    RUN_TEST(test_battery_critical_voltage);
    RUN_TEST(test_battery_below_critical);
    RUN_TEST(test_battery_above_full);
    RUN_TEST(test_battery_mid_range);
    RUN_TEST(test_battery_low_threshold);
    RUN_TEST(test_battery_ok_state);
    RUN_TEST(test_battery_critical_state);
    RUN_TEST(test_battery_not_initialized_returns_zero);

    return UNITY_END();
}
