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
extern void test_ota_version_policy_allows_upgrade(void);
extern void test_ota_version_policy_rejects_rollback(void);
extern void test_ota_version_policy_rejects_same_version(void);
extern void test_ota_version_policy_allows_when_current_unparseable(void);

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
extern void test_isr_deferred_stop_fires_in_safety_loop(void);
extern void test_isr_deferred_stop_not_double_fired(void);
extern void test_isr_deferred_stop_noop_when_not_pending(void);

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

// test_ota_preflight.c
extern void test_preflight_result_struct_has_expected_fields(void);
extern void test_preflight_thresholds_correct(void);
extern void test_preflight_boot_fail_count_initial_zero(void);
extern void test_preflight_boot_fail_increment(void);
extern void test_preflight_boot_fail_clear(void);
extern void test_preflight_boot_fail_reaches_max(void);
extern void test_preflight_fail_reason_buffer_size(void);

// test_ota_compat.c
extern void test_compat_same_protocol_version_passes(void);
extern void test_compat_v3_compatible_with_v2(void);
extern void test_compat_v1_incompatible_with_v2(void);
extern void test_compat_unknown_version_rejected(void);
extern void test_compat_no_current_version_allows_any(void);
extern void test_compat_v2_min_boundary(void);
extern void test_compat_v2_max_boundary(void);

// test_heartbeat_monitor.c
extern void test_heartbeat_init_relay_on(void);
extern void test_heartbeat_feed_transitions_to_active(void);
extern void test_heartbeat_feed_updates_timestamp(void);
extern void test_heartbeat_status_initial(void);
extern void test_heartbeat_timeout_constants(void);
extern void test_heartbeat_relay_gpio_defined(void);
extern void test_heartbeat_feed_from_timeout_to_active(void);

// test_external_wdt.c
extern void test_ext_wdt_init_sets_gpio_low(void);
extern void test_ext_wdt_gpio_defined(void);
extern void test_ext_wdt_feed_period(void);
extern void test_ext_wdt_init_success(void);

// test_battery_multipack.c
extern void test_battery_multipack_constants(void);
extern void test_battery_pack2_gpio_defined(void);
extern void test_battery_system_state_single_pack(void);
extern void test_battery_pack_state_struct(void);
extern void test_battery_pack0_voltage(void);
extern void test_battery_invalid_pack_index(void);
extern void test_battery_system_state_worst_state(void);

// test_ota_upload.c
extern void test_upload_rejects_zero_content_length(void);
extern void test_upload_rejects_oversized_content(void);
extern void test_upload_rejects_short_header(void);
extern void test_upload_rejects_invalid_magic(void);
extern void test_upload_rejects_zero_firmware_size(void);
extern void test_upload_rejects_firmware_size_too_large(void);
extern void test_upload_rejects_no_ota_partition(void);
extern void test_upload_rejects_ota_begin_failure(void);
extern void test_upload_incomplete_body(void);
extern void test_upload_write_failure_aborts(void);
extern void test_upload_signature_verification_failure(void);
extern void test_upload_ota_end_failure(void);
extern void test_upload_set_boot_partition_failure(void);
extern void test_upload_success_triggers_reboot(void);
extern void test_upload_writes_correct_firmware_data(void);

// test_dtls_authority.c
extern void test_authority_init_sets_no_holder(void);
extern void test_authority_init_no_one_is_holder(void);
extern void test_authority_request_grants_when_empty(void);
extern void test_authority_request_grants_different_session_when_empty(void);
extern void test_authority_request_same_session_returns_granted(void);
extern void test_authority_request_preempts_lower_priority(void);
extern void test_authority_request_denied_equal_priority(void);
extern void test_authority_request_denied_lower_priority(void);
extern void test_authority_request_rejects_invalid_session(void);
extern void test_authority_request_null_preempted_does_not_crash(void);
extern void test_authority_release_clears_holder(void);
extern void test_authority_release_wrong_session_no_effect(void);
extern void test_authority_release_when_empty_no_effect(void);
extern void test_authority_disconnect_releases_holder(void);
extern void test_authority_disconnect_non_holder_no_effect(void);
extern void test_authority_feed_updates_timestamp(void);
extern void test_authority_feed_no_holder_is_noop(void);
extern void test_authority_check_idle_no_holder_returns_false(void);
extern void test_authority_check_idle_no_feed_yet_returns_false(void);
extern void test_authority_check_idle_within_timeout_returns_false(void);
extern void test_authority_check_idle_expired_releases_and_returns_true(void);
extern void test_authority_check_idle_exact_boundary_not_expired(void);
extern void test_authority_sequence_preempt_release_rerequest(void);

