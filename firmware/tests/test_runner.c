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

// test_dtls_integration.c
extern void test_dtls_handshake_success_sets_connected(void);
extern void test_dtls_handshake_failure_stays_disconnected(void);
extern void test_dtls_recv_callback_dispatches_data(void);
extern void test_dtls_psk_callback_rejects_wrong_identity(void);

// test_ultrasonic_estop.c
extern void test_ultrasonic_below_threshold_triggers_estop(void);
extern void test_ultrasonic_at_threshold_does_not_trigger(void);
extern void test_ultrasonic_above_threshold_does_not_trigger(void);
extern void test_ultrasonic_does_not_retrigger_when_already_estopped(void);

// test_payload_hotplug.c
extern void test_hotplug_init_success(void);
extern void test_hotplug_init_failure_iodir(void);
extern void test_hotplug_state_absent_after_init(void);
extern void test_hotplug_descriptor_null_when_absent(void);
extern void test_hotplug_power_off_writes_zeros(void);
extern void test_hotplug_register_callback_smoke(void);
extern void test_hotplug_power_off_notifies_callback(void);
extern void test_hotplug_init_iodir_write_first(void);
extern void test_hotplug_init_failure_olat(void);
extern void test_hotplug_power_off_idempotent(void);
extern void test_hotplug_eeprom_mock_setup(void);
extern void test_hotplug_power_off_with_i2c_error(void);
extern void hotplug_test_setUp(void);

// test_canbus.c
extern void test_canbus_init_null_config(void);
extern void test_canbus_init_spi_bus_failure(void);
extern void test_canbus_init_not_config_mode(void);
extern void test_canbus_init_config_mode_verified(void);
extern void test_canbus_is_ready_initially_false(void);
extern void test_canbus_send_null_frame(void);
extern void test_canbus_send_not_ready(void);
extern void test_canbus_set_bitrate_invalid(void);
extern void test_canbus_set_filter_not_ready(void);
extern void test_canbus_set_recv_callback(void);

// test_imu.c
extern void test_imu_init_primary_addr(void);
extern void test_imu_init_alt_addr(void);
extern void test_imu_init_not_found(void);
extern void test_imu_read_quaternion(void);
extern void test_imu_read_quaternion_negative(void);
extern void test_imu_read_euler(void);
extern void test_imu_read_angular_velocity(void);
extern void test_imu_read_linear_accel(void);
extern void test_imu_is_calibrated_true(void);
extern void test_imu_is_calibrated_false(void);
extern void test_imu_read_fails_i2c_error(void);

// test_safety_state_machine.c
extern void test_safety_init_normal(void);
extern void test_safety_init_estopped_at_boot(void);
extern void test_safety_trigger_estop_from_normal(void);
extern void test_safety_trigger_estop_already_stopped(void);
extern void test_safety_is_estopped_all_non_normal(void);
extern void test_safety_reset_success(void);
extern void test_safety_reset_rejects_button_pressed(void);
extern void test_safety_reset_rejects_relay_fault(void);
extern void test_safety_reset_rejects_wrong_state(void);
extern void test_safety_confirm_reset_success(void);
extern void test_safety_confirm_reset_rejects_button_pressed(void);
extern void test_safety_confirm_reset_rejects_wrong_state(void);
extern void test_safety_watchdog_timeout(void);
extern void test_safety_feed_watchdog_resets(void);
extern void test_safety_relay_selftest_pass_released(void);
extern void test_safety_relay_selftest_fail_stuck_off(void);
extern void test_safety_relay_selftest_pass_pressed(void);
extern void test_safety_relay_selftest_fail_welded(void);
extern void test_safety_clear_relay_fault_success(void);
extern void test_safety_clear_relay_fault_wrong_state(void);
extern void test_safety_callback_invoked_on_trigger(void);

// test_thermal_monitor.c
extern void test_thermal_init_success(void);
extern void test_thermal_init_verifies_i2c_writes(void);
extern void test_thermal_init_failure_i2c_write_error(void);
extern void test_thermal_get_state_after_init(void);
extern void test_thermal_get_reading_null_returns_invalid_arg(void);
extern void test_thermal_get_reading_valid_returns_zeroed_after_init(void);
extern void test_thermal_register_callback_does_not_crash(void);
extern void test_thermal_register_callback_null_does_not_crash(void);

