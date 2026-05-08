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

// test_ota_signing.c
extern void test_ota_init_accepts_valid_pubkey(void);
extern void test_ota_init_rejects_null_pubkey(void);
extern void test_ota_verify_accepts_valid_image(void);
extern void test_ota_verify_rejects_before_init(void);
extern void test_ota_verify_rejects_wrong_magic(void);
extern void test_ota_verify_rejects_size_mismatch(void);
extern void test_ota_verify_rejects_hash_mismatch(void);
extern void test_ota_verify_rejects_invalid_signature(void);
extern void test_ota_apply_rejects_too_small(void);
extern void test_ota_apply_rejects_too_large(void);
extern void test_ota_apply_rejects_version_rollback(void);
extern void test_ota_apply_rejects_same_version(void);
extern void test_ota_apply_succeeds_with_valid_upgrade(void);
extern void test_ota_apply_rejects_when_no_partition(void);

// test_dtls_transport.c
extern void test_dtls_init_rejects_null_config(void);
extern void test_dtls_init_accepts_valid_config(void);
extern void test_dtls_not_connected_initially(void);
extern void test_dtls_send_rejects_when_not_connected(void);
extern void test_dtls_callback_registration(void);
extern void test_dtls_default_ports(void);
extern void test_dtls_default_timeouts(void);

// test_ultrasonic_estop.c
extern void test_ultrasonic_below_threshold_triggers_estop(void);
extern void test_ultrasonic_at_threshold_does_not_trigger(void);
extern void test_ultrasonic_above_threshold_does_not_trigger(void);
extern void test_ultrasonic_does_not_retrigger_when_already_estopped(void);

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

    // OTA signing
    RUN_TEST(test_ota_init_accepts_valid_pubkey);
    RUN_TEST(test_ota_init_rejects_null_pubkey);
    RUN_TEST(test_ota_verify_accepts_valid_image);
    RUN_TEST(test_ota_verify_rejects_before_init);
    RUN_TEST(test_ota_verify_rejects_wrong_magic);
    RUN_TEST(test_ota_verify_rejects_size_mismatch);
    RUN_TEST(test_ota_verify_rejects_hash_mismatch);
    RUN_TEST(test_ota_verify_rejects_invalid_signature);
    RUN_TEST(test_ota_apply_rejects_too_small);
    RUN_TEST(test_ota_apply_rejects_too_large);
    RUN_TEST(test_ota_apply_rejects_version_rollback);
    RUN_TEST(test_ota_apply_rejects_same_version);
    RUN_TEST(test_ota_apply_succeeds_with_valid_upgrade);
    RUN_TEST(test_ota_apply_rejects_when_no_partition);

    // DTLS transport
    RUN_TEST(test_dtls_init_rejects_null_config);
    RUN_TEST(test_dtls_init_accepts_valid_config);
    RUN_TEST(test_dtls_not_connected_initially);
    RUN_TEST(test_dtls_send_rejects_when_not_connected);
    RUN_TEST(test_dtls_callback_registration);
    RUN_TEST(test_dtls_default_ports);
    RUN_TEST(test_dtls_default_timeouts);

    // Ultrasonic safety estop path
    RUN_TEST(test_ultrasonic_below_threshold_triggers_estop);
    RUN_TEST(test_ultrasonic_at_threshold_does_not_trigger);
    RUN_TEST(test_ultrasonic_above_threshold_does_not_trigger);
    RUN_TEST(test_ultrasonic_does_not_retrigger_when_already_estopped);

    return UNITY_END();
}