// test_microros_messages.c
extern void test_fk_all_wheels_forward_gives_pure_vx(void);
extern void test_fk_zero_wheels_gives_zero_velocity(void);
extern void test_fk_strafe_right_pattern(void);
extern void test_fk_rotation_ccw_pattern(void);
extern void test_fk_asymmetric_speeds_give_combined_motion(void);
extern void test_odom_integration_forward(void);
extern void test_odom_integration_rotation_then_forward(void);
extern void test_odom_integration_zero_velocity(void);
extern void test_odom_integration_small_dt(void);
extern void test_quaternion_zero_yaw(void);
extern void test_quaternion_90_degrees(void);
extern void test_quaternion_unit_norm(void);
extern void test_cmd_vel_clamp_within_limit(void);
extern void test_cmd_vel_clamp_above_limit(void);
extern void test_cmd_vel_clamp_below_negative_limit(void);
extern void test_wheel_msg_requires_4_elements(void);
extern void test_range_field_of_view_reasonable(void);
extern void test_range_limits_match_params(void);
extern void test_battery_percentage_bounded(void);
extern void test_battery_percentage_boundary_zero(void);
extern void test_battery_percentage_boundary_full(void);

// test_current_sense.c
extern void test_current_sense_init_returns_ok(void);
extern void test_current_sense_read_null_returns_invalid_arg(void);
extern void test_current_sense_read_zeroed_after_init(void);
extern void test_current_sense_get_state_invalid_channel(void);
extern void test_current_sense_get_state_normal_after_init(void);
extern void test_current_sense_update_zero_current(void);
extern void test_current_sense_update_normal_current(void);
extern void test_current_sense_soft_limit_requires_duration(void);
extern void test_current_sense_hard_limit_triggers_after_duration(void);
extern void test_current_sense_overcurrent_clears_when_normal(void);
extern void test_current_sense_total_current_sums_channels(void);
extern void test_current_sense_hard_limit_sets_overcurrent_flags(void);
extern void test_current_sense_negative_current_uses_absolute(void);

// test_charging_detect.c
extern void test_charging_detect_init_success(void);
extern void test_charging_detect_not_connected_below_threshold(void);
extern void test_charging_detect_connected_at_threshold(void);
extern void test_charging_detect_connected_above_threshold(void);
extern void test_charging_detect_voltage_returns_calibrated(void);
extern void test_charging_detect_voltage_zero_before_init(void);
extern void test_charging_detect_boundary_just_below_threshold(void);
#ifdef CONFIG_ROBOT_DOCKING_DIGITAL_DETECT
extern void test_charging_detect_digital_asserted_when_low(void);
extern void test_charging_detect_connected_via_analog_only(void);
extern void test_charging_detect_connected_via_digital_only(void);
extern void test_charging_detect_method_reports_both(void);
#endif
extern void test_charging_detect_method_analog_when_connected(void);
extern void test_charging_detect_method_none_when_disconnected(void);