// test_i2c_bus.c
extern void test_i2c_bus_init_success(void);
extern void test_i2c_bus_init_idempotent(void);
extern void test_i2c_bus_get_mutex_after_init(void);
extern void test_i2c_bus_lock_unlock_cycle(void);

// test_udp_transport.c
extern void test_udp_init_rejects_null_config(void);
extern void test_udp_has_client_initially_false(void);
extern void test_udp_init_fails_socket_create(void);
extern void test_udp_init_fails_bind(void);
extern void test_udp_init_success(void);
extern void test_udp_send_telemetry_no_client(void);
extern void test_udp_set_recv_callback(void);

// test_captive_portal.c
extern void test_captive_portal_ssid_from_mac(void);
extern void test_captive_portal_ssid_zero_mac(void);
extern void test_captive_portal_store_rejects_empty_ssid(void);
extern void test_captive_portal_store_rejects_null_ssid(void);
extern void test_captive_portal_store_accepts_valid(void);
extern void test_captive_portal_store_empty_password(void);
extern void test_captive_portal_store_null_password(void);

// test_ota_update.c
extern void test_ota_update_progress_initial_idle(void);
extern void test_ota_update_progress_downloading(void);
extern void test_ota_update_progress_failed_with_message(void);
extern void test_ota_update_progress_pct_calculation(void);
extern void test_ota_update_progress_pct_zero_total(void);
extern void test_ota_update_progress_pct_complete(void);
extern void test_ota_update_rejects_empty_url(void);
extern void test_ota_update_url_max_length(void);

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

    // DTLS integration (handshake + PSK + recv dispatch)
    RUN_TEST(test_dtls_handshake_success_sets_connected);
    RUN_TEST(test_dtls_handshake_failure_stays_disconnected);
    RUN_TEST(test_dtls_recv_callback_dispatches_data);
    RUN_TEST(test_dtls_psk_callback_rejects_wrong_identity);

    // Ultrasonic safety estop path
    RUN_TEST(test_ultrasonic_below_threshold_triggers_estop);
    RUN_TEST(test_ultrasonic_at_threshold_does_not_trigger);
    RUN_TEST(test_ultrasonic_above_threshold_does_not_trigger);
    RUN_TEST(test_ultrasonic_does_not_retrigger_when_already_estopped);

    // Payload hot-plug
#define RUN_HOTPLUG_TEST(f) do { hotplug_test_setUp(); RUN_TEST(f); } while(0)
    RUN_HOTPLUG_TEST(test_hotplug_init_success);
    RUN_HOTPLUG_TEST(test_hotplug_init_failure_iodir);
    RUN_HOTPLUG_TEST(test_hotplug_state_absent_after_init);
    RUN_HOTPLUG_TEST(test_hotplug_descriptor_null_when_absent);
    RUN_HOTPLUG_TEST(test_hotplug_power_off_writes_zeros);
    RUN_HOTPLUG_TEST(test_hotplug_register_callback_smoke);
    RUN_HOTPLUG_TEST(test_hotplug_power_off_notifies_callback);
    RUN_HOTPLUG_TEST(test_hotplug_init_iodir_write_first);
    RUN_HOTPLUG_TEST(test_hotplug_init_failure_olat);
    RUN_HOTPLUG_TEST(test_hotplug_power_off_idempotent);
    RUN_HOTPLUG_TEST(test_hotplug_eeprom_mock_setup);
    RUN_HOTPLUG_TEST(test_hotplug_power_off_with_i2c_error);