// test_payload_power.c
extern void power_test_setUp(void);
extern void test_power_init_configures_rails(void);
extern void test_power_init_rejects_null(void);
extern void test_power_init_rejects_zero_rails(void);
extern void test_power_init_rejects_too_many_rails(void);
extern void test_power_enable_rail_writes_mcp_bit(void);
extern void test_power_disable_rail_clears_mcp_bit(void);
extern void test_power_disable_all_clears_all_bits(void);
extern void test_power_state_transitions(void);
extern void test_power_invalid_rail_index_returns_error(void);
extern void test_power_enable_disabled_rail_returns_error(void);
extern void test_power_get_status_returns_current_state(void);
extern void test_power_get_status_null_returns_error(void);

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
    RUN_TEST(test_ota_version_policy_allows_upgrade);
    RUN_TEST(test_ota_version_policy_rejects_rollback);
    RUN_TEST(test_ota_version_policy_rejects_same_version);
    RUN_TEST(test_ota_version_policy_allows_when_current_unparseable);

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
    RUN_TEST(test_isr_deferred_stop_fires_in_safety_loop);
    RUN_TEST(test_isr_deferred_stop_not_double_fired);
    RUN_TEST(test_isr_deferred_stop_noop_when_not_pending);

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

    // OTA preflight
    RUN_TEST(test_preflight_result_struct_has_expected_fields);
    RUN_TEST(test_preflight_thresholds_correct);
    RUN_TEST(test_preflight_boot_fail_count_initial_zero);
    RUN_TEST(test_preflight_boot_fail_increment);
    RUN_TEST(test_preflight_boot_fail_clear);
    RUN_TEST(test_preflight_boot_fail_reaches_max);
    RUN_TEST(test_preflight_fail_reason_buffer_size);

    // OTA compatibility
    RUN_TEST(test_compat_same_protocol_version_passes);
    RUN_TEST(test_compat_v3_compatible_with_v2);
    RUN_TEST(test_compat_v1_incompatible_with_v2);
    RUN_TEST(test_compat_unknown_version_rejected);
    RUN_TEST(test_compat_no_current_version_allows_any);
    RUN_TEST(test_compat_v2_min_boundary);
    RUN_TEST(test_compat_v2_max_boundary);

    // Heartbeat monitor
    RUN_TEST(test_heartbeat_init_relay_on);
    RUN_TEST(test_heartbeat_feed_transitions_to_active);
    RUN_TEST(test_heartbeat_feed_updates_timestamp);
    RUN_TEST(test_heartbeat_status_initial);
    RUN_TEST(test_heartbeat_timeout_constants);
    RUN_TEST(test_heartbeat_relay_gpio_defined);
    RUN_TEST(test_heartbeat_feed_from_timeout_to_active);

    // External watchdog
    RUN_TEST(test_ext_wdt_init_sets_gpio_low);
    RUN_TEST(test_ext_wdt_gpio_defined);
    RUN_TEST(test_ext_wdt_feed_period);
    RUN_TEST(test_ext_wdt_init_success);

    // Multi-battery pack
    RUN_TEST(test_battery_multipack_constants);
    RUN_TEST(test_battery_pack2_gpio_defined);
    RUN_TEST(test_battery_system_state_single_pack);
    RUN_TEST(test_battery_pack_state_struct);
    RUN_TEST(test_battery_pack0_voltage);
    RUN_TEST(test_battery_invalid_pack_index);
    RUN_TEST(test_battery_system_state_worst_state);

    // OTA upload handler
    RUN_TEST(test_upload_rejects_zero_content_length);
    RUN_TEST(test_upload_rejects_oversized_content);
    RUN_TEST(test_upload_rejects_short_header);
    RUN_TEST(test_upload_rejects_invalid_magic);
    RUN_TEST(test_upload_rejects_zero_firmware_size);
    RUN_TEST(test_upload_rejects_firmware_size_too_large);
    RUN_TEST(test_upload_rejects_no_ota_partition);
    RUN_TEST(test_upload_rejects_ota_begin_failure);
    RUN_TEST(test_upload_incomplete_body);
    RUN_TEST(test_upload_write_failure_aborts);
    RUN_TEST(test_upload_signature_verification_failure);
    RUN_TEST(test_upload_ota_end_failure);
    RUN_TEST(test_upload_set_boot_partition_failure);
    RUN_TEST(test_upload_success_triggers_reboot);
    RUN_TEST(test_upload_writes_correct_firmware_data);

    // micro-ROS message logic
    RUN_TEST(test_fk_all_wheels_forward_gives_pure_vx);
    RUN_TEST(test_fk_zero_wheels_gives_zero_velocity);
    RUN_TEST(test_fk_strafe_right_pattern);
    RUN_TEST(test_fk_rotation_ccw_pattern);
    RUN_TEST(test_fk_asymmetric_speeds_give_combined_motion);
    RUN_TEST(test_odom_integration_forward);
    RUN_TEST(test_odom_integration_rotation_then_forward);
    RUN_TEST(test_odom_integration_zero_velocity);
    RUN_TEST(test_odom_integration_small_dt);
    RUN_TEST(test_quaternion_zero_yaw);
    RUN_TEST(test_quaternion_90_degrees);
    RUN_TEST(test_quaternion_unit_norm);
    RUN_TEST(test_cmd_vel_clamp_within_limit);
    RUN_TEST(test_cmd_vel_clamp_above_limit);
    RUN_TEST(test_cmd_vel_clamp_below_negative_limit);
    RUN_TEST(test_wheel_msg_requires_4_elements);
    RUN_TEST(test_range_field_of_view_reasonable);
    RUN_TEST(test_range_limits_match_params);
    RUN_TEST(test_battery_percentage_bounded);
    RUN_TEST(test_battery_percentage_boundary_zero);
    RUN_TEST(test_battery_percentage_boundary_full);

    // DTLS authority state machine
    RUN_TEST(test_authority_init_sets_no_holder);
    RUN_TEST(test_authority_init_no_one_is_holder);
    RUN_TEST(test_authority_request_grants_when_empty);
    RUN_TEST(test_authority_request_grants_different_session_when_empty);
    RUN_TEST(test_authority_request_same_session_returns_granted);
    RUN_TEST(test_authority_request_preempts_lower_priority);
    RUN_TEST(test_authority_request_denied_equal_priority);
    RUN_TEST(test_authority_request_denied_lower_priority);
    RUN_TEST(test_authority_request_rejects_invalid_session);
    RUN_TEST(test_authority_request_null_preempted_does_not_crash);
    RUN_TEST(test_authority_release_clears_holder);
    RUN_TEST(test_authority_release_wrong_session_no_effect);
    RUN_TEST(test_authority_release_when_empty_no_effect);
    RUN_TEST(test_authority_disconnect_releases_holder);
    RUN_TEST(test_authority_disconnect_non_holder_no_effect);
    RUN_TEST(test_authority_feed_updates_timestamp);
    RUN_TEST(test_authority_feed_no_holder_is_noop);
    RUN_TEST(test_authority_check_idle_no_holder_returns_false);
    RUN_TEST(test_authority_check_idle_no_feed_yet_returns_false);
    RUN_TEST(test_authority_check_idle_within_timeout_returns_false);
    RUN_TEST(test_authority_check_idle_expired_releases_and_returns_true);
    RUN_TEST(test_authority_check_idle_exact_boundary_not_expired);
    RUN_TEST(test_authority_sequence_preempt_release_rerequest);

    // Current sense (ACS712)
    RUN_TEST(test_current_sense_init_returns_ok);
    RUN_TEST(test_current_sense_read_null_returns_invalid_arg);
    RUN_TEST(test_current_sense_read_zeroed_after_init);
    RUN_TEST(test_current_sense_get_state_invalid_channel);
    RUN_TEST(test_current_sense_get_state_normal_after_init);
    RUN_TEST(test_current_sense_update_zero_current);
    RUN_TEST(test_current_sense_update_normal_current);
    RUN_TEST(test_current_sense_soft_limit_requires_duration);
    RUN_TEST(test_current_sense_hard_limit_triggers_after_duration);
    RUN_TEST(test_current_sense_overcurrent_clears_when_normal);
    RUN_TEST(test_current_sense_total_current_sums_channels);
    RUN_TEST(test_current_sense_hard_limit_sets_overcurrent_flags);
    RUN_TEST(test_current_sense_negative_current_uses_absolute);

    // Charging detect
    RUN_TEST(test_charging_detect_init_success);
    RUN_TEST(test_charging_detect_not_connected_below_threshold);
    RUN_TEST(test_charging_detect_connected_at_threshold);
    RUN_TEST(test_charging_detect_connected_above_threshold);
    RUN_TEST(test_charging_detect_voltage_returns_calibrated);
    RUN_TEST(test_charging_detect_voltage_zero_before_init);
    RUN_TEST(test_charging_detect_boundary_just_below_threshold);
#ifdef CONFIG_ROBOT_DOCKING_DIGITAL_DETECT
    RUN_TEST(test_charging_detect_digital_asserted_when_low);
    RUN_TEST(test_charging_detect_connected_via_analog_only);
    RUN_TEST(test_charging_detect_connected_via_digital_only);
    RUN_TEST(test_charging_detect_method_reports_both);
#endif
    RUN_TEST(test_charging_detect_method_analog_when_connected);
    RUN_TEST(test_charging_detect_method_none_when_disconnected);

    // Payload power rail controller
#define RUN_POWER_TEST(f) do { power_test_setUp(); RUN_TEST(f); } while(0)
    RUN_POWER_TEST(test_power_init_configures_rails);
    RUN_POWER_TEST(test_power_init_rejects_null);
    RUN_POWER_TEST(test_power_init_rejects_zero_rails);
    RUN_POWER_TEST(test_power_init_rejects_too_many_rails);
    RUN_POWER_TEST(test_power_enable_rail_writes_mcp_bit);
    RUN_POWER_TEST(test_power_disable_rail_clears_mcp_bit);
    RUN_POWER_TEST(test_power_disable_all_clears_all_bits);
    RUN_POWER_TEST(test_power_state_transitions);
    RUN_POWER_TEST(test_power_invalid_rail_index_returns_error);
    RUN_POWER_TEST(test_power_enable_disabled_rail_returns_error);
    RUN_POWER_TEST(test_power_get_status_returns_current_state);
    RUN_POWER_TEST(test_power_get_status_null_returns_error);
#undef RUN_POWER_TEST

    return UNITY_END();
}