#undef RUN_HOTPLUG_TEST

    // CAN bus (MCP2515)
    RUN_TEST(test_canbus_init_null_config);
    RUN_TEST(test_canbus_init_spi_bus_failure);
    RUN_TEST(test_canbus_init_not_config_mode);
    RUN_TEST(test_canbus_init_config_mode_verified);
    RUN_TEST(test_canbus_is_ready_initially_false);
    RUN_TEST(test_canbus_send_null_frame);
    RUN_TEST(test_canbus_send_not_ready);
    RUN_TEST(test_canbus_set_bitrate_invalid);
    RUN_TEST(test_canbus_set_filter_not_ready);
    RUN_TEST(test_canbus_set_recv_callback);

    // IMU (BNO055)
    RUN_TEST(test_imu_init_primary_addr);
    RUN_TEST(test_imu_init_alt_addr);
    RUN_TEST(test_imu_init_not_found);
    RUN_TEST(test_imu_read_quaternion);
    RUN_TEST(test_imu_read_quaternion_negative);
    RUN_TEST(test_imu_read_euler);
    RUN_TEST(test_imu_read_angular_velocity);
    RUN_TEST(test_imu_read_linear_accel);
    RUN_TEST(test_imu_is_calibrated_true);
    RUN_TEST(test_imu_is_calibrated_false);
    RUN_TEST(test_imu_read_fails_i2c_error);

    // Safety state machine
    RUN_TEST(test_safety_init_normal);
    RUN_TEST(test_safety_init_estopped_at_boot);
    RUN_TEST(test_safety_trigger_estop_from_normal);
    RUN_TEST(test_safety_trigger_estop_already_stopped);
    RUN_TEST(test_safety_is_estopped_all_non_normal);
    RUN_TEST(test_safety_reset_success);
    RUN_TEST(test_safety_reset_rejects_button_pressed);
    RUN_TEST(test_safety_reset_rejects_relay_fault);
    RUN_TEST(test_safety_reset_rejects_wrong_state);
    RUN_TEST(test_safety_confirm_reset_success);
    RUN_TEST(test_safety_confirm_reset_rejects_button_pressed);
    RUN_TEST(test_safety_confirm_reset_rejects_wrong_state);
    RUN_TEST(test_safety_watchdog_timeout);
    RUN_TEST(test_safety_feed_watchdog_resets);
    RUN_TEST(test_safety_relay_selftest_pass_released);
    RUN_TEST(test_safety_relay_selftest_fail_stuck_off);
    RUN_TEST(test_safety_relay_selftest_pass_pressed);
    RUN_TEST(test_safety_relay_selftest_fail_welded);
    RUN_TEST(test_safety_clear_relay_fault_success);
    RUN_TEST(test_safety_clear_relay_fault_wrong_state);
    RUN_TEST(test_safety_callback_invoked_on_trigger);

    // Thermal monitor (INA219)
    RUN_TEST(test_thermal_init_success);
    RUN_TEST(test_thermal_init_verifies_i2c_writes);
    RUN_TEST(test_thermal_init_failure_i2c_write_error);
    RUN_TEST(test_thermal_get_state_after_init);
    RUN_TEST(test_thermal_get_reading_null_returns_invalid_arg);
    RUN_TEST(test_thermal_get_reading_valid_returns_zeroed_after_init);
    RUN_TEST(test_thermal_register_callback_does_not_crash);
    RUN_TEST(test_thermal_register_callback_null_does_not_crash);

    // I2C bus
    RUN_TEST(test_i2c_bus_init_success);
    RUN_TEST(test_i2c_bus_init_idempotent);
    RUN_TEST(test_i2c_bus_get_mutex_after_init);
    RUN_TEST(test_i2c_bus_lock_unlock_cycle);

    // UDP transport
    RUN_TEST(test_udp_init_rejects_null_config);
    RUN_TEST(test_udp_has_client_initially_false);
    RUN_TEST(test_udp_init_fails_socket_create);
    RUN_TEST(test_udp_init_fails_bind);
    RUN_TEST(test_udp_init_success);
    RUN_TEST(test_udp_send_telemetry_no_client);
    RUN_TEST(test_udp_set_recv_callback);

    // Captive portal
    RUN_TEST(test_captive_portal_ssid_from_mac);
    RUN_TEST(test_captive_portal_ssid_zero_mac);
    RUN_TEST(test_captive_portal_store_rejects_empty_ssid);
    RUN_TEST(test_captive_portal_store_rejects_null_ssid);
    RUN_TEST(test_captive_portal_store_accepts_valid);
    RUN_TEST(test_captive_portal_store_empty_password);
    RUN_TEST(test_captive_portal_store_null_password);

    // OTA update
    RUN_TEST(test_ota_update_progress_initial_idle);
    RUN_TEST(test_ota_update_progress_downloading);
    RUN_TEST(test_ota_update_progress_failed_with_message);
    RUN_TEST(test_ota_update_progress_pct_calculation);
    RUN_TEST(test_ota_update_progress_pct_zero_total);
    RUN_TEST(test_ota_update_progress_pct_complete);
    RUN_TEST(test_ota_update_rejects_empty_url);
    RUN_TEST(test_ota_update_url_max_length);

    return UNITY_END();
}
